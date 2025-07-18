"""
Device Information Extraction Utilities

This module provides utilities for extracting device information from HTTP requests.
Note: MAC addresses cannot be captured from web requests for security reasons.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import Request
from user_agents import parse


class DeviceInfoExtractor:
    """Extract comprehensive device information from HTTP requests"""

    @staticmethod
    def extract_comprehensive_device_info(request: Request) -> Dict[str, Any]:
        """
        Extract comprehensive device information from HTTP request.

        Args:
            request: FastAPI Request object

        Returns:
            Dict containing device information
        """
        user_agent_string = request.headers.get("user-agent", "")
        user_agent = parse(user_agent_string)

        # Extract IP address
        ip_address = DeviceInfoExtractor._extract_ip_address(request)

        # Extract device details
        device_info = {
            "ip_address": ip_address,
            "user_agent": user_agent_string,
            "device_family": user_agent.device.family,
            "device_brand": user_agent.device.brand,
            "device_model": user_agent.device.model,
            "browser_family": user_agent.browser.family,
            "browser_version": user_agent.browser.version_string,
            "os_family": user_agent.os.family,
            "os_version": user_agent.os.version_string,
            "is_mobile": user_agent.is_mobile,
            "is_tablet": user_agent.is_tablet,
            "is_pc": user_agent.is_pc,
            "is_bot": user_agent.is_bot,
            "device_type": DeviceInfoExtractor._determine_device_type(
                user_agent
            ),
            "screen_info": DeviceInfoExtractor._extract_screen_info(request),
            "language": request.headers.get("accept-language", "").split(",")[
                0
            ],
            "timezone": request.headers.get("x-timezone", "UTC"),
            "connection_type": DeviceInfoExtractor._detect_connection_type(
                request
            ),
            "fingerprint": DeviceInfoExtractor._generate_device_fingerprint(
                request, user_agent
            ),
            "extracted_at": datetime.now(timezone.utc),
        }

        return device_info

    @staticmethod
    def _extract_ip_address(request: Request) -> str:
        """Extract real IP address considering proxies and load balancers"""
        # Check for forwarded headers in order of preference
        forwarded_headers = [
            "x-forwarded-for",
            "x-real-ip",
            "x-client-ip",
            "cf-connecting-ip",  # Cloudflare
            "x-forwarded",
            "forwarded-for",
            "forwarded",
        ]

        for header in forwarded_headers:
            if header in request.headers:
                # Take the first IP in case of multiple
                ip = request.headers[header].split(",")[0].strip()
                if ip and ip != "unknown":
                    return ip

        # Fallback to request.client.host
        if request.client:
            return request.client.host

        return "unknown"

    @staticmethod
    def _determine_device_type(user_agent) -> str:
        """Determine device type based on user agent object"""
        if not user_agent:
            return "Unknown Device"

        # Use the parsed user agent object properties
        if user_agent.is_mobile:
            if "iPhone" in user_agent.device.family:
                return "iPhone"
            elif "Android" in user_agent.os.family:
                return "Android Device"
            return "Mobile Device"
        elif user_agent.is_tablet:
            return "Tablet Device"
        elif user_agent.is_pc:
            if "Windows" in user_agent.os.family:
                return "Windows PC"
            elif "Mac" in user_agent.os.family:
                return "Mac"
            elif "Linux" in user_agent.os.family:
                return "Linux PC"
            else:
                return "Desktop Device"
        elif user_agent.is_bot:
            return "Bot"
        else:
            return "Desktop Device"

    @staticmethod
    def _extract_screen_info(request: Request) -> Dict[str, Optional[str]]:
        """Extract screen information from custom headers"""
        return {
            "screen_width": request.headers.get("x-screen-width"),
            "screen_height": request.headers.get("x-screen-height"),
            "screen_density": request.headers.get("x-screen-density"),
            "color_depth": request.headers.get("x-color-depth"),
        }

    @staticmethod
    def _detect_connection_type(request: Request) -> str:
        """Detect connection type from headers"""
        # Check for connection type headers
        connection_headers = [
            "x-connection-type",
            "x-network-type",
            "save-data",
        ]

        for header in connection_headers:
            if header in request.headers:
                return request.headers[header]

        # Check for save-data header (indicates slow connection)
        if (
            "save-data" in request.headers
            and request.headers["save-data"] == "on"
        ):
            return "slow"

        return "unknown"

    @staticmethod
    def _generate_device_fingerprint(request: Request, user_agent) -> str:
        """Generate a device fingerprint for identification"""
        import hashlib

        # Combine various attributes to create a fingerprint
        fingerprint_data = [
            user_agent.browser.family,
            user_agent.browser.version_string,
            user_agent.os.family,
            user_agent.os.version_string,
            user_agent.device.family,
            request.headers.get("accept-language", ""),
            request.headers.get("accept-encoding", ""),
            request.headers.get("x-screen-width", ""),
            request.headers.get("x-screen-height", ""),
        ]

        # Create hash from combined data
        fingerprint_string = "|".join(filter(None, fingerprint_data))
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]


class LocationService:
    """Service for extracting location information from IP addresses"""

    @staticmethod
    async def get_location_from_ip(ip_address: str) -> Optional[Dict[str, Any]]:
        """
        Get location information from IP address using a free IP geolocation service.

        Args:
            ip_address: IP address to lookup

        Returns:
            Dict containing location information or None if failed
        """
        if not ip_address or ip_address in ["unknown", "127.0.0.1", "::1"]:
            return None

        try:
            # Using ipapi.co as a free service (consider using a paid service for production)
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"https://ipapi.co/{ip_address}/json/"
                )

                if response.status_code == 200:
                    data = response.json()

                    # Check if the response contains an error
                    if "error" in data:
                        return None

                    return {
                        "ip": data.get("ip"),
                        "city": data.get("city"),
                        "region": data.get("region"),
                        "country": data.get("country_name"),
                        "country_code": data.get("country_code"),
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "timezone": data.get("timezone"),
                        "isp": data.get("org"),
                        "as": data.get("asn"),
                        "retrieved_at": datetime.now(timezone.utc),
                    }
        except Exception as e:
            # Log the error but don't fail the login process
            from core.logging_config import get_logger

            logger = get_logger(__name__)
            logger.warning(f"Failed to get location for IP {ip_address}: {e}")

        return None


class DeviceSessionManager:
    """Manager for device session operations"""

    @staticmethod
    def generate_device_name(device_info: Dict[str, Any]) -> str:
        """Generate a human-readable device name"""
        parts = []

        # Add device brand and model if available
        if device_info.get("device_brand") and device_info.get("device_model"):
            parts.append(
                f"{device_info['device_brand']} {device_info['device_model']}"
            )
        elif (
            device_info.get("device_family")
            and device_info["device_family"] != "Other"
        ):
            parts.append(device_info["device_family"])

        # Add OS information
        if device_info.get("os_family") and device_info.get("os_version"):
            parts.append(
                f"{device_info['os_family']} {device_info['os_version']}"
            )
        elif device_info.get("os_family"):
            parts.append(device_info["os_family"])

        # Add browser information
        if device_info.get("browser_family") and device_info.get(
            "browser_version"
        ):
            parts.append(
                f"{device_info['browser_family']} {device_info['browser_version']}"
            )
        elif device_info.get("browser_family"):
            parts.append(device_info["browser_family"])

        # Add device type if no specific device info
        if not parts and device_info.get("device_type"):
            parts.append(device_info["device_type"].title())

        # Fallback to generic name
        if not parts:
            parts.append("Unknown Device")

        return " - ".join(parts)

    @staticmethod
    def should_create_new_session(
        existing_sessions: list, device_info: Dict[str, Any]
    ) -> bool:
        """
        Determine if a new session should be created based on device fingerprint.

        Args:
            existing_sessions: List of existing active sessions
            device_info: Current device information

        Returns:
            True if a new session should be created
        """
        current_fingerprint = device_info.get("fingerprint")
        current_ip = device_info.get("ip_address")

        if not current_fingerprint:
            return True

        # Check if Any existing session has the same fingerprint
        for session in existing_sessions:
            if (
                hasattr(session, "df")
                and session.device_fingerprint == current_fingerprint
            ):
                # Same device fingerprint - check if IP is similar
                if (
                    hasattr(session, "ip_address")
                    and session.ip_address == current_ip
                ):
                    return (
                        False  # Same device, same IP - don't create new session
                    )

        return True  # Different device or IP - create new session
