import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    api_key: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None
    admin_full_name: str | None = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    api_key: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    api_key: str | None = None
