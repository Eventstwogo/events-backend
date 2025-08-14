"""
Tests for coupon API endpoints.
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models.events import Coupon, DiscountType


class TestCouponEndpoints:
    """Test class for coupon API endpoints."""

    @pytest.fixture
    async def sample_coupon_data(self):
        """Sample coupon data for testing."""
        return {
            "coupon_code": "TEST2024",
            "description": "Test coupon for 20% discount",
            "discount_type": "PERCENTAGE",
            "discount_value": 20.0,
            "max_uses": 100,
            "valid_from": (datetime.now() - timedelta(days=1)).isoformat(),
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "is_active": True,
        }

    @pytest.fixture
    async def expired_coupon_data(self):
        """Expired coupon data for testing."""
        return {
            "coupon_code": "EXPIRED2024",
            "description": "Expired test coupon",
            "discount_type": "FIXED",
            "discount_value": 10.0,
            "max_uses": 50,
            "valid_from": (datetime.now() - timedelta(days=10)).isoformat(),
            "valid_until": (datetime.now() - timedelta(days=1)).isoformat(),
            "is_active": True,
        }

    @pytest.mark.asyncio
    async def test_create_coupon_success(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test successful coupon creation."""
        response = await async_client.post(
            "/api/v1/coupons/", json=sample_coupon_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Coupon created successfully"
        assert data["data"]["coupon_code"] == sample_coupon_data["coupon_code"]
        assert (
            data["data"]["discount_type"] == sample_coupon_data["discount_type"]
        )
        assert (
            data["data"]["discount_value"]
            == sample_coupon_data["discount_value"]
        )

    @pytest.mark.asyncio
    async def test_create_coupon_duplicate_code(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test creating coupon with duplicate code."""
        # Create first coupon
        await async_client.post("/api/v1/coupons/", json=sample_coupon_data)

        # Try to create duplicate
        response = await async_client.post(
            "/api/v1/coupons/", json=sample_coupon_data
        )

        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_coupon_invalid_percentage(
        self, async_client: AsyncClient
    ):
        """Test creating coupon with invalid percentage."""
        invalid_data = {
            "coupon_code": "INVALID2024",
            "description": "Invalid percentage coupon",
            "discount_type": "PERCENTAGE",
            "discount_value": 150.0,  # Invalid: > 100%
            "is_active": True,
        }

        response = await async_client.post(
            "/api/v1/coupons/", json=invalid_data
        )

        assert response.status_code == 422
        data = response.json()
        assert "cannot exceed 100%" in str(data["detail"])

    @pytest.mark.asyncio
    async def test_list_coupons(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test listing coupons with pagination."""
        # Create a coupon first
        await async_client.post("/api/v1/coupons/", json=sample_coupon_data)

        response = await async_client.get("/api/v1/coupons/?page=1&per_page=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "coupons" in data["data"]
        assert "total" in data["data"]
        assert "page" in data["data"]
        assert "per_page" in data["data"]
        assert "total_pages" in data["data"]

    @pytest.mark.asyncio
    async def test_list_coupons_with_filters(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test listing coupons with filters."""
        # Create a coupon first
        await async_client.post("/api/v1/coupons/", json=sample_coupon_data)

        response = await async_client.get(
            "/api/v1/coupons/?is_active=true&discount_type=PERCENTAGE&search=TEST"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["coupons"]) >= 0

    @pytest.mark.asyncio
    async def test_get_coupon_by_id(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test getting coupon by ID."""
        # Create a coupon first
        create_response = await async_client.post(
            "/api/v1/coupons/", json=sample_coupon_data
        )
        coupon_id = create_response.json()["data"]["coupon_id"]

        response = await async_client.get(f"/api/v1/coupons/{coupon_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["coupon_id"] == coupon_id
        assert data["data"]["coupon_code"] == sample_coupon_data["coupon_code"]

    @pytest.mark.asyncio
    async def test_get_coupon_by_id_not_found(self, async_client: AsyncClient):
        """Test getting non-existent coupon by ID."""
        response = await async_client.get("/api/v1/coupons/99999")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_coupon_by_code(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test getting coupon by code."""
        # Create a coupon first
        await async_client.post("/api/v1/coupons/", json=sample_coupon_data)

        response = await async_client.get(
            f"/api/v1/coupons/code/{sample_coupon_data['coupon_code']}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["coupon_code"] == sample_coupon_data["coupon_code"]

    @pytest.mark.asyncio
    async def test_update_coupon(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test updating coupon."""
        # Create a coupon first
        create_response = await async_client.post(
            "/api/v1/coupons/", json=sample_coupon_data
        )
        coupon_id = create_response.json()["data"]["coupon_id"]

        update_data = {
            "description": "Updated description",
            "discount_value": 25.0,
        }

        response = await async_client.put(
            f"/api/v1/coupons/{coupon_id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["description"] == update_data["description"]
        assert data["data"]["discount_value"] == update_data["discount_value"]

    @pytest.mark.asyncio
    async def test_delete_coupon(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test deleting coupon."""
        # Create a coupon first
        create_response = await async_client.post(
            "/api/v1/coupons/", json=sample_coupon_data
        )
        coupon_id = create_response.json()["data"]["coupon_id"]

        response = await async_client.delete(f"/api/v1/coupons/{coupon_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Coupon deleted successfully"

    @pytest.mark.asyncio
    async def test_validate_coupon_valid(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test validating a valid coupon."""
        # Create a coupon first
        await async_client.post("/api/v1/coupons/", json=sample_coupon_data)

        validation_data = {
            "coupon_code": sample_coupon_data["coupon_code"],
            "original_price": 100.0,
        }

        response = await async_client.post(
            "/api/v1/coupons/validate", json=validation_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_valid"] is True
        assert data["data"]["discount_amount"] == 20.0  # 20% of 100
        assert data["data"]["final_price"] == 80.0

    @pytest.mark.asyncio
    async def test_validate_coupon_expired(
        self, async_client: AsyncClient, expired_coupon_data
    ):
        """Test validating an expired coupon."""
        # Create an expired coupon first
        await async_client.post("/api/v1/coupons/", json=expired_coupon_data)

        validation_data = {
            "coupon_code": expired_coupon_data["coupon_code"],
            "original_price": 100.0,
        }

        response = await async_client.post(
            "/api/v1/coupons/validate", json=validation_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["data"]["is_valid"] is False
        assert "expired" in data["data"]["error_message"].lower()

    @pytest.mark.asyncio
    async def test_validate_coupon_not_found(self, async_client: AsyncClient):
        """Test validating non-existent coupon."""
        validation_data = {
            "coupon_code": "NONEXISTENT",
            "original_price": 100.0,
        }

        response = await async_client.post(
            "/api/v1/coupons/validate", json=validation_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["data"]["is_valid"] is False
        assert data["data"]["error_message"] == "Coupon not found"

    @pytest.mark.asyncio
    async def test_use_coupon_success(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test using a valid coupon."""
        # Create a coupon first
        await async_client.post("/api/v1/coupons/", json=sample_coupon_data)

        usage_data = {
            "coupon_code": sample_coupon_data["coupon_code"],
            "original_price": 100.0,
        }

        response = await async_client.post(
            "/api/v1/coupons/use", json=usage_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is True
        assert data["data"]["discount_amount"] == 20.0
        assert data["data"]["final_price"] == 80.0
        assert data["data"]["coupon"]["used_count"] == 1

    @pytest.mark.asyncio
    async def test_get_coupon_stats(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test getting coupon statistics."""
        # Create and use a coupon first
        create_response = await async_client.post(
            "/api/v1/coupons/", json=sample_coupon_data
        )
        coupon_id = create_response.json()["data"]["coupon_id"]

        # Use the coupon once
        usage_data = {
            "coupon_code": sample_coupon_data["coupon_code"],
            "original_price": 100.0,
        }
        await async_client.post("/api/v1/coupons/use", json=usage_data)

        response = await async_client.get(f"/api/v1/coupons/{coupon_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["coupon_id"] == coupon_id
        assert data["data"]["total_uses"] == 1
        assert data["data"]["remaining_uses"] == 99  # 100 - 1
        assert data["data"]["is_active"] is True
        assert data["data"]["is_valid"] is True

    @pytest.mark.asyncio
    async def test_create_bulk_coupons(self, async_client: AsyncClient):
        """Test creating bulk coupons."""
        bulk_data = {
            "prefix": "BULK",
            "count": 5,
            "discount_type": "PERCENTAGE",
            "discount_value": 15.0,
            "description": "Bulk generated coupons",
            "max_uses": 10,
            "valid_from": datetime.now().isoformat(),
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
        }

        response = await async_client.post(
            "/api/v1/coupons/bulk", json=bulk_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["created_count"] == 5
        assert len(data["data"]["coupon_codes"]) == 5

        # Check that all codes start with the prefix
        for code in data["data"]["coupon_codes"]:
            assert code.startswith("BULK-")

    @pytest.mark.asyncio
    async def test_get_active_coupons(
        self, async_client: AsyncClient, sample_coupon_data
    ):
        """Test getting active coupons."""
        # Create a coupon first
        await async_client.post("/api/v1/coupons/", json=sample_coupon_data)

        response = await async_client.get("/api/v1/coupons/active/list")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1
