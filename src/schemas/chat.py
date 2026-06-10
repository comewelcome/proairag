import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="Nouvelle conversation", min_length=1, max_length=256)
    department_id: uuid.UUID | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    department_id: uuid.UUID | None
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    message: str = Field(..., min_length=1)
    department_id: uuid.UUID | None = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    sources: list | None = None
    graph_context: list | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
