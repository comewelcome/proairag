from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.session import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="departments")
    documents: Mapped[list["Document"]] = relationship(back_populates="department", lazy="selectin")
    users: Mapped[list["User"]] = relationship(
        secondary="user_departments",
        back_populates="departments",
        lazy="selectin",
    )
