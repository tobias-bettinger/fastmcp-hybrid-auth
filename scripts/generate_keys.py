#!/usr/bin/env python3
"""
Generate cryptographic keys for the FastMCP server.

This script generates:
1. JWT signing key for session persistence
2. Fernet encryption key for Redis token storage
"""

import secrets
from cryptography.fernet import Fernet


def main():
    """Generate and display cryptographic keys."""
    print("=" * 70)
    print("FastMCP Server - Cryptographic Key Generator")
    print("=" * 70)
    print()

    # Generate JWT signing key
    jwt_key = secrets.token_urlsafe(32)
    print("1. JWT Signing Key (for session persistence):")
    print("-" * 70)
    print(f"JWT_SIGNING_KEY={jwt_key}")
    print()

    # Generate Fernet encryption key
    fernet_key = Fernet.generate_key().decode()
    print("2. Storage Encryption Key (for Redis token encryption):")
    print("-" * 70)
    print(f"STORAGE_ENCRYPTION_KEY={fernet_key}")
    print()

    print("=" * 70)
    print("Add these to your .env file:")
    print("=" * 70)
    print(f"JWT_SIGNING_KEY={jwt_key}")
    print(f"STORAGE_ENCRYPTION_KEY={fernet_key}")
    print()
    print("⚠️  IMPORTANT: Keep these keys secret and never commit them to git!")
    print("=" * 70)


if __name__ == "__main__":
    main()
