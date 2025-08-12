from typing import Optional

from pydantic import BaseModel, Field


class OrganizerCardStats(BaseModel):
    """Statistics for organizer dashboard cards"""

    total_organizers: int = Field(..., description="Total number of organizers")
    approved: int = Field(..., description="Number of approved organizers")
    pending: int = Field(..., description="Number of pending organizers")
    rejected: int = Field(..., description="Number of rejected organizers")
    under_review: int = Field(
        ..., description="Number of organizers under review"
    )
    not_started: int = Field(
        ..., description="Number of organizers who haven't started onboarding"
    )


# API Response wrapper models
class ApiResponse(BaseModel):
    statusCode: int
    message: str
    timestamp: str
    method: Optional[str] = None
    path: Optional[str] = None


class OrganizerCardStatsApiResponse(ApiResponse):
    data: OrganizerCardStats
