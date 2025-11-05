"""
Keycloak client for token exchange and authorization.

This module handles the integration between Azure Entra ID and Keycloak,
enabling authentication with Entra ID and authorization with Keycloak.
"""

import logging
from typing import Optional, Dict, Any, List
import httpx
from datetime import datetime, timedelta
from dataclasses import dataclass
import jwt

logger = logging.getLogger(__name__)


@dataclass
class KeycloakToken:
    """Keycloak access token with parsed claims."""

    access_token: str
    refresh_token: Optional[str]
    expires_in: int
    token_type: str
    scope: Optional[str]

    # Parsed claims
    sub: str  # Subject (user ID)
    preferred_username: str
    email: Optional[str]
    roles: List[str]
    resource_access: Dict[str, Any]

    # Token metadata
    issued_at: datetime
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() >= self.expires_at

    @property
    def needs_refresh(self) -> bool:
        """Check if token should be refreshed (within 5 minutes of expiry)."""
        return datetime.utcnow() >= (self.expires_at - timedelta(minutes=5))


class KeycloakClient:
    """
    Client for interacting with Keycloak for authorization.

    This client handles:
    - Token exchange (Entra ID token -> Keycloak token)
    - Token validation
    - Role and permission checking
    - Token refresh
    """

    def __init__(
        self,
        server_url: str,
        realm: str,
        client_id: str,
        client_secret: Optional[str] = None,
        verify_ssl: bool = True,
    ):
        """
        Initialize Keycloak client.

        Args:
            server_url: Keycloak server URL (e.g., https://keycloak.example.com)
            realm: Keycloak realm name
            client_id: Client ID in Keycloak
            client_secret: Client secret (for confidential clients)
            verify_ssl: Whether to verify SSL certificates
        """
        self.server_url = server_url.rstrip('/')
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.verify_ssl = verify_ssl

        # Endpoints
        self.realm_url = f"{self.server_url}/realms/{self.realm}"
        self.token_endpoint = f"{self.realm_url}/protocol/openid-connect/token"
        self.userinfo_endpoint = f"{self.realm_url}/protocol/openid-connect/userinfo"
        self.logout_endpoint = f"{self.realm_url}/protocol/openid-connect/logout"
        self.jwks_uri = f"{self.realm_url}/protocol/openid-connect/certs"

        # Cache for JWKS
        self._jwks_cache: Optional[Dict] = None
        self._jwks_cache_time: Optional[datetime] = None

        logger.info(
            f"Keycloak client initialized for realm '{realm}' at {server_url}"
        )

    async def exchange_token(
        self,
        entra_id_token: str,
        subject_token_type: str = "urn:ietf:params:oauth:token-type:access_token",
    ) -> KeycloakToken:
        """
        Exchange Entra ID token for Keycloak token using OAuth2 Token Exchange.

        Args:
            entra_id_token: The Entra ID access token
            subject_token_type: Type of the subject token

        Returns:
            KeycloakToken with access token and parsed claims

        Raises:
            httpx.HTTPError: If token exchange fails
        """
        logger.info("Exchanging Entra ID token for Keycloak token")

        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "client_id": self.client_id,
            "subject_token": entra_id_token,
            "subject_token_type": subject_token_type,
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            try:
                response = await client.post(
                    self.token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )
                response.raise_for_status()
                token_data = response.json()

                logger.info("Token exchange successful")
                return self._parse_token_response(token_data)

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Token exchange failed: {e.response.status_code} - {e.response.text}"
                )
                raise
            except Exception as e:
                logger.error(f"Token exchange error: {e}", exc_info=True)
                raise

    async def refresh_token(self, refresh_token: str) -> KeycloakToken:
        """
        Refresh Keycloak token using refresh token.

        Args:
            refresh_token: The refresh token

        Returns:
            New KeycloakToken
        """
        logger.info("Refreshing Keycloak token")

        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            response = await client.post(
                self.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            response.raise_for_status()
            token_data = response.json()

            logger.info("Token refresh successful")
            return self._parse_token_response(token_data)

    def _parse_token_response(self, token_data: Dict[str, Any]) -> KeycloakToken:
        """Parse token response from Keycloak."""
        access_token = token_data["access_token"]

        # Decode token (without verification for now, just to get claims)
        # In production, you should verify the signature
        claims = jwt.decode(
            access_token,
            options={"verify_signature": False}
        )

        # Extract roles
        roles = []
        if "realm_access" in claims:
            roles.extend(claims["realm_access"].get("roles", []))

        # Extract resource access
        resource_access = claims.get("resource_access", {})

        # Calculate expiry
        issued_at = datetime.utcnow()
        expires_in = token_data.get("expires_in", 300)
        expires_at = issued_at + timedelta(seconds=expires_in)

        return KeycloakToken(
            access_token=access_token,
            refresh_token=token_data.get("refresh_token"),
            expires_in=expires_in,
            token_type=token_data.get("token_type", "Bearer"),
            scope=token_data.get("scope"),
            sub=claims.get("sub", ""),
            preferred_username=claims.get("preferred_username", ""),
            email=claims.get("email"),
            roles=roles,
            resource_access=resource_access,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    async def verify_token(self, access_token: str) -> Dict[str, Any]:
        """
        Verify Keycloak token by calling userinfo endpoint.

        Args:
            access_token: The access token to verify

        Returns:
            User info from Keycloak
        """
        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            response = await client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    def has_role(self, token: KeycloakToken, role: str) -> bool:
        """
        Check if token has a specific realm role.

        Args:
            token: The KeycloakToken to check
            role: Role name to check for

        Returns:
            True if user has the role
        """
        return role in token.roles

    def has_resource_role(
        self,
        token: KeycloakToken,
        resource: str,
        role: str
    ) -> bool:
        """
        Check if token has a specific resource (client) role.

        Args:
            token: The KeycloakToken to check
            resource: Resource/client name
            role: Role name to check for

        Returns:
            True if user has the resource role
        """
        if resource not in token.resource_access:
            return False

        resource_roles = token.resource_access[resource].get("roles", [])
        return role in resource_roles

    def has_any_role(self, token: KeycloakToken, roles: List[str]) -> bool:
        """
        Check if token has any of the specified roles.

        Args:
            token: The KeycloakToken to check
            roles: List of role names

        Returns:
            True if user has at least one of the roles
        """
        return any(role in token.roles for role in roles)

    def has_all_roles(self, token: KeycloakToken, roles: List[str]) -> bool:
        """
        Check if token has all of the specified roles.

        Args:
            token: The KeycloakToken to check
            roles: List of role names

        Returns:
            True if user has all of the roles
        """
        return all(role in token.roles for role in roles)

    async def logout(self, refresh_token: str) -> None:
        """
        Logout and invalidate refresh token.

        Args:
            refresh_token: The refresh token to invalidate
        """
        logger.info("Logging out from Keycloak")

        data = {
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            response = await client.post(
                self.logout_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            response.raise_for_status()
            logger.info("Logout successful")


class KeycloakTokenCache:
    """
    Simple in-memory cache for Keycloak tokens.

    In production, use Redis or another distributed cache.
    """

    def __init__(self):
        """Initialize token cache."""
        self._cache: Dict[str, KeycloakToken] = {}

    def get(self, user_id: str) -> Optional[KeycloakToken]:
        """Get cached token for user."""
        token = self._cache.get(user_id)
        if token and not token.is_expired:
            return token
        elif token:
            # Remove expired token
            del self._cache[user_id]
        return None

    def set(self, user_id: str, token: KeycloakToken) -> None:
        """Cache token for user."""
        self._cache[user_id] = token

    def delete(self, user_id: str) -> None:
        """Remove cached token."""
        self._cache.pop(user_id, None)

    def clear(self) -> None:
        """Clear all cached tokens."""
        self._cache.clear()
