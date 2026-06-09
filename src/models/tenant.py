from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.session import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    api_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    documents: Mapped[list["Document"]] = relationship(back_populates="tenant", lazy="selectin")
    departments: Mapped[list["Department"]] = relationship(back_populates="tenant", lazy="selectin")
    users: Mapped[list["User"]] = relationship(back_populates="tenant", lazy="selectin")
