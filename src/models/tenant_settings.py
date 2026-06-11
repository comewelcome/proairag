from __future__ import annotations

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, UUID, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.db.session import Base


class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    chunk_size: Mapped[int] = mapped_column(Integer, default=512)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=64)
    top_k: Mapped[int] = mapped_column(Integer, default=5)
    embedding_model: Mapped[str] = mapped_column(
        String(256), default="sentence-transformers/paraphrase-MiniLM-L3-v2"
    )
    llm_provider: Mapped[str] = mapped_column(String(32), default="openai")
    llm_model: Mapped[str | None] = mapped_column(String(128))
    openai_api_key: Mapped[str | None] = mapped_column(Text)
    openai_api_base: Mapped[str | None] = mapped_column(String(256))
    ollama_base_url: Mapped[str | None] = mapped_column(String(256))
    ollama_model: Mapped[str | None] = mapped_column(String(128))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
