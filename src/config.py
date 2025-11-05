"""
Configuration management for the MCP server.

This module handles loading and validating configuration from environment variables,
config files, and provides sensible defaults for development and production.
"""

import os
from typing import Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class AzureAuthConfig:
    """Microsoft Entra ID (Azure AD) authentication configuration."""

    client_id: str
    client_secret: str
    tenant_id: str
    base_url: str = "http://localhost:8000"
    required_scopes: List[str] = field(default_factory=lambda: ["read", "write"])
    identifier_uri: Optional[str] = None
    redirect_path: str = "/auth/callback"
    additional_authorize_scopes: List[str] = field(default_factory=list)
    base_authority: Optional[str] = None  # For Azure Government clouds
    jwt_signing_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AzureAuthConfig":
        """Load Azure auth configuration from environment variables."""
        client_id = os.getenv("AZURE_CLIENT_ID") or os.getenv("FASTMCP_SERVER_AUTH_AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET") or os.getenv("FASTMCP_SERVER_AUTH_AZURE_CLIENT_SECRET")
        tenant_id = os.getenv("AZURE_TENANT_ID") or os.getenv("FASTMCP_SERVER_AUTH_AZURE_TENANT_ID")

        if not all([client_id, client_secret, tenant_id]):
            raise ValueError(
                "Missing required Azure auth configuration. "
                "Please set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID"
            )

        # Parse required scopes
        scopes_raw = (
            os.getenv("AZURE_REQUIRED_SCOPES") or
            os.getenv("FASTMCP_SERVER_AUTH_AZURE_REQUIRED_SCOPES") or
            "read,write"
        )
        required_scopes = cls._parse_scopes(scopes_raw)

        # Parse additional authorize scopes
        additional_scopes_raw = (
            os.getenv("AZURE_ADDITIONAL_AUTHORIZE_SCOPES") or
            os.getenv("FASTMCP_SERVER_AUTH_AZURE_ADDITIONAL_AUTHORIZE_SCOPES") or
            ""
        )
        additional_scopes = cls._parse_scopes(additional_scopes_raw) if additional_scopes_raw else []

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            base_url=os.getenv("AZURE_BASE_URL") or os.getenv("FASTMCP_SERVER_AUTH_AZURE_BASE_URL", "http://localhost:8000"),
            required_scopes=required_scopes,
            identifier_uri=os.getenv("AZURE_IDENTIFIER_URI") or os.getenv("FASTMCP_SERVER_AUTH_AZURE_IDENTIFIER_URI"),
            redirect_path=os.getenv("AZURE_REDIRECT_PATH") or os.getenv("FASTMCP_SERVER_AUTH_AZURE_REDIRECT_PATH", "/auth/callback"),
            additional_authorize_scopes=additional_scopes,
            base_authority=os.getenv("AZURE_BASE_AUTHORITY") or os.getenv("FASTMCP_SERVER_AUTH_AZURE_BASE_AUTHORITY"),
            jwt_signing_key=os.getenv("JWT_SIGNING_KEY"),
        )

    @staticmethod
    def _parse_scopes(scopes_str: str) -> List[str]:
        """Parse scope string from various formats (JSON, comma-separated, space-separated)."""
        scopes_str = scopes_str.strip()

        # Try JSON parsing first
        if scopes_str.startswith("["):
            try:
                return json.loads(scopes_str)
            except json.JSONDecodeError:
                pass

        # Try comma or space separated
        if "," in scopes_str:
            return [s.strip() for s in scopes_str.split(",") if s.strip()]
        else:
            return [s.strip() for s in scopes_str.split() if s.strip()]


@dataclass
class KeycloakConfig:
    """Keycloak authorization configuration."""

    server_url: str
    realm: str
    client_id: str
    client_secret: Optional[str] = None
    verify_ssl: bool = True
    enable_token_exchange: bool = True
    cache_tokens: bool = True

    @classmethod
    def from_env(cls) -> "KeycloakConfig":
        """Load Keycloak configuration from environment variables."""
        server_url = os.getenv("KEYCLOAK_SERVER_URL")
        realm = os.getenv("KEYCLOAK_REALM")
        client_id = os.getenv("KEYCLOAK_CLIENT_ID")

        if not all([server_url, realm, client_id]):
            raise ValueError(
                "Missing required Keycloak configuration. "
                "Please set KEYCLOAK_SERVER_URL, KEYCLOAK_REALM, and KEYCLOAK_CLIENT_ID"
            )

        return cls(
            server_url=server_url,
            realm=realm,
            client_id=client_id,
            client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET"),
            verify_ssl=os.getenv("KEYCLOAK_VERIFY_SSL", "true").lower() in ("true", "1", "yes"),
            enable_token_exchange=os.getenv("KEYCLOAK_ENABLE_TOKEN_EXCHANGE", "true").lower() in ("true", "1", "yes"),
            cache_tokens=os.getenv("KEYCLOAK_CACHE_TOKENS", "true").lower() in ("true", "1", "yes"),
        )


@dataclass
class ServerConfig:
    """Main server configuration."""

    # Server settings
    name: str = "FastMCP Boilerplate Server"
    description: str = "Production-ready MCP server with Azure Entra ID authentication and Keycloak authorization"
    host: str = "0.0.0.0"
    port: int = 8000
    transport: str = "http"  # http, sse, or stdio

    # Environment
    environment: str = "development"  # development, staging, production
    debug: bool = False

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    log_file: Optional[str] = None

    # Security
    enable_auth: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    # Azure Auth (if enabled)
    azure_auth: Optional[AzureAuthConfig] = None

    # Keycloak Authorization (if enabled)
    enable_keycloak: bool = False
    keycloak: Optional[KeycloakConfig] = None

    # Redis for production token storage
    redis_host: Optional[str] = None
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    storage_encryption_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load server configuration from environment variables."""
        environment = os.getenv("ENVIRONMENT", "development")
        enable_auth = os.getenv("ENABLE_AUTH", "true").lower() in ("true", "1", "yes")

        # Load Azure auth config if enabled
        azure_auth = None
        if enable_auth:
            try:
                azure_auth = AzureAuthConfig.from_env()
                logger.info("Azure authentication configuration loaded successfully")
            except ValueError as e:
                logger.warning(f"Azure auth disabled: {e}")
                enable_auth = False

        # Load Keycloak config if enabled
        enable_keycloak = os.getenv("ENABLE_KEYCLOAK", "false").lower() in ("true", "1", "yes")
        keycloak_config = None
        if enable_keycloak:
            try:
                keycloak_config = KeycloakConfig.from_env()
                logger.info("Keycloak authorization configuration loaded successfully")
            except ValueError as e:
                logger.warning(f"Keycloak disabled: {e}")
                enable_keycloak = False

        # Parse CORS origins
        cors_origins_str = os.getenv("CORS_ORIGINS", "*")
        if cors_origins_str == "*":
            cors_origins = ["*"]
        else:
            cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]

        return cls(
            name=os.getenv("SERVER_NAME", "FastMCP Boilerplate Server"),
            description=os.getenv("SERVER_DESCRIPTION", "Production-ready MCP server with Azure Entra ID authentication"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            transport=os.getenv("TRANSPORT", "http"),
            environment=environment,
            debug=os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "json"),
            log_file=os.getenv("LOG_FILE"),
            enable_auth=enable_auth,
            cors_origins=cors_origins,
            azure_auth=azure_auth,
            enable_keycloak=enable_keycloak,
            keycloak=keycloak_config,
            redis_host=os.getenv("REDIS_HOST"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            storage_encryption_key=os.getenv("STORAGE_ENCRYPTION_KEY"),
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def validate(self) -> None:
        """Validate configuration and raise errors for invalid settings."""
        if self.is_production:
            if self.enable_auth and not self.azure_auth:
                raise ValueError("Authentication must be configured for production environment")

            if self.azure_auth and not self.azure_auth.base_url.startswith("https://"):
                logger.warning(
                    "Production environment should use HTTPS for AZURE_BASE_URL. "
                    f"Current value: {self.azure_auth.base_url}"
                )

            if self.enable_auth and self.azure_auth:
                if not self.azure_auth.jwt_signing_key:
                    logger.warning("JWT_SIGNING_KEY not set - sessions won't persist across server restarts")

                if self.redis_host and not self.storage_encryption_key:
                    raise ValueError(
                        "STORAGE_ENCRYPTION_KEY is required when using Redis for token storage. "
                        "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                    )

        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Invalid port number: {self.port}")

        if self.transport not in ("http", "sse", "stdio"):
            raise ValueError(f"Invalid transport: {self.transport}. Must be one of: http, sse, stdio")


# Global config instance
_config: Optional[ServerConfig] = None


def get_config() -> ServerConfig:
    """Get the global configuration instance, loading it if necessary."""
    global _config
    if _config is None:
        _config = ServerConfig.from_env()
        _config.validate()
    return _config


def reload_config() -> ServerConfig:
    """Reload configuration from environment (useful for testing)."""
    global _config
    _config = None
    return get_config()
