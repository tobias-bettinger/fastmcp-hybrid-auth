"""
Example tools demonstrating various FastMCP tool patterns.

These tools serve as templates for implementing your own business logic.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastmcp import FastMCP

from src.auth.provider import get_user_info_from_token

logger = logging.getLogger(__name__)


def register_example_tools(mcp: FastMCP) -> None:
    """
    Register example tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    def calculate(
        operation: str,
        a: float,
        b: float,
    ) -> Dict[str, Any]:
        """
        Perform a mathematical calculation.

        Args:
            operation: The operation to perform (add, subtract, multiply, divide)
            a: First number
            b: Second number

        Returns:
            Dictionary with the result and operation details
        """
        logger.info(f"Calculate tool called: {operation}({a}, {b})")

        operations = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else None,
        }

        if operation not in operations:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}. Available: {list(operations.keys())}",
            }

        try:
            result = operations[operation](a, b)
            if result is None:
                return {
                    "success": False,
                    "error": "Division by zero",
                }

            return {
                "success": True,
                "operation": operation,
                "operands": {"a": a, "b": b},
                "result": result,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            logger.error(f"Calculation error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def get_current_user() -> Dict[str, Any]:
        """
        Get information about the currently authenticated Azure user.

        This tool demonstrates how to access user information from the
        authentication token within a tool handler.

        Returns:
            Dictionary with user information from Azure Entra ID
        """
        try:
            user_info = get_user_info_from_token()
            logger.info(f"User info retrieved for: {user_info.get('email')}")

            return {
                "success": True,
                "user": user_info,
                "retrieved_at": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            logger.error(f"Error getting user info: {e}", exc_info=True)
            return {
                "success": False,
                "error": "Could not retrieve user information. Ensure authentication is enabled.",
            }

    @mcp.tool()
    async def process_data(
        data: List[str],
        operation: str = "uppercase",
    ) -> Dict[str, Any]:
        """
        Process a list of strings with various operations.

        Args:
            data: List of strings to process
            operation: Operation to perform (uppercase, lowercase, reverse, length)

        Returns:
            Dictionary with processed results
        """
        logger.info(f"Processing {len(data)} items with operation: {operation}")

        operations = {
            "uppercase": lambda x: x.upper(),
            "lowercase": lambda x: x.lower(),
            "reverse": lambda x: x[::-1],
            "length": lambda x: len(x),
        }

        if operation not in operations:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}. Available: {list(operations.keys())}",
            }

        try:
            processed = [operations[operation](item) for item in data]

            return {
                "success": True,
                "operation": operation,
                "input_count": len(data),
                "results": processed,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            logger.error(f"Data processing error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    async def validate_input(
        text: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate text input against various criteria.

        Args:
            text: Text to validate
            min_length: Minimum required length
            max_length: Maximum allowed length
            pattern: Optional regex pattern to match

        Returns:
            Dictionary with validation results
        """
        import re

        logger.info(f"Validating input of length {len(text)}")

        errors = []

        if min_length is not None and len(text) < min_length:
            errors.append(f"Text is too short (minimum {min_length} characters)")

        if max_length is not None and len(text) > max_length:
            errors.append(f"Text is too long (maximum {max_length} characters)")

        if pattern is not None:
            try:
                if not re.match(pattern, text):
                    errors.append(f"Text does not match required pattern: {pattern}")
            except re.error as e:
                errors.append(f"Invalid regex pattern: {e}")

        is_valid = len(errors) == 0

        return {
            "success": True,
            "is_valid": is_valid,
            "text_length": len(text),
            "errors": errors if not is_valid else None,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    logger.info("Example tools registered successfully")
