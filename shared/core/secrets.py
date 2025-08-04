from typing import Dict

import aiohttp

VAULT_URL: str = "https://vault.events2go.com.au"
VAULT_TOKEN: str = "hvs.ATZ5B71yX4RmAjAB9dIoT6U7"
SECRET_PATH: str = "v1/kv/data/data"


class VaultError(Exception):
    """Exception raised for errors in fetching secrets from Vault."""

    def __init__(self, message: str):
        super().__init__(message)


# Function to fetch database credentials from Vault asynchronously
async def fetch_secrets_from_vault() -> Dict[str, str]:
    """
    Fetches database credentials stored in HashiCorp Vault.

    Parameters:
        vault_url (str): The URL of the HashiCorp Vault server.
        vault_token (str): The token used for authenticating with Vault.
        secret_path (str): The path to the secret in Vault. Defaults to "v1/kv/data/shoudb".

    Returns:
        Dict[str, str]: A dictionary containing the database credentials.

    Raises:
        VaultError: If there's an error in fetching the credentials or the response is invalid.
    """
    if not VAULT_URL or not VAULT_TOKEN or not SECRET_PATH:
        raise VaultError("Vault configuration is incomplete")

    try:
        # Define the headers for the Vault API request
        headers = {
            "X-Vault-Token": VAULT_TOKEN,  # Vault authentication token
            "Content-Type": "application/json",
        }

        # Construct the full URL for the Vault API
        url = f"{VAULT_URL}/{SECRET_PATH}"

        # Perform an async GET request to fetch the secret data
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                # Check if the response status is successful (HTTP 200)
                if response.status == 200:
                    # Parse the JSON response
                    response_data = await response.json()

                    # Extract the `data` field containing secrets
                    secrets = response_data["data"]["data"]
                    # print("Vault Secrets: ", secrets)

                    # Return the extracted secrets in a structured dictionary
                    return {
                        "DB_USER": secrets.get("DATABASE"),
                        "DB_HOST": secrets.get("DB_HOST"),
                        "DB_PASSWORD": secrets.get("DB_PASSWORD"),
                        "DB_PORT": secrets.get("DB_PORT"),
                        "DB_NAME": secrets.get("SOURCE_DB_NAME"),
                        "EMAIL_FROM": secrets.get("SENDER_EMAIL"),
                        "SMTP_PASSWORD": secrets.get("SENDER_PASSWORD"),
                        "SMTP_USER": secrets.get("SMTP_LOGIN"),
                        "SMTP_PORT": secrets.get("SMTP_PORT"),
                        "SMTP_HOST": secrets.get("SMTP_SERVER"),
                        "SPACES_ACCESS_KEY": secrets.get("SPACES_ACCESS_KEY"),
                        "SPACES_BUCKET_NAME": secrets.get("SPACES_BUCKET_NAME"),
                        "SPACES_REGION_NAME": secrets.get("SPACES_REGION_NAME"),
                        "SPACES_SECRET_KEY": secrets.get("SPACES_SECRET_KEY"),
                    }

                # Raise a specific error if the response status is not 200
                raise VaultError(
                    f"Failed to fetch secrets. HTTP Status: {response.status}"
                )

    except aiohttp.ClientError as e:
        # Handle HTTP client errors specifically
        raise VaultError(f"HTTP Client Error: {str(e)}")
    except KeyError as e:
        # Handle missing keys in the response data
        raise VaultError(f"Missing expected key in Vault response: {str(e)}")
    except Exception as e:
        # Raise a VaultError for any other unexpected exceptions
        raise VaultError(
            f"Unexpected error fetching secrets from Vault: {str(e)}"
        )
