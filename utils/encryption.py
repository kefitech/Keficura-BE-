"""
Hospital Information System - Data Encryption Utilities
======================================================

Author: Athul Gopan
Created: 2025
Module: Symmetric Encryption for Sensitive Data

This module provides symmetric encryption/decryption utilities for protecting
sensitive healthcare data such as patient information, medical records, and
personal identifiable information (PII).

Encryption Method:
    - Uses Fernet (symmetric encryption) from the cryptography library
    - Fernet guarantees that data encrypted cannot be manipulated or read without the key
    - Uses AES-128 in CBC mode with PKCS7 padding and HMAC for authentication

Security Features:
    - Symmetric key encryption
    - Built-in message authentication (prevents tampering)
    - Time-based token expiration support
    - Cryptographically secure key generation

Functions Available:
    - encrypt_data(data): Encrypts a string and returns encrypted string
    - decrypt_data(encrypted_data): Decrypts an encrypted string and returns original data

IMPORTANT SECURITY NOTES:
    - The ENCRYPTION_KEY must be kept secret and secure
    - Store ENCRYPTION_KEY in environment variables, not in code
    - Backup the encryption key securely - lost keys mean lost data
    - Use different keys for development, staging, and production
    - Rotate encryption keys periodically following security best practices

Configuration Required:
    - ENCRYPTION_KEY in settings.py (must be a valid Fernet key)
    - Key should be generated using: Fernet.generate_key()

Example Key Generation:
    >>> from cryptography.fernet import Fernet
    >>> key = Fernet.generate_key()
    >>> print(key.decode())  # Add this to your .env file
"""

from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os

# ============================================================================
# ENCRYPTION KEY CONFIGURATION
# ============================================================================

# Load encryption key from settings or generate a new one (not recommended for production)
# WARNING: If a new key is generated on each application restart, previously encrypted
# data will become unrecoverable. Always use a persistent key from settings/environment.
ENCRYPTION_KEY = settings.ENCRYPTION_KEY or Fernet.generate_key()


# ============================================================================
# ENCRYPTION FUNCTIONS
# ============================================================================

def encrypt_data(data: str) -> str:
    """
    Encrypt a string using Fernet symmetric encryption.

    This function takes a plain text string and encrypts it using the
    configured ENCRYPTION_KEY. The encrypted data can only be decrypted
    using the same key.

    Args:
        data (str): Plain text string to encrypt

    Returns:
        str: Base64-encoded encrypted string

    Raises:
        TypeError: If data is not a string
        Exception: If encryption fails

    Example:
        >>> sensitive_data = "Patient SSN: 123-45-6789"
        >>> encrypted = encrypt_data(sensitive_data)
        >>> print(encrypted)
        'gAAAAABh5x7Y9...[encrypted string]...'

    Use Cases:
        - Encrypting patient Social Security Numbers
        - Encrypting medical record numbers
        - Encrypting sensitive personal information
        - Encrypting payment information

    Security Note:
        The returned encrypted string is safe to store in databases or
        transmit over networks, but should still be handled with care.
    """
    # Initialize Fernet cipher with the encryption key
    f = Fernet(ENCRYPTION_KEY)

    # Encrypt the data (convert string to bytes, encrypt, convert back to string)
    encrypted_data = f.encrypt(data.encode())

    # Return encrypted data as a string (base64-encoded)
    return encrypted_data.decode()


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt a Fernet-encrypted string back to plain text.

    This function takes an encrypted string (previously encrypted with
    encrypt_data) and decrypts it using the configured ENCRYPTION_KEY.

    Args:
        encrypted_data (str): Base64-encoded encrypted string

    Returns:
        str: Original plain text string

    Raises:
        cryptography.fernet.InvalidToken: If the encrypted data is invalid,
            corrupted, or was encrypted with a different key
        Exception: If decryption fails

    Example:
        >>> encrypted = 'gAAAAABh5x7Y9...[encrypted string]...'
        >>> decrypted = decrypt_data(encrypted)
        >>> print(decrypted)
        'Patient SSN: 123-45-6789'

    Use Cases:
        - Decrypting stored patient information for display
        - Decrypting medical records for authorized access
        - Decrypting sensitive data for processing

    Security Note:
        Only decrypt data when absolutely necessary and ensure proper
        access controls are in place before displaying decrypted data.

    Error Handling:
        If you receive InvalidToken error, it means:
        - The data was encrypted with a different key
        - The data has been corrupted or tampered with
        - The encryption key has been changed since encryption
    """
    # Initialize Fernet cipher with the encryption key
    f = Fernet(ENCRYPTION_KEY)

    # Decrypt the data (convert string to bytes, decrypt, convert back to string)
    decrypted_data = f.decrypt(encrypted_data.encode())

    # Return decrypted data as a string
    return decrypted_data.decode()