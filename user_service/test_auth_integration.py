#!/usr/bin/env python3
"""
Simple test script to verify OAuth2 authentication is working
for user management endpoints.

This script demonstrates that the endpoints now require authentication.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from user_service.api.routes import user_router


def test_authentication_required():
    """Test that user management endpoints require authentication"""

    # Create a test app
    app = FastAPI()
    app.include_router(user_router)

    client = TestClient(app)

    print("Testing OAuth2 Authentication on User Management Endpoints")
    print("=" * 60)

    # Test endpoints without authentication - should return 401
    endpoints_to_test = [
        ("GET", "/api/v1/users/"),
        ("GET", "/api/v1/users/ABC123"),
        ("PATCH", "/api/v1/users/ABC123/deactivate"),
        ("PATCH", "/api/v1/users/ABC123/reactivate"),
        ("DELETE", "/api/v1/users/ABC123"),
    ]

    for method, endpoint in endpoints_to_test:
        print(f"\nTesting {method} {endpoint} without authentication...")

        if method == "GET":
            response = client.get(endpoint)
        elif method == "PATCH":
            response = client.patch(endpoint)
        elif method == "DELETE":
            response = client.delete(endpoint)

        if response.status_code == 401:
            print(
                f"✅ PASS: {endpoint} correctly requires authentication (401)"
            )
        else:
            print(
                f"❌ FAIL: {endpoint} returned {response.status_code} instead of 401"
            )
            print(f"   Response: {response.text}")

    print("\n" + "=" * 60)
    print("Authentication test completed!")
    print("\nTo test with valid authentication:")
    print("1. Start the server: uvicorn main:app --reload")
    print("2. Login to get a token: POST /api/v1/users/login")
    print("3. Use the token: Authorization: Bearer <token>")


if __name__ == "__main__":
    test_authentication_required()
