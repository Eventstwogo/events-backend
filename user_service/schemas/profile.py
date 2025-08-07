from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    user_id: str
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: EmailStr
    profile_picture: str | None = None


class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    username: str = Field(..., max_length=255)
    email: EmailStr
