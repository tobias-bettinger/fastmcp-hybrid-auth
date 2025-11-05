"""
Example tools demonstrating Keycloak authorization patterns.

These tools show how to use the authorization decorators to protect
endpoints with role-based access control.
"""

import logging
from typing import Dict, Any
from fastmcp import FastMCP

from src.auth.authorization import (
    require_role,
    require_any_role,
    require_all_roles,
    require_resource_role,
    AuthorizationError,
    AuthorizationHelper,
    format_authorization_error,
)
from src.auth.token_exchange import get_auth_context

logger = logging.getLogger(__name__)


def register_authorized_tools(mcp: FastMCP) -> None:
    """
    Register tools with Keycloak authorization checks.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    @require_role("data_reader")
    async def read_protected_data(query: str) -> Dict[str, Any]:
        """
        Read protected data (requires 'data_reader' role).

        This tool demonstrates single role requirement.
        Only users with the 'data_reader' role can execute this.

        Args:
            query: Data query parameter

        Returns:
            Protected data results
        """
        try:
            logger.info(f"Reading protected data with query: {query}")

            # Get auth context for additional user info
            ctx = await get_auth_context()

            return {
                "success": True,
                "data": {
                    "query": query,
                    "results": [
                        {"id": 1, "value": "Protected Data 1"},
                        {"id": 2, "value": "Protected Data 2"},
                    ],
                    "accessed_by": ctx.email,
                    "user_roles": ctx.roles,
                }
            }

        except AuthorizationError as e:
            logger.warning(f"Authorization failed: {e}")
            return format_authorization_error(e)
        except Exception as e:
            logger.error(f"Error reading protected data: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    @require_role("data_writer")
    async def write_protected_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write protected data (requires 'data_writer' role).

        This tool demonstrates write access control.

        Args:
            data: Data to write

        Returns:
            Write operation result
        """
        try:
            logger.info(f"Writing protected data")

            ctx = await get_auth_context()

            return {
                "success": True,
                "message": "Data written successfully",
                "written_by": ctx.email,
                "data_id": "generated-id-123",
            }

        except AuthorizationError as e:
            return format_authorization_error(e)
        except Exception as e:
            logger.error(f"Error writing protected data: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    @require_any_role(["admin", "supervisor", "data_manager"])
    async def manage_critical_resource(action: str, resource_id: str) -> Dict[str, Any]:
        """
        Manage critical resources (requires admin, supervisor, or data_manager role).

        This tool demonstrates authorization with multiple acceptable roles.

        Args:
            action: Action to perform (view, update, delete)
            resource_id: Resource identifier

        Returns:
            Operation result
        """
        try:
            logger.info(f"Managing resource {resource_id} with action: {action}")

            ctx = await get_auth_context()

            # Check which role the user has
            user_role = None
            for role in ["admin", "supervisor", "data_manager"]:
                if role in ctx.roles:
                    user_role = role
                    break

            return {
                "success": True,
                "action": action,
                "resource_id": resource_id,
                "performed_by": ctx.email,
                "user_role": user_role,
                "message": f"{action.capitalize()} operation completed",
            }

        except AuthorizationError as e:
            return format_authorization_error(e)
        except Exception as e:
            logger.error(f"Error managing resource: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    @require_all_roles(["finance_access", "executive_level"])
    async def view_financial_data(report_type: str) -> Dict[str, Any]:
        """
        View financial data (requires BOTH 'finance_access' AND 'executive_level' roles).

        This tool demonstrates requiring multiple roles simultaneously.

        Args:
            report_type: Type of financial report

        Returns:
            Financial data
        """
        try:
            logger.info(f"Viewing financial report: {report_type}")

            ctx = await get_auth_context()

            return {
                "success": True,
                "report_type": report_type,
                "data": {
                    "revenue": "$1,000,000",
                    "expenses": "$750,000",
                    "profit": "$250,000",
                },
                "accessed_by": ctx.email,
                "clearance_level": "executive",
            }

        except AuthorizationError as e:
            return format_authorization_error(e)
        except Exception as e:
            logger.error(f"Error viewing financial data: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    @require_resource_role("critical-data-api", "writer")
    async def write_to_critical_system(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write to critical on-premise system (requires 'writer' role in 'critical-data-api' client).

        This tool demonstrates client/resource-specific role checking,
        perfect for protecting access to specific on-premise systems.

        Args:
            payload: Data to write to critical system

        Returns:
            Write operation result
        """
        try:
            logger.info("Writing to critical on-premise system")

            ctx = await get_auth_context()

            # Simulate writing to critical system
            # In production, this would make actual API calls to on-premise infrastructure

            return {
                "success": True,
                "message": "Data written to critical system",
                "transaction_id": "crit-txn-789",
                "written_by": ctx.email,
                "system": "critical-data-api",
            }

        except AuthorizationError as e:
            return format_authorization_error(e)
        except Exception as e:
            logger.error(f"Error writing to critical system: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def get_my_authorization_info() -> Dict[str, Any]:
        """
        Get current user's authorization information.

        This tool shows how to programmatically check authorization
        without using decorators.

        Returns:
            User authorization information
        """
        try:
            ctx = await get_auth_context()

            # Use AuthorizationHelper for programmatic checks
            has_admin = await AuthorizationHelper.check_role("admin")
            has_reader = await AuthorizationHelper.check_role("data_reader")

            return {
                "success": True,
                "user": {
                    "email": ctx.email,
                    "entra_id": ctx.entra_user_id,
                    "keycloak_id": ctx.keycloak_user_id,
                },
                "authorization": {
                    "realm_roles": ctx.roles,
                    "resource_access": list(ctx.keycloak_token.resource_access.keys()),
                    "is_admin": has_admin,
                    "is_data_reader": has_reader,
                },
                "token_info": {
                    "expires_at": ctx.keycloak_token.expires_at.isoformat(),
                    "needs_refresh": ctx.keycloak_token.needs_refresh,
                }
            }

        except Exception as e:
            logger.error(f"Error getting authorization info: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def conditional_data_access(sensitivity_level: str) -> Dict[str, Any]:
        """
        Access data with conditional authorization based on sensitivity.

        This demonstrates dynamic authorization logic based on parameters.

        Args:
            sensitivity_level: Data sensitivity (public, internal, confidential, secret)

        Returns:
            Data appropriate for user's authorization level
        """
        try:
            ctx = await get_auth_context()

            # Define role requirements for each sensitivity level
            role_requirements = {
                "public": [],  # No special role needed
                "internal": ["employee"],
                "confidential": ["data_reader", "analyst"],
                "secret": ["executive_level", "security_clearance"],
            }

            required_roles = role_requirements.get(sensitivity_level, [])

            # Check if user has required roles
            if required_roles:
                has_access = await AuthorizationHelper.check_any_role(required_roles)

                if not has_access:
                    return {
                        "success": False,
                        "error": "authorization_failed",
                        "message": f"Insufficient clearance for {sensitivity_level} data",
                        "required_roles": required_roles,
                        "user_roles": ctx.roles,
                    }

            logger.info(f"Granting access to {sensitivity_level} data for {ctx.email}")

            return {
                "success": True,
                "sensitivity_level": sensitivity_level,
                "data": f"Sample {sensitivity_level} data",
                "accessed_by": ctx.email,
                "authorization_level": "granted",
            }

        except Exception as e:
            logger.error(f"Error in conditional data access: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    logger.info("Authorized tools registered successfully")
