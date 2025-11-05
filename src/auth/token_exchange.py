"""
Token exchange service for Entra ID to Keycloak authorization handover.

This module provides the bridge between Azure Entra ID authentication
and Keycloak authorization.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from fastmcp.server.dependencies import get_access_token

from src.auth.keycloak_client import KeycloakClient, KeycloakToken, KeycloakTokenCache

logger = logging.getLogger(__name__)


@dataclass
class AuthContext:
    """
    Combined authentication and authorization context.

    Contains both Entra ID authentication info and Keycloak authorization info.
    """

    # Entra ID authentication
    entra_id_token: str
    entra_user_id: str
    entra_email: Optional[str]
    entra_claims: Dict[str, Any]

    # Keycloak authorization
    keycloak_token: KeycloakToken
    keycloak_user_id: str
    keycloak_roles: list[str]

    @property
    def user_id(self) -> str:
        """Primary user identifier (from Entra ID)."""
        return self.entra_user_id

    @property
    def email(self) -> str:
        """User email address."""
        return self.entra_email or self.keycloak_token.email or ""

    @property
    def roles(self) -> list[str]:
        """User roles from Keycloak."""
        return self.keycloak_roles


class TokenExchangeService:
    """
    Service for exchanging Entra ID tokens for Keycloak tokens.

    This service manages the token lifecycle and caching.
    """

    def __init__(
        self,
        keycloak_client: KeycloakClient,
        cache_tokens: bool = True,
    ):
        """
        Initialize token exchange service.

        Args:
            keycloak_client: Configured Keycloak client
            cache_tokens: Whether to cache Keycloak tokens
        """
        self.keycloak_client = keycloak_client
        self.cache_tokens = cache_tokens
        self._token_cache = KeycloakTokenCache() if cache_tokens else None

        logger.info(
            f"Token exchange service initialized (caching: {cache_tokens})"
        )

    async def exchange_and_get_context(
        self,
        entra_token_str: Optional[str] = None,
    ) -> AuthContext:
        """
        Exchange Entra ID token for Keycloak token and build auth context.

        This is the main method to call from within tool handlers.

        Args:
            entra_token_str: Optional Entra ID token string. If not provided,
                           will attempt to get from FastMCP context.

        Returns:
            AuthContext with both authentication and authorization info

        Raises:
            ValueError: If no Entra ID token available
            httpx.HTTPError: If token exchange fails
        """
        # Get Entra ID token
        if entra_token_str is None:
            try:
                entra_token = get_access_token()
                entra_token_str = entra_token.token if hasattr(entra_token, 'token') else str(entra_token)
                entra_claims = entra_token.claims if hasattr(entra_token, 'claims') else {}
            except Exception as e:
                logger.error(f"Failed to get Entra ID token from context: {e}")
                raise ValueError("No Entra ID token available") from e
        else:
            # Parse token manually if provided as string
            import jwt
            entra_claims = jwt.decode(entra_token_str, options={"verify_signature": False})

        # Extract Entra ID user info
        entra_user_id = entra_claims.get("oid") or entra_claims.get("sub", "")
        entra_email = entra_claims.get("email") or entra_claims.get("preferred_username")

        logger.info(f"Exchanging token for user: {entra_email or entra_user_id}")

        # Check cache first
        keycloak_token = None
        if self._token_cache:
            keycloak_token = self._token_cache.get(entra_user_id)
            if keycloak_token:
                if keycloak_token.needs_refresh and keycloak_token.refresh_token:
                    logger.info("Refreshing cached Keycloak token")
                    try:
                        keycloak_token = await self.keycloak_client.refresh_token(
                            keycloak_token.refresh_token
                        )
                        self._token_cache.set(entra_user_id, keycloak_token)
                    except Exception as e:
                        logger.warning(f"Token refresh failed, will exchange: {e}")
                        keycloak_token = None
                else:
                    logger.debug("Using cached Keycloak token")

        # Exchange token if not cached or cache failed
        if keycloak_token is None:
            logger.info("Exchanging Entra ID token for Keycloak token")
            keycloak_token = await self.keycloak_client.exchange_token(entra_token_str)

            # Cache the token
            if self._token_cache:
                self._token_cache.set(entra_user_id, keycloak_token)

        # Build auth context
        context = AuthContext(
            entra_id_token=entra_token_str,
            entra_user_id=entra_user_id,
            entra_email=entra_email,
            entra_claims=entra_claims,
            keycloak_token=keycloak_token,
            keycloak_user_id=keycloak_token.sub,
            keycloak_roles=keycloak_token.roles,
        )

        logger.info(
            f"Auth context created for user {context.email} "
            f"with {len(context.roles)} roles"
        )

        return context

    async def verify_keycloak_token(self, access_token: str) -> Dict[str, Any]:
        """
        Verify a Keycloak token.

        Args:
            access_token: Keycloak access token

        Returns:
            User info from Keycloak
        """
        return await self.keycloak_client.verify_token(access_token)

    def invalidate_cache(self, user_id: str) -> None:
        """
        Invalidate cached token for a user.

        Args:
            user_id: User ID to invalidate
        """
        if self._token_cache:
            self._token_cache.delete(user_id)
            logger.info(f"Cache invalidated for user: {user_id}")

    def clear_cache(self) -> None:
        """Clear all cached tokens."""
        if self._token_cache:
            self._token_cache.clear()
            logger.info("Token cache cleared")


# Global token exchange service instance
_token_exchange_service: Optional[TokenExchangeService] = None


def initialize_token_exchange_service(keycloak_client: KeycloakClient) -> None:
    """
    Initialize the global token exchange service.

    Should be called during server startup.

    Args:
        keycloak_client: Configured Keycloak client
    """
    global _token_exchange_service
    _token_exchange_service = TokenExchangeService(keycloak_client)
    logger.info("Global token exchange service initialized")


def get_token_exchange_service() -> TokenExchangeService:
    """
    Get the global token exchange service instance.

    Returns:
        TokenExchangeService instance

    Raises:
        RuntimeError: If service not initialized
    """
    if _token_exchange_service is None:
        raise RuntimeError(
            "Token exchange service not initialized. "
            "Call initialize_token_exchange_service() first."
        )
    return _token_exchange_service


async def get_auth_context() -> AuthContext:
    """
    Get the current auth context (Entra ID + Keycloak).

    This is a convenience function for use in tool handlers.

    Returns:
        AuthContext with authentication and authorization info

    Example:
        @mcp.tool()
        async def my_tool() -> dict:
            ctx = await get_auth_context()
            if not ctx.keycloak_token.has_role("admin"):
                return {"error": "Unauthorized"}
            # ... rest of tool logic
    """
    service = get_token_exchange_service()
    return await service.exchange_and_get_context()
