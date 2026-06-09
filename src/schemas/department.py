import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DepartmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class UserDepartmentAssignment(BaseModel):
    user_id: uuid.UUID
    role: str = Field(default="member", pattern="^(member|admin)$")


class UserDepartmentResponse(BaseModel):
    user_id: uuid.UUID
    department_id: uuid.UUID
    role: str
    email: str | None = None
    full_name: str | None = None

    model_config = {"from_attributes": True}
