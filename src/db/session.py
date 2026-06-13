from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from src.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_db_with_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AsyncSession:
    """DB session with RLS tenant context set for Row-Level Security."""
    tid = getattr(request.state, "tenant_id", None)
    if tid:
        await db.execute(text(f"SET LOCAL app.current_tenant_id = '{tid}'"))
    return db
