from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from shared.utils.security_validators import contains_xss
from shared.utils.validators import (
    has_excessive_repetition,
    normalize_whitespace,
    validate_length_range,
)


class QueryCreateRequest(BaseModel):
    """
    Schema for creating a new query with validation and sanitization.
    """

    user_id: str = Field(..., description="ID of the user asking the question")
    query: str = Field(
        ..., description="The query text", min_length=10, max_length=2000
    )

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, v: str) -> str:
        """
        Normalize whitespace before all validations.
        """
        if not isinstance(v, str):
            raise TypeError("Query must be a string.")
        return normalize_whitespace(v)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """
        Perform multiple validations on the query string.
        """
        if not v.strip():
            raise ValueError("Query must not be empty or only whitespace.")

        if contains_xss(v):
            raise ValueError(
                "Query contains potentially unsafe input (XSS detected)."
            )

        if has_excessive_repetition(v):
            raise ValueError("Query contains excessive repetition.")

        if not validate_length_range(v, min_len=10, max_len=2000):
            raise ValueError("Query length is outside the acceptable range.")

        return v


class QueryAnswerRequest(BaseModel):
    """
    Schema for adding an answer to a query with proper validation.
    """

    user_id: str = Field(..., description="ID of the user providing the answer")
    answer: str = Field(
        ..., description="The answer text", min_length=1, max_length=2000
    )

    @field_validator("answer", mode="before")
    @classmethod
    def normalize_answer(cls, v: str) -> str:
        """
        Normalize whitespace before other validations.
        """
        if not isinstance(v, str):
            raise TypeError("Answer must be a string.")
        return normalize_whitespace(v)

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str) -> str:
        """
        Validate content of the answer.
        """
        if not v.strip():
            raise ValueError("Answer must not be empty or just whitespace.")

        if contains_xss(v):
            raise ValueError(
                "Answer contains potentially unsafe input (XSS detected)."
            )

        if has_excessive_repetition(v):
            raise ValueError("Answer contains excessive repetition.")

        if not validate_length_range(v, min_len=1, max_len=2000):
            raise ValueError("Answer length is outside the acceptable range.")

        return v


class QueryAnswerResponse(BaseModel):
    """Schema for query answer response"""

    answer_id: str = Field(..., description="Unique identifier for the answer")
    answer: str = Field(..., description="The answer text")
    answered_by: str = Field(..., description="User ID who provided the answer")
    answered_by_username: Optional[str] = Field(
        None, description="Username of who provided the answer"
    )
    answered_at: datetime = Field(
        ..., description="When the answer was provided"
    )

    class Config:
        from_attributes = True


class QueryResponse(BaseModel):
    """Schema for query response"""

    query_id: str = Field(..., description="Unique identifier for the query")
    organizer_id: str = Field(
        ..., description="ID of the organizer who created the query"
    )
    organizer_username: Optional[str] = Field(
        None, description="Username of the organizer"
    )
    admin_user_id: Optional[str] = Field(
        None, description="ID of the admin handling the query"
    )
    admin_username: Optional[str] = Field(
        None, description="Username of the admin handling the query"
    )
    query: str = Field(..., description="The query text")
    answers: Optional[List[Dict[str, Any]]] = Field(
        None, description="List of answers"
    )
    query_status: str = Field(
        ..., description="Status of the query (open, closed, etc.)"
    )
    created_at: datetime = Field(..., description="When the query was created")
    updated_at: datetime = Field(
        ..., description="When the query was last updated"
    )

    class Config:
        from_attributes = True


class QueryListResponse(BaseModel):
    """Schema for listing queries"""

    queries: List[QueryResponse] = Field(..., description="List of queries")
    total_count: int = Field(..., description="Total number of queries")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        from_attributes = True


class QueryCreateResponse(BaseModel):
    """Schema for query creation response"""

    query_id: str = Field(
        ..., description="Unique identifier for the created query"
    )
    message: str = Field(..., description="Success message")

    class Config:
        from_attributes = True


class QueryAnswerCreateResponse(BaseModel):
    """Schema for query answer creation response"""

    answer_id: str = Field(..., description="Unique identifier for the answer")
    query_status: str = Field(..., description="Updated status of the query")

    class Config:
        from_attributes = True


class QueryStatusUpdateResponse(BaseModel):
    """Schema for query status update response"""

    query_id: str = Field(..., description="Unique identifier for the query")
    old_status: str = Field(..., description="Previous status of the query")
    new_status: str = Field(..., description="New status of the query")
    admin_user_id: Optional[str] = Field(
        None, description="ID of the admin who updated the status"
    )

    class Config:
        from_attributes = True
