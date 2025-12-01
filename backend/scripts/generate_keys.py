#!/usr/bin/env python3
"""
Script para generar claves de seguridad para Balaur SMS
"""
import secrets


def generate_secret_key(length: int = 32) -> str:
    """Genera SECRET_KEY para JWT"""
    return secrets.token_hex(length)


def generate_encryption_key() -> str:
    """Genera ENCRYPTION_KEY para AES-GCM (32 bytes = 64 hex chars)"""
    return secrets.token_hex(32)


if __name__ == "__main__":
    print("=" * 70)
    print("BALAUR SMS - Security Keys Generator")
    print("=" * 70)
    print()
    print("⚠️  IMPORTANT: Store these keys securely!")
    print("⚠️  DO NOT commit these keys to version control!")
    print("⚠️  Add them to your .env file")
    print()
    print("-" * 70)
    print("SECRET_KEY (for JWT signing):")
    print("-" * 70)
    print(generate_secret_key())
    print()
    print("-" * 70)
    print("ENCRYPTION_KEY (for license encryption - must be 64 hex chars):")
    print("-" * 70)
    print(generate_encryption_key())
    print()
    print("=" * 70)
    print("Copy these values to your .env file:")
    print("=" * 70)
    # Generate once and reuse so printed values match the ones shown above
    secret = generate_secret_key()
    encryption = generate_encryption_key()

    print(f"SECRET_KEY={secret}")
    print(f"ENCRYPTION_KEY={encryption}")
    print()