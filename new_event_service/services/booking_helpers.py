from datetime import date
from typing import Any, Optional, Tuple

from paypalcheckoutsdk.orders import OrdersCreateRequest
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.services.bookings import (
    check_existing_booking,
    verify_booking_constraints,
)
from event_service.utils.paypal_client import paypal_client
from shared.core.config import settings


def extract_approval_url_from_paypal_response(response: Any) -> Optional[str]:
    """
    Safely extract the approval URL from PayPal response.

    Args:
        response: PayPal SDK response object

    Returns:
        Optional[str]: The approval URL if found, None otherwise
    """
    try:
        if not response or not hasattr(response, "result"):
            return None

        if not hasattr(response.result, "links") or not response.result.links:
            return None

        for link in response.result.links:
            if (
                hasattr(link, "rel")
                and hasattr(link, "href")
                and link.rel == "approve"
            ):
                return link.href

        return None
    except Exception:
        return None


def check_paypal_payment_status(response: Any) -> Optional[str]:
    """
    Safely extract the payment status from PayPal response.

    Args:
        response: PayPal SDK response object

    Returns:
        Optional[str]: The payment status if found, None otherwise
    """
    try:
        if not response or not hasattr(response, "result"):
            return None

        if hasattr(response.result, "status"):
            return response.result.status

        return None
    except Exception:
        return None


def extract_capture_id(response):
    """
    Safely extract the capture ID from a PayPal OrdersCaptureResponse.

    Args:
        response: PayPalHttpResponse object from PayPal client execute()

    Returns:
        str | None: The capture ID if available, otherwise None
    """
    try:
        if not hasattr(response, "result"):
            return None

        purchase_units = getattr(response.result, "purchase_units", [])
        if not purchase_units:
            return None

        payments = getattr(purchase_units[0], "payments", None)
        if not payments or not getattr(payments, "captures", None):
            return None

        return payments.captures[0].id
    except Exception:
        return None


async def create_paypal_order(
    total_price: float, booking_id: str
) -> Optional[str]:
    """Create PayPal order and return approval URL."""
    request = OrdersCreateRequest()
    request.headers["prefer"] = "return=representation"
    request.request_body(
        {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "AUD",
                        "value": str(round(total_price, 2)),
                    }
                }
            ],
            "application_context": {
                "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                "brand_name": "Events2Go",
                "landing_page": "LOGIN",
                "locale": "en-AU",
                "user_action": "PAY_NOW",
                "return_url": f"{settings.API_BACKEND_URL}/api/v1/bookings/confirm?booking_id={booking_id}",
                "cancel_url": f"{settings.API_BACKEND_URL}/api/v1/bookings/cancel?booking_id={booking_id}",
            },
        }
    )
    response = paypal_client.client.execute(request)
    return extract_approval_url_from_paypal_response(response)
