"""
Main FastMCP Server Implementation.

This is the entry point for the MCP server. It initializes the server,
configures authentication, registers tools and resources, and starts the server.
"""

import logging
import sys
from typing import Optional
from fastmcp import FastMCP

from src.config import get_config
from src.utils.logging_config import setup_logging
from src.auth.provider import create_azure_auth_provider
from src.auth.keycloak_client import KeycloakClient
from src.auth.token_exchange import initialize_token_exchange_service
from src.tools.example_tools import register_example_tools
from src.tools.authorized_tools import register_authorized_tools
from src.resources.example_resources import register_example_resources

logger = logging.getLogger(__name__)


def create_server() -> FastMCP:
    """
    Create and configure the FastMCP server.

    Returns:
        Configured FastMCP server instance
    """
    # Load configuration
    config = get_config()

    # Setup logging
    setup_logging(
        level=config.log_level,
        format_type=config.log_format,
        log_file=config.log_file,
    )

    logger.info(
        "Initializing MCP server",
        extra={
            "name": config.name,
            "environment": config.environment,
            "auth_enabled": config.enable_auth,
        },
    )

    # Create auth provider if enabled
    auth_provider = None
    if config.enable_auth and config.azure_auth:
        try:
            auth_provider = create_azure_auth_provider(
                config=config.azure_auth,
                redis_host=config.redis_host,
                redis_port=config.redis_port,
                redis_db=config.redis_db,
                redis_password=config.redis_password,
                storage_encryption_key=config.storage_encryption_key,
            )
            logger.info("Authentication provider configured successfully")
        except Exception as e:
            logger.error(f"Failed to create auth provider: {e}", exc_info=True)
            if config.is_production:
                logger.critical("Cannot start production server without authentication")
                sys.exit(1)
            logger.warning("Starting server without authentication")

    # Initialize Keycloak authorization if enabled
    if config.enable_keycloak and config.keycloak:
        try:
            keycloak_client = KeycloakClient(
                server_url=config.keycloak.server_url,
                realm=config.keycloak.realm,
                client_id=config.keycloak.client_id,
                client_secret=config.keycloak.client_secret,
                verify_ssl=config.keycloak.verify_ssl,
            )

            # Initialize token exchange service
            initialize_token_exchange_service(keycloak_client)

            logger.info(
                "Keycloak authorization configured successfully",
                extra={
                    "server_url": config.keycloak.server_url,
                    "realm": config.keycloak.realm,
                    "token_exchange": config.keycloak.enable_token_exchange,
                }
            )
        except Exception as e:
            logger.error(f"Failed to initialize Keycloak: {e}", exc_info=True)
            if config.is_production:
                logger.critical("Cannot start production server without Keycloak authorization")
                sys.exit(1)
            logger.warning("Starting server without Keycloak authorization")

    # Create FastMCP server
    mcp = FastMCP(
        name=config.name,
        auth=auth_provider,
    )

    # Register tools
    logger.info("Registering tools...")
    register_example_tools(mcp)

    # Register authorized tools if Keycloak is enabled
    if config.enable_keycloak:
        logger.info("Registering authorized tools...")
        register_authorized_tools(mcp)

    # Register resources
    logger.info("Registering resources...")
    register_example_resources(mcp)

    # Add server info tool
    @mcp.tool()
    async def get_server_info() -> dict:
        """
        Get information about the MCP server.

        Returns:
            Dictionary with server metadata and capabilities
        """
        return {
            "name": config.name,
            "description": config.description,
            "environment": config.environment,
            "version": "1.0.0",
            "authentication": {
                "enabled": config.enable_auth,
                "provider": "Azure Entra ID" if config.azure_auth else None,
            },
            "authorization": {
                "enabled": config.enable_keycloak,
                "provider": "Keycloak" if config.keycloak else None,
                "realm": config.keycloak.realm if config.keycloak else None,
            },
            "transport": config.transport,
            "features": {
                "tools": True,
                "resources": True,
                "prompts": False,  # Can be extended
                "authorization": config.enable_keycloak,
            },
        }

    logger.info(
        "Server initialization complete",
        extra={
            "tools_count": len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else "unknown",
            "resources_count": len(mcp._resource_manager._resources) if hasattr(mcp, "_resource_manager") else "unknown",
        },
    )

    return mcp


def main() -> None:
    """
    Main entry point for the server.

    This function creates the server and runs it with the configured transport.
    """
    try:
        # Create server
        mcp = create_server()

        # Get configuration
        config = get_config()

        # Run server
        logger.info(
            f"Starting MCP server on {config.host}:{config.port} with {config.transport} transport"
        )

        # The actual server run is handled by FastMCP's CLI or programmatically
        # For CLI usage: fastmcp run src/server.py --transport http --port 8000
        # For programmatic usage:
        mcp.run(
            transport=config.transport,
            host=config.host if config.transport in ("http", "sse") else None,
            port=config.port if config.transport in ("http", "sse") else None,
        )

    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


# Create module-level mcp instance for fastmcp CLI
mcp = create_server()

if __name__ == "__main__":
    main()
