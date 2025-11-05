"""
Pytest configuration and fixtures for testing.
"""

import pytest
import os
from typing import Generator


@pytest.fixture(autouse=True)
def clean_env(monkeypatch) -> Generator:
    """
    Clean environment variables before each test.

    This prevents tests from being affected by actual environment variables.
    """
    # Store original env
    original_env = dict(os.environ)

    # Clear relevant env vars
    env_vars_to_clear = [
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID",
        "AZURE_BASE_URL",
        "AZURE_REQUIRED_SCOPES",
        "SERVER_NAME",
        "ENVIRONMENT",
        "DEBUG",
        "ENABLE_AUTH",
        "PORT",
        "HOST",
        "TRANSPORT",
    ]

    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)

    yield

    # Restore original env (cleanup)
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_azure_env(monkeypatch):
    """Provide mock Azure environment variables."""
    monkeypatch.setenv("AZURE_CLIENT_ID", "mock-client-id")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "mock-client-secret")
    monkeypatch.setenv("AZURE_TENANT_ID", "mock-tenant-id")
    monkeypatch.setenv("AZURE_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("AZURE_REQUIRED_SCOPES", "read,write")
    return {
        "client_id": "mock-client-id",
        "client_secret": "mock-client-secret",
        "tenant_id": "mock-tenant-id",
    }
