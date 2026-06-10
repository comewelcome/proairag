# src/db/

## Purpose

Database session management for ProAiRag. Provides async SQLAlchemy engine, session factory, and Base declarative class.

## Ownership

Owns the database connection, session lifecycle, and declarative base. All models and services depend on this module.

## Local Contracts

- Uses async SQLAlchemy (create_async_engine, async_sessionmaker)
- Base class is DeclarativeBase for SQLAlchemy 2.0 compatibility
- get_db() is a FastAPI dependency that yields an async session
- Database URL configured via pydantic-settings (DATABASE_URL env var)
- pgvector extension must be loaded in PostgreSQL

## Module Index

- session.py — Base, engine, async_session, get_db() dependency
- rls_policies.py — (future) RLS policy management via SQLAlchemy
- seed.py — (future) Database seeding utilities

## Work Guidance

- Always use async sessions for DB operations
- get_db() dependency handles session lifecycle (open/cleanup)
- For raw SQL (RLS policies), use migrations/sql/ instead

## Verification

- DB connectivity tested via health endpoint
- RLS policies verified in migrations

## Child DOX Index

No child DOX files yet.
