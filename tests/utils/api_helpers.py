from typing import Any, Dict, Optional

from httpx import AsyncClient


class AsyncAPITestHelper:
    def __init__(self, client: AsyncClient):
        self.client = client

    async def get(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        r = await self.client.get(url, **kwargs)
        return {
            "status_code": r.status_code,
            "data": r.json() if r.content else None,
            "headers": dict(r.headers),
        }

    async def post(
        self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        r = await self.client.post(url, json=data, **kwargs)
        return {
            "status_code": r.status_code,
            "data": r.json() if r.content else None,
            "headers": dict(r.headers),
        }

    async def put(
        self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        r = await self.client.put(url, json=data, **kwargs)
        return {
            "status_code": r.status_code,
            "data": r.json() if r.content else None,
            "headers": dict(r.headers),
        }

    async def delete(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        r = await self.client.delete(url, **kwargs)
        return {
            "status_code": r.status_code,
            "data": r.json() if r.content else None,
            "headers": dict(r.headers),
        }

    async def patch(
        self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        r = await self.client.patch(url, json=data, **kwargs)
        return {
            "status_code": r.status_code,
            "data": r.json() if r.content else None,
            "headers": dict(r.headers),
        }
