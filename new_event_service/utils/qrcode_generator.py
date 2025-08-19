import base64
from io import BytesIO
import qrcode
from fastapi import APIRouter

from shared.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


def generate_qr_code(data: str) -> str:
    """
    Generate a QR code and return as base64-encoded PNG string.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"