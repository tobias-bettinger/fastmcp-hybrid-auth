"""Authentication and Authorization module for Azure Entra ID and Keycloak integration."""

from src.auth.provider import create_azure_auth_provider, get_user_info_from_token
from src.auth.keycloak_client import KeycloakClient, KeycloakToken, KeycloakTokenCache
from src.auth.token_exchange import (
    TokenExchangeService,
    AuthContext,
    initialize_token_exchange_service,
    get_token_exchange_service,
    get_auth_context,
)
from src.auth.authorization import (
    AuthorizationError,
    require_role,
    require_any_role,
    require_all_roles,
    require_resource_role,
    require_custom_check,
    AuthorizationHelper,
    format_authorization_error,
)

__all__ = [
    # Azure Entra ID
    "create_azure_auth_provider",
    "get_user_info_from_token",
    # Keycloak
    "KeycloakClient",
    "KeycloakToken",
    "KeycloakTokenCache",
    # Token Exchange
    "TokenExchangeService",
    "AuthContext",
    "initialize_token_exchange_service",
    "get_token_exchange_service",
    "get_auth_context",
    # Authorization
    "AuthorizationError",
    "require_role",
    "require_any_role",
    "require_all_roles",
    "require_resource_role",
    "require_custom_check",
    "AuthorizationHelper",
    "format_authorization_error",
]
