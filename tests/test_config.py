"""
Tests for configuration module.

Example tests to demonstrate testing patterns for the boilerplate.
"""

import os
import pytest
from src.config import ServerConfig, AzureAuthConfig


class TestAzureAuthConfig:
    """Test Azure authentication configuration."""

    def test_parse_scopes_comma_separated(self):
        """Test parsing comma-separated scopes."""
        scopes = AzureAuthConfig._parse_scopes("read,write,admin")
        assert scopes == ["read", "write", "admin"]

    def test_parse_scopes_space_separated(self):
        """Test parsing space-separated scopes."""
        scopes = AzureAuthConfig._parse_scopes("read write admin")
        assert scopes == ["read", "write", "admin"]

    def test_parse_scopes_json(self):
        """Test parsing JSON array scopes."""
        scopes = AzureAuthConfig._parse_scopes('["read", "write", "admin"]')
        assert scopes == ["read", "write", "admin"]

    def test_parse_scopes_mixed_whitespace(self):
        """Test parsing with extra whitespace."""
        scopes = AzureAuthConfig._parse_scopes("  read , write  , admin  ")
        assert scopes == ["read", "write", "admin"]

    def test_from_env_missing_credentials(self, monkeypatch):
        """Test that missing credentials raises ValueError."""
        monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
        monkeypatch.delenv("AZURE_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("AZURE_TENANT_ID", raising=False)

        with pytest.raises(ValueError, match="Missing required Azure auth configuration"):
            AzureAuthConfig.from_env()

    def test_from_env_with_credentials(self, monkeypatch):
        """Test loading configuration from environment."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "test-secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "test-tenant")
        monkeypatch.setenv("AZURE_REQUIRED_SCOPES", "read,write")

        config = AzureAuthConfig.from_env()

        assert config.client_id == "test-client-id"
        assert config.client_secret == "test-secret"
        assert config.tenant_id == "test-tenant"
        assert config.required_scopes == ["read", "write"]


class TestServerConfig:
    """Test server configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ServerConfig()

        assert config.name == "FastMCP Boilerplate Server"
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.transport == "http"
        assert config.environment == "development"
        assert config.debug is False

    def test_is_production(self):
        """Test production environment detection."""
        config = ServerConfig(environment="production")
        assert config.is_production is True
        assert config.is_development is False

    def test_is_development(self):
        """Test development environment detection."""
        config = ServerConfig(environment="development")
        assert config.is_development is True
        assert config.is_production is False

    def test_validate_invalid_port(self):
        """Test validation with invalid port."""
        config = ServerConfig(port=99999)

        with pytest.raises(ValueError, match="Invalid port number"):
            config.validate()

    def test_validate_invalid_transport(self):
        """Test validation with invalid transport."""
        config = ServerConfig(transport="invalid")

        with pytest.raises(ValueError, match="Invalid transport"):
            config.validate()

    def test_validate_production_without_https(self, monkeypatch):
        """Test warning for production without HTTPS."""
        monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "test-secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "test-tenant")

        azure_config = AzureAuthConfig.from_env()
        config = ServerConfig(
            environment="production",
            enable_auth=True,
            azure_auth=azure_config,
        )

        # Should not raise, but will log warning
        config.validate()

    def test_from_env(self, monkeypatch):
        """Test loading server configuration from environment."""
        monkeypatch.setenv("SERVER_NAME", "Test Server")
        monkeypatch.setenv("PORT", "9000")
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("ENABLE_AUTH", "false")

        config = ServerConfig.from_env()

        assert config.name == "Test Server"
        assert config.port == 9000
        assert config.environment == "staging"
        assert config.debug is True
        assert config.enable_auth is False
