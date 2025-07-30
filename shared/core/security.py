import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from shared.core.config import settings


def get_or_generate_key() -> bytes:
    """
    Get the Fernet key from environment or generate a new one.

    IMPORTANT: This key must remain consistent across application restarts
    to decrypt previously encrypted data. When a new key is generated,
    save it to your environment variables or secure storage.

    Returns:
        bytes: A valid Fernet key (32 bytes, URL-safe base64-encoded)
    """
    # Check if we have a valid key in settings
    if settings.FERNET_KEY and settings.FERNET_KEY != "fernet-key":
        try:
            # Validate the key by attempting to initialize Fernet with it
            key = settings.FERNET_KEY.encode()
            Fernet(key)
            return key
        except (ValueError, TypeError):
            # Key is invalid, we'll generate a new one
            pass

    # Generate a new key using Fernet's built-in key generation
    # This creates a cryptographically secure random key
    key = Fernet.generate_key()

    print("\n" + "!" * 80)
    print("WARNING: Generated new Fernet key.")
    print("This key MUST be saved and reused for all future application runs.")
    print(
        "Otherwise, you will not be able to decrypt previously encrypted data!"
    )
    print(f"Set this in your environment variables: FERNET_KEY={key.decode()}")
    print("!" * 80 + "\n")

    return key


# Initialize Fernet with a valid key
fernet = Fernet(get_or_generate_key())


def encrypt_data(data: str) -> str:
    """
    Encrypt a string using Fernet symmetric encryption.

    Args:
        data: The string to encrypt

    Returns:
        str: The encrypted data as a string
    """
    if not data:
        return ""
    return fernet.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt a Fernet-encrypted string.

    Args:
        encrypted_data: The encrypted string to decrypt

    Returns:
        Optional[str]: The decrypted string, or None if decryption failed

    Raises:
        ValueError: If the data has been tampered with or is corrupted
    """
    if not encrypted_data:
        return ""

    try:
        return fernet.decrypt(encrypted_data.encode()).decode()
    except InvalidToken:
        # Handle the case where token is invalid (tampered with or corrupted)
        raise ValueError(
            "Failed to decrypt data: token may be invalid or corrupted"
        )
    except Exception as e:
        # Handle other potential errors
        raise ValueError(f"Decryption error: {str(e)}")


def generate_searchable_hash(value: str) -> str:
    """
    Generate a deterministic hash for a string value.
    This is used for creating searchable hashes of encrypted values.

    Args:
        value: The string to hash

    Returns:
        str: A hexadecimal hash string
    """
    if not value:
        return ""
    # Using SHA-256 for a good balance of security and performance
    # For case-insensitive comparisons, convert to lowercase before hashing
    normalized_value = value.lower().strip()
    return hashlib.sha256(normalized_value.encode()).hexdigest()


def hash_data(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def encrypt_dict_values(data: dict) -> dict:
    return {key: encrypt_data(value) for key, value in data.items()}


def decrypt_dict_values(data: dict) -> dict:
    return {key: decrypt_data(value) for key, value in data.items()}


# Unused Code Functions for Encryption Algorithms
def encrypt_aes256(plaintext: str, key: str) -> str:
    """
    Encrypt a string using AES-256 encryption.

    Args:
        plaintext (str): The text to encrypt
        key (str): The encryption key

    Returns:
        str: Base64-encoded encrypted string

    Raises:
        ValueError: If encryption fails

    Example:
        >>> encrypted = encrypt_aes256("sensitive data", "encryption_key")
    """
    try:
        # Convert inputs to bytes
        plaintext_bytes = plaintext.encode("utf-8")
        key_bytes = (
            base64.b64decode(key) if len(key) != 32 else key.encode("utf-8")
        )

        # Generate a random initialization vector
        iv = os.urandom(16)

        # Create a padder
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext_bytes) + padder.finalize()

        # Create an encryptor
        cipher = Cipher(
            algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend()
        )
        encryptor = cipher.encryptor()

        # Encrypt the data
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # Combine IV and ciphertext and encode as base64
        encrypted_data = base64.b64encode(iv + ciphertext).decode("utf-8")

        return encrypted_data
    except Exception as e:
        raise ValueError(f"Encryption failed: {str(e)}") from e


def decrypt_aes256(ciphertext: str, key: str) -> str:
    """
    Decrypt an AES-256 encrypted string.

    Args:
        ciphertext (str): Base64-encoded encrypted string
        key (str): The encryption key

    Returns:
        str: Decrypted plaintext

    Raises:
        ValueError: If decryption fails

    Example:
        >>> decrypted = decrypt_aes256(encrypted_text, "encryption_key")
    """
    try:
        # Convert inputs to bytes
        ciphertext_bytes = base64.b64decode(ciphertext)
        key_bytes = (
            base64.b64decode(key) if len(key) != 32 else key.encode("utf-8")
        )

        # Extract IV (first 16 bytes)
        iv = ciphertext_bytes[:16]
        actual_ciphertext = ciphertext_bytes[16:]

        # Create a decryptor
        cipher = Cipher(
            algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend()
        )
        decryptor = cipher.decryptor()

        # Decrypt the data
        padded_data = decryptor.update(actual_ciphertext) + decryptor.finalize()

        # Remove padding
        unpadder = padding.PKCS7(128).unpadder()
        plaintext_bytes = unpadder.update(padded_data) + unpadder.finalize()

        # Convert back to string
        return plaintext_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}") from e
