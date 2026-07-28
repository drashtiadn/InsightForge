"""Pydantic schemas for ResearchSession API contracts."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.research_session import ResearchSessionStatus


class ResearchSessionCreate(BaseModel):
    """Payload for creating a new research session."""

    title: str = Field(max_length=255)
    query: str

    @field_validator("title", "query")
    @classmethod
    def must_not_be_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class ResearchSessionResponse(BaseModel):
    """Serialized research session returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    query: str
    status: ResearchSessionStatus
    created_at: datetime
    updated_at: datetime
