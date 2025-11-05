"""
Authorization decorators and helpers for role-based access control.

This module provides decorators and utilities for enforcing authorization
policies on MCP tools using Keycloak roles and permissions.
"""

import logging
from typing import Callable, List, Optional, Any
from functools import wraps

from src.auth.token_exchange import get_auth_context
from src.auth.keycloak_client import KeycloakToken

logger = logging.getLogger(__name__)


class AuthorizationError(Exception):
    """Raised when authorization check fails."""

    def __init__(self, message: str, required_roles: Optional[List[str]] = None):
        """
        Initialize authorization error.

        Args:
            message: Error message
            required_roles: List of required roles that were missing
        """
        self.message = message
        self.required_roles = required_roles or []
        super().__init__(self.message)


def require_role(role: str):
    """
    Decorator to require a specific Keycloak realm role.

    Args:
        role: The role name required

    Example:
        @mcp.tool()
        @require_role("data_reader")
        async def read_sensitive_data() -> dict:
            # Only users with "data_reader" role can execute
            return {"data": "..."}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                ctx = await get_auth_context()
                keycloak_client = ctx.keycloak_token

                if not any(role == r for r in ctx.roles):
                    logger.warning(
                        f"Authorization failed: User {ctx.email} missing role '{role}'"
                    )
                    raise AuthorizationError(
                        f"Insufficient permissions. Required role: {role}",
                        required_roles=[role]
                    )

                logger.debug(f"Authorization passed for role '{role}'")
                return await func(*args, **kwargs)

            except AuthorizationError:
                raise
            except Exception as e:
                logger.error(f"Authorization check failed: {e}", exc_info=True)
                raise AuthorizationError(f"Authorization check failed: {str(e)}")

        return wrapper
    return decorator


def require_any_role(roles: List[str]):
    """
    Decorator to require ANY of the specified roles.

    Args:
        roles: List of role names (user needs at least one)

    Example:
        @mcp.tool()
        @require_any_role(["admin", "supervisor", "data_manager"])
        async def manage_data() -> dict:
            # Users with admin OR supervisor OR data_manager can execute
            return {"status": "ok"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                ctx = await get_auth_context()
                user_roles = set(ctx.roles)
                required_roles_set = set(roles)

                if not user_roles.intersection(required_roles_set):
                    logger.warning(
                        f"Authorization failed: User {ctx.email} missing any of roles {roles}"
                    )
                    raise AuthorizationError(
                        f"Insufficient permissions. Required any of: {', '.join(roles)}",
                        required_roles=roles
                    )

                logger.debug(f"Authorization passed for any of roles {roles}")
                return await func(*args, **kwargs)

            except AuthorizationError:
                raise
            except Exception as e:
                logger.error(f"Authorization check failed: {e}", exc_info=True)
                raise AuthorizationError(f"Authorization check failed: {str(e)}")

        return wrapper
    return decorator


def require_all_roles(roles: List[str]):
    """
    Decorator to require ALL of the specified roles.

    Args:
        roles: List of role names (user needs all of them)

    Example:
        @mcp.tool()
        @require_all_roles(["finance_access", "executive_level"])
        async def view_financial_data() -> dict:
            # Users need BOTH finance_access AND executive_level
            return {"data": "..."}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                ctx = await get_auth_context()
                user_roles = set(ctx.roles)
                required_roles_set = set(roles)

                missing_roles = required_roles_set - user_roles
                if missing_roles:
                    logger.warning(
                        f"Authorization failed: User {ctx.email} missing roles {missing_roles}"
                    )
                    raise AuthorizationError(
                        f"Insufficient permissions. Missing roles: {', '.join(missing_roles)}",
                        required_roles=list(missing_roles)
                    )

                logger.debug(f"Authorization passed for all roles {roles}")
                return await func(*args, **kwargs)

            except AuthorizationError:
                raise
            except Exception as e:
                logger.error(f"Authorization check failed: {e}", exc_info=True)
                raise AuthorizationError(f"Authorization check failed: {str(e)}")

        return wrapper
    return decorator


def require_resource_role(resource: str, role: str):
    """
    Decorator to require a specific client/resource role.

    Args:
        resource: The resource/client name in Keycloak
        role: The role name within that resource

    Example:
        @mcp.tool()
        @require_resource_role("critical-data-api", "writer")
        async def write_critical_data(data: str) -> dict:
            # User needs "writer" role in "critical-data-api" client
            return {"status": "written"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                ctx = await get_auth_context()
                token = ctx.keycloak_token

                has_access = (
                    resource in token.resource_access and
                    role in token.resource_access[resource].get("roles", [])
                )

                if not has_access:
                    logger.warning(
                        f"Authorization failed: User {ctx.email} missing "
                        f"resource role '{role}' in '{resource}'"
                    )
                    raise AuthorizationError(
                        f"Insufficient permissions. Required: {resource}:{role}"
                    )

                logger.debug(f"Authorization passed for {resource}:{role}")
                return await func(*args, **kwargs)

            except AuthorizationError:
                raise
            except Exception as e:
                logger.error(f"Authorization check failed: {e}", exc_info=True)
                raise AuthorizationError(f"Authorization check failed: {str(e)}")

        return wrapper
    return decorator


def require_custom_check(check_func: Callable[[Any], bool], error_message: str = "Unauthorized"):
    """
    Decorator for custom authorization logic.

    Args:
        check_func: Function that takes AuthContext and returns bool
        error_message: Error message if check fails

    Example:
        def is_from_trusted_tenant(ctx):
            return ctx.entra_claims.get("tid") in TRUSTED_TENANTS

        @mcp.tool()
        @require_custom_check(is_from_trusted_tenant, "Tenant not authorized")
        async def tenant_specific_tool() -> dict:
            return {"data": "..."}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                ctx = await get_auth_context()

                if not check_func(ctx):
                    logger.warning(
                        f"Custom authorization check failed for user {ctx.email}"
                    )
                    raise AuthorizationError(error_message)

                logger.debug("Custom authorization check passed")
                return await func(*args, **kwargs)

            except AuthorizationError:
                raise
            except Exception as e:
                logger.error(f"Authorization check failed: {e}", exc_info=True)
                raise AuthorizationError(f"Authorization check failed: {str(e)}")

        return wrapper
    return decorator


class AuthorizationHelper:
    """Helper class for programmatic authorization checks."""

    @staticmethod
    async def check_role(role: str) -> bool:
        """
        Check if current user has a specific role.

        Args:
            role: Role name to check

        Returns:
            True if user has the role
        """
        try:
            ctx = await get_auth_context()
            return role in ctx.roles
        except Exception as e:
            logger.error(f"Role check failed: {e}")
            return False

    @staticmethod
    async def check_any_role(roles: List[str]) -> bool:
        """
        Check if current user has any of the specified roles.

        Args:
            roles: List of role names

        Returns:
            True if user has at least one role
        """
        try:
            ctx = await get_auth_context()
            return bool(set(ctx.roles).intersection(set(roles)))
        except Exception as e:
            logger.error(f"Role check failed: {e}")
            return False

    @staticmethod
    async def check_all_roles(roles: List[str]) -> bool:
        """
        Check if current user has all of the specified roles.

        Args:
            roles: List of role names

        Returns:
            True if user has all roles
        """
        try:
            ctx = await get_auth_context()
            return set(roles).issubset(set(ctx.roles))
        except Exception as e:
            logger.error(f"Role check failed: {e}")
            return False

    @staticmethod
    async def get_user_roles() -> List[str]:
        """
        Get current user's roles.

        Returns:
            List of role names
        """
        try:
            ctx = await get_auth_context()
            return ctx.roles
        except Exception as e:
            logger.error(f"Failed to get user roles: {e}")
            return []

    @staticmethod
    async def get_user_info() -> dict:
        """
        Get current user's information.

        Returns:
            Dictionary with user info
        """
        try:
            ctx = await get_auth_context()
            return {
                "user_id": ctx.user_id,
                "email": ctx.email,
                "entra_id": ctx.entra_user_id,
                "keycloak_id": ctx.keycloak_user_id,
                "roles": ctx.roles,
            }
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return {}


def format_authorization_error(error: AuthorizationError) -> dict:
    """
    Format authorization error for tool response.

    Args:
        error: AuthorizationError instance

    Returns:
        Formatted error dictionary
    """
    return {
        "success": False,
        "error": "authorization_failed",
        "message": error.message,
        "required_roles": error.required_roles,
    }
