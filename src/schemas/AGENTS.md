# src/schemas/

## Purpose

Pydantic v2 schemas for request/response validation in ProAiRag API. Enforces data contracts between API clients and the application.

## Ownership

Owns all request/response models. Used by API routes for input validation and response serialization.

## Local Contracts

- All schemas use Pydantic v2 BaseModel
- Response schemas include model_config = {"from_attributes": True} for ORM compatibility
- Request schemas use Field() for validation constraints
- Schemas are separate from models — no SQLAlchemy dependencies

## Schema Index

- tenant.py — TenantCreate, TenantResponse, TenantUpdate (+ admin_email, admin_password, admin_full_name)
- document.py — DocumentCreate, DocumentResponse (+ department_id)
- rag.py — RAGQuery, RAGResponse, RAGSource
- auth.py — UserCreate, UserResponse (+ is_super_admin), LoginRequest, TokenResponse
- department.py — DepartmentCreate, DepartmentResponse, DepartmentUpdate, UserDepartmentAssignment, UserDepartmentResponse
- chat.py — ConversationCreate, ConversationResponse, MessageCreate, MessageResponse
- settings.py — RagSettingsUpdate, RagSettingsResponse, SystemStats

## Work Guidance

- Keep schemas thin — validation only, no business logic
- Use optional fields for update schemas (PATCH semantics)
- RAG schemas support both vector and graph sources

## Verification

- Schema validation tested via API integration tests

## Child DOX Index

No child DOX files yet.
