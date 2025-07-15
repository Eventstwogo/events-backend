import os
import stat
import sys
import uuid
from datetime import datetime, timedelta

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class KeyManager:
    """
    Manages generation, storage, and retrieval of RSA keys.
    """

    def __init__(self, key_dir: str = "keys", key_refresh_days: int = 30):
        """
        Initializes the KeyManager and ensures keys are up-to-date.

        :param key_dir: Directory to store the keys.
        :param key_refresh_days: Number of days after which keys should be refreshed.
        """
        self.key_dir = key_dir
        self.key_refresh_days = key_refresh_days
        self.private_key_path = os.path.join(key_dir, "private_key.pem")
        self.public_key_path = os.path.join(key_dir, "public_key.pem")
        self.key_id_path = os.path.join(key_dir, "key_id.txt")
        self._ensure_keys()  # Ensure keys are present and valid

    def _ensure_keys(self) -> None:
        """
        Ensures the keys are present and refreshed if necessary.
        """
        if not os.path.exists(self.key_dir):
            os.makedirs(self.key_dir)  # Create directory if it does not exist
        if (
            not os.path.exists(self.private_key_path)
            or not os.path.exists(self.key_id_path)
            or self._keys_need_refresh()
        ):
            self._generate_keys()  # Generate new keys if needed

    def _keys_need_refresh(self) -> bool:
        """
        Checks if the keys need to be refreshed based on their last modification time.

        :return: True if keys need refresh, otherwise False.
        """
        if not os.path.exists(self.private_key_path):
            return True
        file_time = datetime.fromtimestamp(
            os.path.getmtime(self.private_key_path)
        )
        # Check if the last modification time is beyond the refresh threshold
        return datetime.now() - file_time > timedelta(
            days=self.key_refresh_days
        )

    def _generate_keys(self) -> None:
        """
        Generates a new RSA key pair and saves them to files.
        Also generates a unique key ID (kid) for key identification.
        """
        # Generate a new key ID
        key_id = str(uuid.uuid4())

        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        public_key = private_key.public_key()

        # Serialize private key to PEM format
        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        # Serialize public key to PEM format
        pem_public = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # Save the keys to files with restricted permissions
        # Save private key with restricted permissions
        with open(self.private_key_path, "wb") as f:
            f.write(pem_private)
        self._set_secure_permissions(self.private_key_path)

        # Save public key
        with open(self.public_key_path, "wb") as f:
            f.write(pem_public)

        # Save the key ID to a file
        with open(self.key_id_path, "w") as f:
            f.write(key_id)

    def get_private_key(self) -> bytes:
        """
        Retrieves the private key from the file.

        :return: The private key in PEM format.
        """
        with open(self.private_key_path, "rb") as f:
            return f.read()

    def get_public_key(self) -> bytes:
        """
        Retrieves the public key from the file.

        :return: The public key in PEM format.
        """
        with open(self.public_key_path, "rb") as f:
            return f.read()

    def get_key_id(self) -> str:
        """
        Retrieves the current key ID.

        :return: The key ID as a string.
        """
        if not os.path.exists(self.key_id_path):
            # If key ID file doesn't exist, generate new keys
            self._generate_keys()

        with open(self.key_id_path, "r") as f:
            return f.read().strip()

    def _set_secure_permissions(self, file_path: str) -> None:
        """
        Set secure file permissions for sensitive files.
        On Unix/Linux, this sets 600 permissions (owner read/write only).
        On Windows, this is a no-op as Windows has a different permission model.

        Args:
            file_path: Path to the file to secure
        """
        # Only set permissions on Unix-like systems
        if sys.platform != "win32":
            try:
                # Set file permissions to owner read/write only (600)
                os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
            except Exception as e:
                # Log but don't fail if permissions can't be set
                # This might happen in containerized environments
                print(
                    f"Warning: Could not set secure permissions on {file_path}: {e}"
                )
                # Continue execution
