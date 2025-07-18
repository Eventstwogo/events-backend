import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Union

import jwt
from passlib.context import CryptContext

from shared.core.config import JWT_KEY_ID, PUBLIC_KEY, settings
from shared.core.logging_config import get_logger
from shared.utils.token_blacklist import add_to_blacklist, is_blacklisted

logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# JWT Creation Function
def create_jwt_token(
    data: Dict[str, Any],
    private_key: Union[str, bytes],
    expires_in: int = settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
) -> str:
    """
    Create an RS256-signed JWT token.

    Args:
        data (dict): Payload data.
        private_key (str/bytes): RSA private key.
        expires_in (int): Expiry time in seconds.

    Returns:
        str: Encoded JWT token.

    Raises:
        RuntimeError: For any encoding issues.
    """
    if not data:
        raise ValueError("JWT payload cannot be empty.")
    if not private_key:
        raise ValueError("Private key is required to sign the JWT.")

    # Ensure user_id is present in the payload
    if "uid" not in data:
        raise ValueError("JWT payload must contain user_id.")

    # Create a standardized payload with required claims
    now = datetime.now(timezone.utc)
    payload = {
        **data,
        "exp": now + timedelta(seconds=expires_in),
        "iat": now,
        "jti": secrets.token_hex(16),  # Add a unique token ID
        "iss": settings.JWT_ISSUER,  # Issuer claim
        "aud": settings.JWT_AUDIENCE,  # Audience claim
        "kid": JWT_KEY_ID,  # Key ID for key rotation support
    }

    try:
        # Ensure algorithm is explicitly set to RS256
        if settings.JWT_ALGORITHM != "RS256":
            logger.warning(
                f"JWT algorithm in settings is {settings.JWT_ALGORITHM}, but RS256 is required"
            )

        token = jwt.encode(payload, private_key, algorithm="RS256")

        # Verify the token can be decoded (sanity check)
        try:
            jwt.decode(
                token,
                PUBLIC_KEY.get_secret_value(),
                algorithms=["RS256"],
                audience=settings.JWT_AUDIENCE,
                issuer=settings.JWT_ISSUER,
            )
        except Exception as verify_error:
            logger.error(f"Generated token failed verification: {verify_error}")
            raise RuntimeError(
                f"Token generation failed verification: {verify_error}"
            )

        return token
    except Exception as e:
        logger.exception("JWT encoding failed.")
        raise RuntimeError(f"JWT encoding failed: {e}") from e


# JWT Verification Function
def verify_jwt_token(
    token: str,
    public_key: Union[str, bytes],
) -> Dict[str, Any]:
    """
    Verify and decode a RS256 JWT token.

    Args:
        token (str): JWT token to verify.
        public_key (str/bytes): RSA public key.

    Returns:
        dict: Decoded payload.

    Raises:
        ValueError or RuntimeError for various failures.
    """
    if not token:
        raise ValueError("JWT token is required.")
    if not public_key:
        raise ValueError("Public key is required.")

    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_iat": True,
        "verify_aud": True,
        "verify_iss": True,
        "require": ["exp", "iat", "iss", "aud"],
    }

    try:
        # Force RS256 algorithm to match token creation
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],  # Hardcode RS256 to ensure consistency
            options=options,
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )

        # Check if token is blacklisted
        if "jti" in payload and is_blacklisted(payload["jti"]):
            logger.warning(
                f"Attempt to use blacklisted token with JTI: {payload['jti']}"
            )
            raise ValueError("Token has been revoked.")

        return payload

    except jwt.ExpiredSignatureError as exc:
        logger.warning("JWT token has expired.")
        raise ValueError("JWT token has expired.") from exc

    except jwt.InvalidSignatureError as exc:
        logger.warning("JWT token has invalid signature.")
        raise ValueError("Invalid token signature.") from exc

    except jwt.InvalidIssuedAtError as exc:
        logger.warning("JWT token has invalid iat claim.")
        raise ValueError("Token has invalid issue time.") from exc

    except jwt.InvalidAlgorithmError as exc:
        logger.warning("JWT token uses invalid algorithm.")
        raise ValueError("Token uses unsupported algorithm.") from exc

    except jwt.MissingRequiredClaimError as exc:
        logger.warning("JWT token missing required claim: %s", exc)
        raise ValueError(f"Token missing required claim: {exc}") from exc

    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid JWT token: %s", exc)
        raise RuntimeError(f"Invalid token: {exc}") from exc


def revoke_token(token: str, public_key: Union[str, bytes]) -> bool:
    """
    Revoke a JWT token by adding it to the blacklist.

    Args:
        token (str): The JWT token to revoke
        public_key (str/bytes): The public key to verify the token

    Returns:
        bool: True if token was successfully revoked, False otherwise

    Raises:
        ValueError: If token is invalid or already expired
    """
    if not token:
        raise ValueError("Token is required for revocation")

    try:
        # Decode the token without verifying expiration
        # We want to blacklist even if it's already expired
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={
                "verify_signature": True,  # Still verify signature
                "verify_exp": False,  # Don't verify expiration
                "verify_aud": False,  # Don't verify audience
                "verify_iss": False,  # Don't verify issuer
            },
        )

        # Check if token has jti claim
        if "jti" not in payload:
            logger.warning("Cannot revoke token without jti claim")
            return False

        # Check if token has exp claim
        if "exp" not in payload:
            logger.warning("Cannot revoke token without exp claim")
            return False

        # Add token to blacklist
        exp_datetime = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        add_to_blacklist(payload["jti"], exp_datetime)

        logger.info(
            f"Token for user {payload.get('uid', 'unknown')} has been revoked"
        )
        return True

    except jwt.InvalidTokenError as exc:
        logger.warning(f"Cannot revoke invalid token: {exc}")
        raise ValueError(f"Cannot revoke invalid token: {exc}") from exc
