from typing import Optional

from pydantic import BaseModel, Field


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    session_id: int | None = Field(
        default=None, description="ID of the associated device session"
    )


class TokenData(BaseModel):
    username: Optional[str] = None
