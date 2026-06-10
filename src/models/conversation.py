from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, UUID, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.session import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), index=True, default=None
    )
    title: Mapped[str] = mapped_column(String(256), default="Nouvelle conversation")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="conversations")
    department: Mapped["Department | None"] = relationship()
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", lazy="selectin", cascade="all, delete-orphan"
    )
