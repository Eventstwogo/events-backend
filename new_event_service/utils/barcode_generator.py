"""
Barcode generation utilities for booking details.
"""

import base64
from io import BytesIO
from typing import Dict, Any, Optional

import barcode
from barcode.writer import ImageWriter
from PIL import Image

from shared.core.logging_config import get_logger

logger = get_logger(__name__)


class BarcodeGenerator:
    """Utility class for generating barcodes for booking details."""

    @staticmethod
    def generate_booking_barcode(
        order_id: str,
        barcode_type: str = "code128",
        width: float = 0.15,
        height: float = 12.0,
        font_size: int = 0,
        text_distance: float = 0.0
    ) -> str:
        """
        Generate a barcode for booking order ID.
        
        Args:
            order_id: Order ID to encode in barcode
            barcode_type: Type of barcode (code128, code39, ean8, ean13, etc.)
            width: Width of the barcode bars
            height: Height of the barcode in mm
            font_size: Font size for the text below barcode
            text_distance: Distance between barcode and text
            
        Returns:
            Base64 encoded PNG image string of the barcode
        """
        try:
            # Get barcode class
            barcode_class = barcode.get_barcode_class(barcode_type)
            
            # Create barcode instance with custom writer options
            writer_options = {
                'module_width': width,
                'module_height': height,
                'font_size': font_size,
                'text_distance': text_distance,
                'background': 'white',
                'foreground': 'black',
                'write_text': False,
                'text': ''
            }
            
            # Generate barcode
            code = barcode_class(order_id, writer=ImageWriter())
            
            # Save to BytesIO buffer
            buffer = BytesIO()
            code.write(buffer, options=writer_options)
            
            # Convert to base64
            buffer.seek(0)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"

        except Exception as e:
            logger.error(f"Error generating barcode: {str(e)}")
            # Fallback: generate simple Code128 barcode
            try:
                code128 = barcode.get_barcode_class('code128')
                simple_code = code128(order_id, writer=ImageWriter())
                buffer = BytesIO()
                simple_code.write(buffer)
                buffer.seek(0)
                img_str = base64.b64encode(buffer.getvalue()).decode()
                return f"data:image/png;base64,{img_str}"
            except Exception as fallback_error:
                logger.error(f"Fallback barcode generation failed: {str(fallback_error)}")
                raise Exception(f"Failed to generate barcode: {str(e)}")

    @staticmethod
    def generate_ean13_barcode(order_id: str) -> str:
        """
        Generate EAN-13 barcode (requires 12-13 digit numeric string).
        
        Args:
            order_id: Order ID (will be padded/truncated to fit EAN-13 format)
            
        Returns:
            Base64 encoded PNG image string of the EAN-13 barcode
        """
        try:
            # Convert order_id to numeric string and pad/truncate for EAN-13
            numeric_id = ''.join(filter(str.isdigit, order_id))
            
            # If no digits found, create from hash
            if not numeric_id:
                numeric_id = str(abs(hash(order_id)))[:12]
            
            # Ensure exactly 12 digits (EAN-13 calculates 13th check digit)
            if len(numeric_id) < 12:
                numeric_id = numeric_id.zfill(12)
            else:
                numeric_id = numeric_id[:12]
            
            ean13 = barcode.get_barcode_class('ean13')
            code = ean13(numeric_id, writer=ImageWriter())
            
            buffer = BytesIO()
            code.write(buffer)
            buffer.seek(0)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"

        except Exception as e:
            logger.error(f"Error generating EAN-13 barcode: {str(e)}")
            # Fallback to Code128
            return BarcodeGenerator.generate_booking_barcode(order_id)

    @staticmethod
    def generate_code39_barcode(order_id: str) -> str:
        """
        Generate Code39 barcode (supports alphanumeric).
        
        Args:
            order_id: Order ID to encode
            
        Returns:
            Base64 encoded PNG image string of the Code39 barcode
        """
        try:
            # Code39 supports: 0-9, A-Z, space, and symbols: - . $ / + %
            # Convert order_id to uppercase and filter valid characters
            valid_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%"
            filtered_id = ''.join(c for c in order_id.upper() if c in valid_chars)
            
            if not filtered_id:
                filtered_id = order_id.upper()[:10]  # Take first 10 chars as fallback
            
            code39 = barcode.get_barcode_class('code39')
            code = code39(filtered_id, writer=ImageWriter(), add_checksum=False)
            
            buffer = BytesIO()
            code.write(buffer)
            buffer.seek(0)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"

        except Exception as e:
            logger.error(f"Error generating Code39 barcode: {str(e)}")
            # Fallback to Code128
            return BarcodeGenerator.generate_booking_barcode(order_id)

    @staticmethod
    def prepare_booking_info_for_display(
        order_id: str,
        event_title: str,
        event_date: str,
        event_time: str,
        user_name: str,
        total_amount: float,
        seat_categories: list,
        event_location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare booking information for display alongside barcode.
        
        Args:
            order_id: Order ID
            event_title: Event title
            event_date: Event date
            event_time: Event time
            user_name: User's name
            total_amount: Total booking amount
            seat_categories: List of seat category details
            event_location: Optional event location
            
        Returns:
            Dictionary with formatted booking information
        """
        return {
            "order_id": order_id,
            "event": {
                "title": event_title,
                "date": event_date,
                "time": event_time,
                "location": event_location or "TBA"
            },
            "booking": {
                "user_name": user_name,
                "total_amount": round(total_amount, 2),
                "total_seats": sum(cat.get("num_seats", 0) for cat in seat_categories),
                "seat_categories": [
                    {
                        "label": cat.get("label", ""),
                        "seats": cat.get("num_seats", 0),
                        "price": round(cat.get("price_per_seat", 0), 2)
                    }
                    for cat in seat_categories
                ]
            }
        }