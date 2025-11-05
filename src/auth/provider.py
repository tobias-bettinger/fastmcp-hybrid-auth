"""
Authentication provider setup for Azure Entra ID.

This module configures the FastMCP authentication provider with proper
token storage, encryption, and production-ready settings.
"""

import os
import logging
from typing import Optional
from fastmcp.server.auth.providers.azure import AzureProvider

from src.config import AzureAuthConfig

logger = logging.getLogger(__name__)


def create_azure_auth_provider(
    config: AzureAuthConfig,
    redis_host: Optional[str] = None,
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: Optional[str] = None,
    storage_encryption_key: Optional[str] = None,
) -> AzureProvider:
    """
    Create and configure an Azure authentication provider.

    Args:
        config: Azure authentication configuration
        redis_host: Optional Redis host for persistent token storage
        redis_port: Redis port (default: 6379)
        redis_db: Redis database number (default: 0)
        redis_password: Optional Redis password
        storage_encryption_key: Required if using Redis - Fernet encryption key

    Returns:
        Configured AzureProvider instance

    Raises:
        ValueError: If Redis is configured but encryption key is missing
    """
    # Base provider kwargs
    provider_kwargs = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "tenant_id": config.tenant_id,
        "base_url": config.base_url,
        "required_scopes": config.required_scopes,
        "redirect_path": config.redirect_path,
    }

    # Add optional parameters
    if config.identifier_uri:
        provider_kwargs["identifier_uri"] = config.identifier_uri

    if config.additional_authorize_scopes:
        provider_kwargs["additional_authorize_scopes"] = config.additional_authorize_scopes

    if config.base_authority:
        provider_kwargs["base_authority"] = config.base_authority

    if config.jwt_signing_key:
        provider_kwargs["jwt_signing_key"] = config.jwt_signing_key
        logger.info("JWT signing key configured for session persistence")

    # Configure Redis storage for production
    if redis_host:
        if not storage_encryption_key:
            raise ValueError(
                "STORAGE_ENCRYPTION_KEY is required when using Redis. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        try:
            from key_value.aio.stores.redis import RedisStore
            from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
            from cryptography.fernet import Fernet

            # Create Redis store
            redis_store = RedisStore(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
            )

            # Wrap with encryption
            provider_kwargs["client_storage"] = FernetEncryptionWrapper(
                key_value=redis_store,
                fernet=Fernet(storage_encryption_key.encode() if isinstance(storage_encryption_key, str) else storage_encryption_key),
            )

            logger.info(
                "Redis token storage configured with encryption",
                extra={
                    "redis_host": redis_host,
                    "redis_port": redis_port,
                    "redis_db": redis_db,
                },
            )
        except ImportError as e:
            logger.warning(
                f"Redis storage dependencies not installed: {e}. "
                "Install with: pip install key-value-py[redis] cryptography"
            )
            logger.warning("Falling back to in-memory token storage")

    # Create and return provider
    provider = AzureProvider(**provider_kwargs)

    logger.info(
        "Azure auth provider created",
        extra={
            "tenant_id": config.tenant_id,
            "client_id": config.client_id,
            "base_url": config.base_url,
            "required_scopes": config.required_scopes,
            "has_redis": redis_host is not None,
        },
    )

    return provider


def get_user_info_from_token() -> dict:
    """
    Extract user information from the current access token.

    This function should be called from within a tool handler that has
    access to the request context.

    Returns:
        Dictionary with user information from Azure token claims
    """
    from fastmcp.server.dependencies import get_access_token

    token = get_access_token()

    return {
        "azure_id": token.claims.get("sub"),
        "email": token.claims.get("email") or token.claims.get("preferred_username"),
        "name": token.claims.get("name"),
        "given_name": token.claims.get("given_name"),
        "family_name": token.claims.get("family_name"),
        "job_title": token.claims.get("job_title"),
        "office_location": token.claims.get("office_location"),
        "tenant_id": token.claims.get("tid"),
        "oid": token.claims.get("oid"),  # Object ID
    }
