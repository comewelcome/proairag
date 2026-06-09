import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1)
    source: str | None = None
    content_type: str = "text"
    department_id: uuid.UUID | None = None


class DocumentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    department_id: uuid.UUID | None = None
    title: str
    source: str | None
    content_type: str
    is_processed: bool
    created_at: datetime

    model_config = {"from_attributes": True}
