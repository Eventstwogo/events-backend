from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    role_id: str


class UpdateProfileRequest(BaseModel):
    username: str = Field(..., max_length=255)
    email: EmailStr
