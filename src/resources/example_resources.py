"""
Example resources demonstrating various FastMCP resource patterns.

Resources provide read-only data and context to LLMs through URIs.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_example_resources(mcp: FastMCP) -> None:
    """
    Register example resources with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.resource("config://server")
    async def get_server_config() -> str:
        """
        Provide server configuration information.

        URI: config://server

        Returns:
            Server configuration as formatted text
        """
        from src.config import get_config

        config = get_config()

        return f"""
# Server Configuration

**Name:** {config.name}
**Description:** {config.description}
**Environment:** {config.environment}
**Debug Mode:** {config.debug}

## Network Settings
- Host: {config.host}
- Port: {config.port}
- Transport: {config.transport}

## Authentication
- Enabled: {config.enable_auth}
- Provider: {"Azure Entra ID" if config.azure_auth else "None"}

## Logging
- Level: {config.log_level}
- Format: {config.log_format}

*Retrieved at: {datetime.utcnow().isoformat()}Z*
"""

    @mcp.resource("status://health")
    async def get_health_status() -> str:
        """
        Provide server health status.

        URI: status://health

        Returns:
            Health status information
        """
        return f"""
# Server Health Status

**Status:** Healthy ✓
**Timestamp:** {datetime.utcnow().isoformat()}Z
**Uptime:** Active

## Components
- MCP Server: Running
- Authentication: Active
- Resources: Available
- Tools: Registered

All systems operational.
"""

    @mcp.resource("docs://api/tools")
    async def get_tools_documentation() -> str:
        """
        Provide documentation for available tools.

        URI: docs://api/tools

        Returns:
            Tools documentation as formatted text
        """
        return """
# Available Tools Documentation

## calculate
Perform mathematical calculations (add, subtract, multiply, divide).

**Parameters:**
- `operation` (string): Operation type
- `a` (number): First operand
- `b` (number): Second operand

**Example:**
```json
{
  "operation": "add",
  "a": 5,
  "b": 3
}
```

## get_current_user
Retrieve information about the authenticated Azure user.

**Parameters:** None

**Returns:** User profile from Azure Entra ID token

## process_data
Process a list of strings with various operations.

**Parameters:**
- `data` (array): List of strings
- `operation` (string): Operation type (uppercase, lowercase, reverse, length)

## validate_input
Validate text input against criteria.

**Parameters:**
- `text` (string): Text to validate
- `min_length` (number, optional): Minimum length
- `max_length` (number, optional): Maximum length
- `pattern` (string, optional): Regex pattern

---

For more information, consult the server documentation.
"""

    @mcp.resource("template://user/{user_id}/profile")
    async def get_user_profile(user_id: str) -> str:
        """
        Provide user profile template (demonstrates dynamic URI templates).

        URI: template://user/{user_id}/profile

        Args:
            user_id: The user identifier

        Returns:
            User profile information (mock data for demonstration)
        """
        logger.info(f"User profile requested for: {user_id}")

        # In a real implementation, this would fetch from a database
        return f"""
# User Profile

**User ID:** {user_id}
**Status:** Active
**Last Accessed:** {datetime.utcnow().isoformat()}Z

## Notes
This is a template resource demonstrating dynamic URI parameters.
In production, this would fetch real user data from your backend.

**Template URI Pattern:** `template://user/{{user_id}}/profile`
"""

    @mcp.resource("data://sample/json")
    async def get_sample_json() -> Dict[str, Any]:
        """
        Provide sample structured data.

        URI: data://sample/json

        Returns:
            Sample JSON data structure
        """
        return {
            "type": "sample_data",
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {
                "items": [
                    {"id": 1, "name": "Item One", "active": True},
                    {"id": 2, "name": "Item Two", "active": False},
                    {"id": 3, "name": "Item Three", "active": True},
                ],
                "metadata": {
                    "total_count": 3,
                    "active_count": 2,
                    "source": "example_resources",
                },
            },
            "description": "This is sample structured data returned as JSON",
        }

    logger.info("Example resources registered successfully")
