import pytest

from shared.core.security import decrypt_data, encrypt_data


def test_encrypt_decrypt_cycle():
    """Test that data can be encrypted and then decrypted back to original."""
    original_data = "sensitive information 123!@#"

    # Encrypt the data
    encrypted = encrypt_data(original_data)

    # Verify encrypted data is different from original
    assert encrypted != original_data

    # Decrypt the data
    decrypted = decrypt_data(encrypted)

    # Verify decrypted data matches original
    assert decrypted == original_data


def test_empty_string_handling():
    """Test that empty strings are handled properly."""
    # Empty string encryption should return empty string
    assert encrypt_data("") == ""

    # Empty string decryption should return empty string
    assert decrypt_data("") == ""


def test_invalid_token_handling():
    """Test that invalid tokens raise appropriate errors."""
    # Create some valid encrypted data
    valid_encrypted = encrypt_data("test data")

    # Tamper with the encrypted data
    tampered_data = valid_encrypted[:-5] + "XXXXX"

    # Attempt to decrypt should raise ValueError
    with pytest.raises(ValueError):
        decrypt_data(tampered_data)
