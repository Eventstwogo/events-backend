import os
from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment, LiveEnvironment
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class PayPalClient:
    def __init__(self):
        self.client_id = os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        paypal_mode = os.getenv("PAYPAL_MODE", "sandbox").lower()
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Missing PayPal credentials in environment variables.")
        
        if paypal_mode not in ["sandbox", "live"]:
            raise ValueError("PAYPAL_MODE must be either 'sandbox' or 'live'")
        
        if paypal_mode == "live":
            self.environment = LiveEnvironment(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            logger.info("PayPal initialized in LIVE mode")
            # Security: Don't log sensitive URLs in production
        else:
            self.environment = SandboxEnvironment(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            logger.info("PayPal initialized in SANDBOX mode")
        
        self.client = PayPalHttpClient(self.environment)
        
        # Verify environment matches expectation
        is_sandbox = "sandbox" in self.environment.base_url.lower()
        expected_sandbox = paypal_mode == "sandbox"
        
        if is_sandbox != expected_sandbox:
            raise ValueError(f"Environment mismatch: Expected {'sandbox' if expected_sandbox else 'live'}, got {'sandbox' if is_sandbox else 'live'}")

# Initialize PayPal client
try:
    paypal_client = PayPalClient()
except Exception as e:
    logger.error(f"Failed to initialize PayPal client: {e}")
    raise