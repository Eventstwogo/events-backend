from datetime import datetime
from pydantic import BaseModel


class EventTypeCreateRequest(BaseModel):
    
    event_type: str


class EventTypeResponse(BaseModel):
    id: int
    type_id: str
    event_type: str
    type_status: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



class UpdateStatusRequest(BaseModel):
    status: bool        