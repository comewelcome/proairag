# RBAC Intra-Tenant: Departments + Users + Authentication

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add department-level access control within tenants so that the accounting department cannot see HR documents, and vice versa.

**Architecture:** Introduce User, Department, and User_Department models. Replace tenant-level API key auth with user-level JWT auth (email + password). Documents are assigned to departments. Users see only documents in departments they belong to. Tenant admins see all documents in their tenant. Legacy API key auth remains for backward compatibility (service-to-service).

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, python-jose (JWT), passlib[bcrypt], PostgreSQL 15 + pgvector, Neo4j 5

---

## Design Decisions

### 1. Dual Authentication
- **User auth (new):** email + password -> JWT token. Used by human users via the API.
- **Tenant API key (existing):** X-API-Key header resolves to a tenant. Used for service-to-service calls. When using API key, the request has NO department filter (sees all tenant docs) -- this is the admin fallback.

### 2. Department Filter Logic
- Each document has an optional `department_id`.
- Each user belongs to one or more departments via the `user_departments` junction table.
- When querying documents (vector search, RAG), filter by `department_id IN (user's departments)`.
- Documents with `department_id IS NULL` are visible to ALL users in the tenant (backward compatibility for existing docs).
- A `tenant_admin` role on a user grants access to ALL documents in the tenant.

### 3. RLS Strategy
- Existing RLS on documents/chunks filters by `tenant_id` (via `current_tenant_id()` session variable).
- Add RLS on the `departments` table so users can only see their own departments.
- Department-level filtering is handled at the application layer (WHERE clause), NOT at RLS level, to keep RLS policies simple and composable.

### 4. JWT Configuration
- JWT secret derived from existing `secret_key` setting.
- Token payload: `{sub: user_id, tenant_id, is_tenant_admin, iat, exp}`.
- Token expiration: 24 hours (configurable).

---

## Database Schema (New Tables)

```sql
-- departments: one per tenant
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

-- users: one per person, belongs to a tenant
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_tenant_admin BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

-- user_departments: many-to-many with role
CREATE TABLE user_departments (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    role VARCHAR(32) DEFAULT 'member',  -- 'member' | 'admin'
    PRIMARY KEY (user_id, department_id)
);

-- Add department_id to documents
ALTER TABLE documents ADD COLUMN department_id UUID REFERENCES departments(id) ON DELETE SET NULL;
CREATE INDEX idx_documents_department_id ON documents(department_id);
```

### RLS for departments
```sql
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_department_isolation ON departments
    FOR SELECT
    USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_department_insert ON departments
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_department_update ON departments
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_department_delete ON departments
    FOR DELETE
    USING (tenant_id = current_tenant_id());
```

### Neo4j Cypher (new)
```cypher
CREATE CONSTRAINT department_unique IF NOT EXISTS
FOR (d:Department) REQUIRE (d.id, d.tenant_id) IS UNIQUE;

CREATE INDEX department_tenant_idx IF NOT EXISTS
FOR (d:Department) ON (d.tenant_id, d.name);
```

---

## Phase 1: Migrations (PostgreSQL + Neo4j)

### Task 1.1: Create departments_users migration
**Objective:** Add SQL migration for departments, users, user_departments tables and add department_id to documents.

**Files:**
- Create: `migrations/sql/004_create_departments_users.sql`

**Migration content:**
```sql
-- Create departments table
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_departments_tenant_id ON departments(tenant_id);

-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_tenant_admin BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- Create user_departments junction table
CREATE TABLE user_departments (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    department_id UUID NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    role VARCHAR(32) DEFAULT 'member',
    PRIMARY KEY (user_id, department_id)
);

-- Add department_id to documents (nullable for backward compatibility)
ALTER TABLE documents ADD COLUMN department_id UUID REFERENCES departments(id) ON DELETE SET NULL;
CREATE INDEX idx_documents_department_id ON documents(department_id);
```

**Verification:**
- Run: `docker-compose up -d postgres` (ensure migration runs via initdb.d)
- Connect to DB and verify tables exist: `\dt departments`, `\dt users`, `\dt user_departments`
- Check documents table has department_id column: `\d documents`

### Task 1.2: Create RLS policies for departments
**Objective:** Add RLS policies for departments table, same pattern as existing documents/chunks policies.

**Files:**
- Create: `migrations/sql/006_rls_departments.sql`

**Migration content:**
```sql
-- ============================================================
-- ROW-LEVEL SECURITY: Isolation des departements
-- ============================================================

ALTER TABLE departments ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Politiques RLS: departments
-- ============================================================
CREATE POLICY tenant_department_isolation ON departments
    FOR SELECT
    USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_department_insert ON departments
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_department_update ON departments
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_department_delete ON departments
    FOR DELETE
    USING (tenant_id = current_tenant_id());
```

**Verification:**
- RLS enabled on departments table
- Policies mirror the existing documents/chunks pattern

### Task 1.3: Create Neo4j department constraints + indexes
**Objective:** Add Neo4j constraints and indexes for Department nodes.

**Files:**
- Create: `migrations/cypher/003_department.cypher`

**Content:**
```cypher
CREATE CONSTRAINT department_unique IF NOT EXISTS
FOR (d:Department) REQUIRE (d.id, d.tenant_id) IS UNIQUE;

CREATE INDEX department_tenant_idx IF NOT EXISTS
FOR (d:Department) ON (d.tenant_id, d.name);
```

---

## Phase 2: ORM Models

### Task 2.1: Create Department model
**Objective:** SQLAlchemy model for departments table.

**Files:**
- Create: `src/models/department.py`

**Code:**
```python
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
```

### Task 2.2: Create User model
**Objective:** SQLAlchemy model for users table.

**Files:**
- Create: `src/models/user.py`

**Code:**
```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean, ForeignKey, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_tenant_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="users")
    departments: Mapped[list["Department"]] = relationship(
        secondary="user_departments",
        back_populates="users",
        lazy="selectin",
    )
```

### Task 2.3: Create UserDepartment model
**Objective:** SQLAlchemy model for the user_departments junction table.

**Files:**
- Create: `src/models/user_department.py`

**Code:**
```python
from sqlalchemy import String, ForeignKey, UUID, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.session import Base


class UserDepartment(Base):
    __tablename__ = "user_departments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(32), default="member")

    user: Mapped["User"] = relationship(back_populates="user_departments")
    department: Mapped["Department"] = relationship(back_populates="user_departments")
```

Wait, User and Department already have `departments` and `users` relationships through the secondary table. UserDepartment doesn't need separate back_populates. Let me fix:

```python
import uuid
from sqlalchemy import String, ForeignKey, UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.db.session import Base


class UserDepartment(Base):
    __tablename__ = "user_departments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(32), default="member")
```

### Task 2.4: Update Tenant model
**Objective:** Add relationships for departments and users to Tenant model.

**Files:**
- Modify: `src/models/tenant.py`

**Changes:** Add two relationship fields at the bottom:
```python
    departments: Mapped[list["Department"]] = relationship(back_populates="tenant", lazy="selectin")
    users: Mapped[list["User"]] = relationship(back_populates="tenant", lazy="selectin")
```

### Task 2.5: Update Document model
**Objective:** Add department_id column and department relationship to Document model.

**Files:**
- Modify: `src/models/document.py`

**Changes:**
```python
# Add imports:
from sqlalchemy import ForeignKey  # already imported

# Add column after tenant_id:
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), index=True, default=None
    )

# Add relationship at bottom:
    department: Mapped["Department | None"] = relationship(back_populates="documents")
```

**Note:** Need to add TYPE_CHECKING import for the string annotation:
```python
from __future__ import annotations
```
Or use `from typing import TYPE_CHECKING` and conditional import. Since we use string annotations, `from __future__ import annotations` is simplest.

---

## Phase 3: Pydantic Schemas

### Task 3.1: Create auth schemas
**Objective:** Request/response schemas for authentication endpoints.

**Files:**
- Create: `src/schemas/auth.py`

**Code:**
```python
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class UserCreate(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)
    full_name: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str | None
    is_tenant_admin: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str
```

### Task 3.2: Create department schemas
**Objective:** Request/response schemas for department management.

**Files:**
- Create: `src/schemas/department.py`

**Code:**
```python
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
```

### Task 3.3: Update document schemas
**Objective:** Add department_id to document create/response schemas.

**Files:**
- Modify: `src/schemas/document.py`

**Changes:**
In `DocumentCreate`:
```python
    department_id: uuid.UUID | None = None
```

In `DocumentResponse`:
```python
    department_id: uuid.UUID | None = None
```

### Task 3.4: Update tenant schemas
**Objective:** Add user creation capability to tenant creation (admin user).

**Files:**
- Modify: `src/schemas/tenant.py`

**Changes:** In `TenantCreate`, add optional admin user fields:
```python
class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    api_key: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None
    admin_full_name: str | None = None
```

---

## Phase 4: Auth Service

### Task 4.1: Create auth service
**Objective:** Password hashing, JWT generation/validation, user authentication.

**Files:**
- Create: `src/services/auth_service.py`

**Code:**
```python
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import jwt, JWTError

from src.config import get_settings
from src.models.user import User
from src.schemas.auth import UserCreate, LoginRequest

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, user_id: uuid.UUID, tenant_id: uuid.UUID, is_tenant_admin: bool = False) -> str:
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "is_tenant_admin": is_tenant_admin,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, settings.secret_key, algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> dict[str, Any] | None:
        try:
            settings = get_settings()
            return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        except JWTError:
            return None

    async def register_user(
        self, tenant_id: uuid.UUID, data: UserCreate, is_admin: bool = False
    ) -> User:
        password_hash = self.hash_password(data.password)
        user = User(
            tenant_id=tenant_id,
            email=data.email,
            password_hash=password_hash,
            full_name=data.full_name,
            is_tenant_admin=is_admin,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, data: LoginRequest) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.email == data.email,
                User.is_active == True,
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not self.verify_password(data.password, user.password_hash):
            return None
        return user

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, tenant_id: uuid.UUID, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id, User.email == email)
        )
        return result.scalar_one_or_none()


def get_auth_service(db: AsyncSession) -> AuthService:
    return AuthService(db)
```

---

## Phase 5: Department Service

### Task 5.1: Create department service
**Objective:** CRUD for departments, user assignment to departments, with tenant isolation.

**Files:**
- Create: `src/services/department_service.py`

**Code:**
```python
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.models.department import Department
from src.models.user import User
from src.models.user_department import UserDepartment
from src.schemas.department import DepartmentCreate, DepartmentUpdate


class DepartmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: uuid.UUID, data: DepartmentCreate) -> Department:
        dept = Department(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
        )
        self.db.add(dept)
        await self.db.commit()
        await self.db.refresh(dept)
        return dept

    async def get_by_id(self, department_id: uuid.UUID) -> Department | None:
        result = await self.db.execute(
            select(Department)
            .options(selectinload(Department.users))
            .where(Department.id == department_id)
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[Department]:
        result = await self.db.execute(
            select(Department).where(Department.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def update(
        self, department_id: uuid.UUID, tenant_id: uuid.UUID, data: DepartmentUpdate
    ) -> Department | None:
        dept = await self.get_by_id(department_id)
        if not dept or dept.tenant_id != tenant_id:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(dept, key, value)
        await self.db.commit()
        await self.db.refresh(dept)
        return dept

    async def delete(self, department_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        dept = await self.get_by_id(department_id)
        if not dept or dept.tenant_id != tenant_id:
            return False
        await self.db.delete(dept)
        await self.db.commit()
        return True

    async def assign_user(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        department_id: uuid.UUID,
        role: str = "member",
    ) -> UserDepartment | None:
        # Verify user belongs to tenant
        user_result = await self.db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        if not user_result.scalar_one_or_none():
            return None

        # Verify department belongs to tenant
        dept = await self.get_by_id(department_id)
        if not dept or dept.tenant_id != tenant_id:
            return None

        ud = UserDepartment(
            user_id=user_id,
            department_id=department_id,
            role=role,
        )
        self.db.add(ud)
        await self.db.commit()
        await self.db.refresh(ud)
        return ud

    async def remove_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, department_id: uuid.UUID
    ) -> bool:
        result = await self.db.execute(
            select(UserDepartment).where(
                UserDepartment.user_id == user_id,
                UserDepartment.department_id == department_id,
            )
        )
        ud = result.scalar_one_or_none()
        if not ud:
            return False

        # Verify department belongs to tenant
        dept = await self.get_by_id(department_id)
        if not dept or dept.tenant_id != tenant_id:
            return False

        await self.db.delete(ud)
        await self.db.commit()
        return True

    async def get_user_department_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(UserDepartment.department_id).where(
                UserDepartment.user_id == user_id
            )
        )
        return [row[0] for row in result.all()]

    async def get_user_department_roles(
        self, user_id: uuid.UUID
    ) -> dict[uuid.UUID, str]:
        result = await self.db.execute(
            select(UserDepartment.department_id, UserDepartment.role).where(
                UserDepartment.user_id == user_id
            )
        )
        return {row[0]: row[1] for row in result.all()}


def get_department_service(db: AsyncSession) -> DepartmentService:
    return DepartmentService(db)
```

---

## Phase 6: Update Tenant Service

### Task 6.1: Add admin user creation to tenant service
**Objective:** When creating a tenant, optionally create an admin user and a "General" department.

**Files:**
- Modify: `src/services/tenant_service.py`

**Changes:** Update the `create` method to accept optional admin user fields:
```python
    async def create(
        self,
        data: TenantCreate,
        admin_email: str | None = None,
        admin_password: str | None = None,
        admin_full_name: str | None = None,
    ) -> Tenant:
        api_key = data.api_key or f"sk-{secrets.token_urlsafe(32)}"
        tenant = Tenant(name=data.name, api_key=api_key)
        self.db.add(tenant)
        await self.db.flush()

        # Create admin user if provided
        if admin_email and admin_password:
            from src.models.user import User
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            admin = User(
                tenant_id=tenant.id,
                email=admin_email,
                password_hash=pwd_context.hash(admin_password),
                full_name=admin_full_name,
                is_tenant_admin=True,
            )
            self.db.add(admin)

        # Create default "General" department
        from src.models.department import Department
        general_dept = Department(
            tenant_id=tenant.id,
            name="General",
            description="Default department for all tenant members",
        )
        self.db.add(general_dept)

        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant
```

---

## Phase 7: Middleware Update

### Task 7.1: Update middleware to support JWT auth
**Objective:** Extend TenantContextMiddleware to handle JWT tokens in addition to API keys. Inject user_id and department context into request.state.

**Files:**
- Modify: `src/middleware/tenant.py`

**Design:** The middleware checks headers in this order:
1. `Authorization: Bearer <JWT>` -- if present, decode JWT, resolve user, inject user context
2. `X-API-Key` -- if present, resolve tenant (existing behavior), no user context (admin-level access)
3. If neither present and path is not public, return 401

**Changes:**
```python
import uuid
from typing import Annotated, Any
from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.tenant import Tenant
from src.models.user import User
from src.db.session import async_session


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        public_paths = ["/health", "/docs", "/openapi.json", "/redoc"]
        if request.url.path in public_paths:
            return await call_next(request)

        # Try JWT auth first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            user_context = await self._resolve_jwt(token)
            if user_context:
                request.state.tenant_id = user_context["tenant_id"]
                request.state.tenant = user_context["tenant"]
                request.state.user_id = user_context["user_id"]
                request.state.user = user_context["user"]
                request.state.is_tenant_admin = user_context["is_tenant_admin"]
                request.state.auth_mode = "jwt"
                response = await call_next(request)
                return response

        # Fall back to API key auth
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="Missing authentication. Provide Authorization: Bearer <JWT> or X-API-Key header",
            )

        async with async_session() as session:
            result = await session.execute(
                select(Tenant).where(
                    Tenant.api_key == api_key, Tenant.is_active == True
                )
            )
            tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

        request.state.tenant_id = tenant.id
        request.state.tenant = tenant
        request.state.auth_mode = "api_key"

        response = await call_next(request)
        return response

    async def _resolve_jwt(self, token: str) -> dict[str, Any] | None:
        from src.services.auth_service import AuthService

        payload = AuthService.decode_token(token)
        if not payload:
            return None

        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenant_id"])

        async with async_session() as session:
            result = await session.execute(
                select(User).where(
                    User.id == user_id,
                    User.tenant_id == tenant_id,
                    User.is_active == True,
                )
            )
            user = result.scalar_one_or_none()
            if not user:
                return None

            tenant_result = await session.execute(
                select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active == True)
            )
            tenant = tenant_result.scalar_one_or_none()
            if not tenant:
                return None

        return {
            "user_id": user.id,
            "user": user,
            "tenant_id": tenant.id,
            "tenant": tenant,
            "is_tenant_admin": payload.get("is_tenant_admin", False),
        }


def get_tenant_id(request: Request) -> uuid.UUID:
    if not hasattr(request.state, "tenant_id"):
        raise HTTPException(status_code=400, detail="Tenant context missing")
    return request.state.tenant_id


def get_tenant(request: Request) -> Tenant:
    if not hasattr(request.state, "tenant"):
        raise HTTPException(status_code=400, detail="Tenant context missing")
    return request.state.tenant


def get_user_id(request: Request) -> uuid.UUID | None:
    return getattr(request.state, "user_id", None)


def get_user(request: Request) -> User | None:
    return getattr(request.state, "user", None)


def get_is_tenant_admin(request: Request) -> bool:
    return getattr(request.state, "is_tenant_admin", False)


def get_auth_mode(request: Request) -> str:
    return getattr(request.state, "auth_mode", "api_key")


TenantId = Annotated[uuid.UUID, Depends(get_tenant_id)]
TenantDep = Annotated[Tenant, Depends(get_tenant)]
UserId = Annotated[uuid.UUID | None, Depends(get_user_id)]
UserDep = Annotated[User | None, Depends(get_user)]
IsTenantAdmin = Annotated[bool, Depends(get_is_tenant_admin)]
AuthMode = Annotated[str, Depends(get_auth_mode)]
```

---

## Phase 8: Ingestion Service Update

### Task 8.1: Add department_id to ingestion
**Objective:** Pass department_id through the ingestion pipeline. Documents and chunks are tagged with the department.

**Files:**
- Modify: `src/services/ingestion_service.py`

**Changes:**
In `ingest_document` method, add `department_id` parameter:
```python
    async def ingest_document(
        self,
        tenant_id: uuid.UUID,
        title: str,
        content: str,
        source: str | None = None,
        content_type: str = "text",
        department_id: uuid.UUID | None = None,
    ) -> Document:
```

Update Document creation:
```python
        document = Document(
            tenant_id=tenant_id,
            department_id=department_id,
            title=title,
            content=content,
            source=source,
            content_type=content_type,
            is_processed=False,
        )
```

---

## Phase 9: Vector Service Update

### Task 9.1: Add department filter to vector search
**Objective:** Filter vector search results by the authenticated user's departments.

**Files:**
- Modify: `src/services/vector_service.py`

**Changes:**
In `search` method, add `department_ids` and `is_tenant_admin` parameters:
```python
    async def search(
        self,
        query: str,
        tenant_id: uuid.UUID,
        top_k: int | None = None,
        department_ids: list[uuid.UUID] | None = None,
        is_tenant_admin: bool = False,
    ) -> list[dict]:
```

Update the SQL query to add department filter:
```python
        # Build department filter
        dept_filter = ""
        dept_params: dict = {}
        if department_ids and not is_tenant_admin:
            dept_uuids = [str(d) for d in department_ids]
            # Documents with NULL department_id are visible to all (backward compat)
            dept_filter = "AND (c.department_id IS NULL OR c.department_id = ANY(:department_ids))"
            dept_params["department_ids"] = dept_uuids

        result = await self.db.execute(
            text(f"""
                SELECT
                    c.id,
                    c.content,
                    c.chunk_index,
                    c.document_id,
                    c.department_id,
                    d.title as document_title,
                    1 - (c.embedding <=> :embedding::vector) as similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.tenant_id = :tenant_id
                {dept_filter}
                ORDER BY c.embedding <=> :embedding::vector
                LIMIT :top_k
            """),
            {
                "embedding": embedding_str,
                "tenant_id": str(tenant_id),
                "top_k": top_k,
                **dept_params,
            },
        )
```

---

## Phase 10: RAG Service Update

### Task 10.1: Add department context to RAG queries
**Objective:** RAG service resolves user's departments and passes them to vector search.

**Files:**
- Modify: `src/services/rag_service.py`

**Changes:**
Update `query` method signature:
```python
    async def query(
        self,
        tenant_id: uuid.UUID,
        rag_query: RAGQuery,
        user_id: uuid.UUID | None = None,
        is_tenant_admin: bool = False,
    ) -> RAGResponse:
```

Before vector search, resolve departments:
```python
        # Resolve user departments for filtering
        department_ids: list[uuid.UUID] | None = None
        if user_id and not is_tenant_admin:
            from src.services.department_service import get_department_service
            dept_service = get_department_service(self.db)
            department_ids = await dept_service.get_user_department_ids(user_id)
```

Pass to vector search:
```python
        vector_results = await self.vector_service.search(
            query=rag_query.query,
            tenant_id=tenant_id,
            top_k=rag_query.top_k,
            department_ids=department_ids,
            is_tenant_admin=is_tenant_admin,
        )
```

---

## Phase 11: Graph Service Update

### Task 11.1: Sync departments to Neo4j
**Objective:** When documents are ingested with a department, create a Department node and link it.

**Files:**
- Modify: `src/graph/graph_sync.py`

**Changes:**
In `sync_document`, add department sync:
```python
    async def sync_document(
        self,
        tenant_id: uuid.UUID,
        doc_id: uuid.UUID,
        chunks: list[dict],
        department_id: uuid.UUID | None = None,
    ):
        # ... existing tenant/doc creation ...

        # Create/merge department and link
        if department_id:
            await self.neo4j.execute(
                """
                MERGE (t:Tenant {id: $tenant_id})
                MERGE (dep:Department {id: $department_id, tenant_id: $tenant_id})
                ON CREATE SET dep.created_at = datetime()
                MERGE (d:Document {id: $doc_id})
                SET d.department_id = $department_id
                MERGE (d)-[:BELONGS_TO]->(dep)
                MERGE (dep)-[:IN_TENANT]->(t)
                """,
                {
                    "tenant_id": str(tenant_id),
                    "department_id": str(department_id),
                    "doc_id": str(doc_id),
                },
            )
```

**Also modify:** `src/services/ingestion_service.py` to pass `department_id` to graph sync (once graph sync is called from ingestion).

---

## Phase 12: API Routes

### Task 12.1: Create auth routes
**Objective:** Login, register, and token refresh endpoints.

**Files:**
- Create: `src/api/auth.py`

**Code:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import TenantId
from src.services.auth_service import get_auth_service
from src.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = get_auth_service(db)
    user = await service.authenticate(data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = service.create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        is_tenant_admin=user.is_tenant_admin,
    )
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    data: UserCreate,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_auth_service(db)

    # Check if email already exists in tenant
    existing = await service.get_user_by_email(tenant_id, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered for this tenant",
        )

    user = await service.register_user(tenant_id, data)
    token = service.create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        is_tenant_admin=user.is_tenant_admin,
    )
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )
```

### Task 12.2: Create department routes
**Objective:** CRUD endpoints for departments and user assignments.

**Files:**
- Create: `src/api/departments.py`

**Code:**
```python
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.middleware.tenant import TenantId, UserId, IsTenantAdmin
from src.services.department_service import get_department_service
from src.services.auth_service import get_auth_service
from src.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    UserDepartmentAssignment,
    UserDepartmentResponse,
)

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("/", response_model=list[DepartmentResponse])
async def list_departments(
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    return await service.list_by_tenant(tenant_id)


@router.post("/", response_model=DepartmentResponse, status_code=201)
async def create_department(
    data: DepartmentCreate,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    return await service.create(tenant_id, data)


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: uuid.UUID,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    dept = await service.get_by_id(department_id)
    if not dept or dept.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    data: DepartmentUpdate,
    department_id: uuid.UUID,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    dept = await service.update(department_id, tenant_id, data)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.delete("/{department_id}", status_code=204)
async def delete_department(
    department_id: uuid.UUID,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    if not await service.delete(department_id, tenant_id):
        raise HTTPException(status_code=404, detail="Department not found")


@router.post("/{department_id}/users", response_model=UserDepartmentResponse, status_code=201)
async def assign_user_to_department(
    data: UserDepartmentAssignment,
    department_id: uuid.UUID,
    tenant_id: TenantId = ...,  # type: ignore
    user_id: UserId = ...,  # type: ignore
    is_tenant_admin: IsTenantAdmin = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    # Only tenant admins or existing department admins can assign users
    # (simplified: require tenant admin for now)
    if not user_id or not is_tenant_admin:
        raise HTTPException(status_code=403, detail="Tenant admin required")

    service = get_department_service(db)
    ud = await service.assign_user(data.user_id, tenant_id, department_id, data.role)
    if not ud:
        raise HTTPException(status_code=404, detail="User or department not found")
    return ud


@router.delete("/{department_id}/users/{user_id}", status_code=204)
async def remove_user_from_department(
    user_id: uuid.UUID,
    department_id: uuid.UUID,
    tenant_id: TenantId = ...,  # type: ignore
    db: AsyncSession = Depends(get_db),
):
    service = get_department_service(db)
    if not await service.remove_user(user_id, tenant_id, department_id):
        raise HTTPException(status_code=404, detail="Assignment not found")
```

### Task 12.3: Update documents route
**Objective:** Add department_id to document creation.

**Files:**
- Modify: `src/api/documents.py`

**Changes:** The DocumentCreate schema now has `department_id`. No API route changes needed -- it flows through automatically from the schema update.

### Task 12.4: Update RAG route
**Objective:** Pass user context to RAG service for department filtering.

**Files:**
- Modify: `src/api/rag.py`

**Changes:**
```python
from src.middleware.tenant import TenantId, UserId, IsTenantAdmin

@router.post("/query", response_model=RAGResponse)
async def rag_query(
    query: RAGQuery,
    db: AsyncSession = Depends(get_db),
    tenant_id: TenantId = ...,  # type: ignore
    user_id: UserId = ...,  # type: ignore
    is_tenant_admin: IsTenantAdmin = ...,  # type: ignore
):
    service = get_rag_service(db)
    result = await service.query(
        tenant_id=tenant_id,
        rag_query=query,
        user_id=user_id,
        is_tenant_admin=is_tenant_admin,
    )
    return result
```

### Task 12.5: Register new routes in main.py
**Objective:** Add auth and departments routers to the FastAPI app.

**Files:**
- Modify: `src/main.py`

**Changes:**
```python
from src.api import tenants, documents, rag, auth, departments

# ... in create_app():
    app.include_router(auth.router)
    app.include_router(departments.router)
```

---

## Phase 13: Config Update

### Task 13.1: Add JWT settings
**Objective:** Add JWT configuration to Settings.

**Files:**
- Modify: `src/config.py`

**Changes:** Add to Settings class:
```python
    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
```

---

## Phase 14: Tests

### Task 14.1: Update test fixtures
**Objective:** Add user, department, and JWT token fixtures to conftest.py.

**Files:**
- Modify: `tests/conftest.py`

**Changes:** Add fixtures:
```python
from src.models.user import User
from src.models.department import Department
from src.services.auth_service import AuthService
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@pytest.fixture
async def dept_hr(tenant_a, db_session):
    dept = Department(tenant_id=tenant_a.id, name="RH", description="Ressources Humaines")
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept

@pytest.fixture
async def dept_compta(tenant_a, db_session):
    dept = Department(tenant_id=tenant_a.id, name="Comptabilite", description="Finance")
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    return dept

@pytest.fixture
async def user_hr(tenant_a, dept_hr, db_session):
    user = User(
        tenant_id=tenant_a.id,
        email="hr@company.com",
        password_hash=pwd_context.hash("password123"),
        full_name="HR User",
    )
    db_session.add(user)
    await db_session.flush()

    from src.models.user_department import UserDepartment
    ud = UserDepartment(user_id=user.id, department_id=dept_hr.id, role="member")
    db_session.add(ud)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def user_compta(tenant_a, dept_compta, db_session):
    user = User(
        tenant_id=tenant_a.id,
        email="compta@company.com",
        password_hash=pwd_context.hash("password123"),
        full_name="Compta User",
    )
    db_session.add(user)
    await db_session.flush()

    from src.models.user_department import UserDepartment
    ud = UserDepartment(user_id=user.id, department_id=dept_compta.id, role="member")
    db_session.add(ud)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def hr_token(user_hr):
    service = AuthService  # type auth_service
    return AuthService.create_access_token(user_hr.id, user_hr.tenant_id)

Wait, create_access_token is an instance method. Fix:
```python
@pytest.fixture
def hr_token(user_hr):
    # create_access_token needs the instance but doesn't use db
    # We can call it on a dummy instance or make it a classmethod
    from src.services.auth_service import AuthService
    from src.db.session import AsyncSession
    # For testing, create a mock db or use the method statically
    service = AuthService.__new__(AuthService)
    return service.create_access_token(user_hr.id, user_hr.tenant_id, user_hr.is_tenant_admin)
```

Actually, let me make `create_access_token` a static method or at least not require `self.db`. Looking at the implementation, it only uses `get_settings()`, so it can be static. Let me update the plan:

**Auth service fix:** Change `create_access_token` and `decode_token` to `@staticmethod`.

### Task 14.2: Create department isolation tests
**Objective:** Verify that HR user cannot see Comptabilite documents and vice versa.

**Files:**
- Create: `tests/test_department_isolation.py`

**Tests:**
```python
import pytest
from src.models.document import Document
from src.models.chunk import Chunk
from src.services.auth_service import AuthService
from src.services.vector_service import get_vector_service


class TestDepartmentIsolation:
    """Tests CRITIQUES: isolation inter-departements.
    Un echec ici = fuite de donnees entre departements."""

    @pytest.mark.asyncio
    async def test_hr_cannot_see_compta_documents(
        self, tenant_a, dept_hr, dept_compta, user_hr, db_session
    ):
        # Create a compta document
        compta_doc = Document(
            tenant_id=tenant_a.id,
            department_id=dept_compta.id,
            title="Paie employees",
            content="Salaires confidentiels",
        )
        db_session.add(compta_doc)
        await db_session.commit()
        await db_session.refresh(compta_doc)

        # Create a chunk
        chunk = Chunk(
            tenant_id=tenant_a.id,
            document_id=compta_doc.id,
            content="Salaire: 5000 EUR",
            embedding=[0.1] * 384,
            chunk_index=0,
        )
        db_session.add(chunk)
        await db_session.commit()

        # HR user should NOT see this in vector search
        vector_service = get_vector_service(db_session)
        hr_dept_ids = [dept_hr.id]
        results = await vector_service.search(
            query="salaire",
            tenant_id=tenant_a.id,
            department_ids=hr_dept_ids,
            is_tenant_admin=False,
        )
        assert all(r.get("document_id") != compta_doc.id for r in results)

    @pytest.mark.asyncio
    async def test_tenant_admin_sees_all_departments(
        self, tenant_a, dept_hr, dept_compta, user_compta, db_session
    ):
        # Create HR document
        hr_doc = Document(
            tenant_id=tenant_a.id,
            department_id=dept_hr.id,
            title="Politique RH",
            content="Conges payes",
        )
        db_session.add(hr_doc)
        await db_session.commit()
        await db_session.refresh(hr_doc)

        chunk = Chunk(
            tenant_id=tenant_a.id,
            document_id=hr_doc.id,
            content="Politique de conges",
            embedding=[0.1] * 384,
            chunk_index=0,
        )
        db_session.add(chunk)
        await db_session.commit()

        # Compta user with is_tenant_admin=True should see HR docs
        vector_service = get_vector_service(db_session)
        results = await vector_service.search(
            query="conges",
            tenant_id=tenant_a.id,
            department_ids=[dept_compta.id],
            is_tenant_admin=True,
        )
        # Should find the HR document because admin bypasses dept filter
        assert any(r.get("document_id") == hr_doc.id for r in results)

    @pytest.mark.asyncio
    async def test_null_department_visible_to_all(
        self, tenant_a, dept_hr, db_session
    ):
        # Document with no department (backward compat)
        doc = Document(
            tenant_id=tenant_a.id,
            department_id=None,
            title="Document general",
            content="Visible par tous",
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        chunk = Chunk(
            tenant_id=tenant_a.id,
            document_id=doc.id,
            content="Document general",
            embedding=[0.1] * 384,
            chunk_index=0,
        )
        db_session.add(chunk)
        await db_session.commit()

        # Should be visible to any department user
        vector_service = get_vector_service(db_session)
        results = await vector_service.search(
            query="general",
            tenant_id=tenant_a.id,
            department_ids=[dept_hr.id],
            is_tenant_admin=False,
        )
        assert any(r.get("document_id") == doc.id for r in results)
```

### Task 14.3: Create auth tests
**Objective:** Test login, JWT token generation, and middleware auth.

**Files:**
- Create: `tests/test_auth.py`

**Tests:**
```python
import pytest
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_success(self, client, tenant_a, user_hr, db_session):
        response = await client.post(
            "/auth/login",
            json={"email": "hr@company.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "hr@company.com"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, tenant_a, user_hr, db_session):
        response = await client.post(
            "/auth/login",
            json={"email": "hr@company.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        response = await client.post(
            "/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_auth_header(self, client, tenant_a, user_hr, dept_hr, db_session):
        from src.services.auth_service import AuthService
        service = AuthService.__new__(AuthService)
        token = service.create_access_token(user_hr.id, user_hr.tenant_id)

        response = await client.post(
            "/documents/",
            json={"title": "Test", "content": "Test content"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_no_auth_returns_401(self, client):
        response = await client.post(
            "/documents/",
            json={"title": "Test", "content": "Test"},
        )
        assert response.status_code == 401


class TestDepartmentEndpoints:
    @pytest.mark.asyncio
    async def test_create_department(self, client, tenant_a):
        response = await client.post(
            "/departments/",
            json={"name": "Marketing", "description": "Dept marketing"},
            headers={"X-API-Key": tenant_a.api_key},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Marketing"

    @pytest.mark.asyncio
    async def test_list_departments(self, client, tenant_a, dept_hr, dept_compta):
        response = await client.get(
            "/departments/",
            headers={"X-API-Key": tenant_a.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
```

---

## Phase 15: DOX Update

### Task 15.1: Update all AGENTS.md files
**Objective:** Update the DOX hierarchy to reflect new models, services, schemas, and API routes.

**Files to update:**
- `AGENTS.md` (root) -- no structural changes
- `src/AGENTS.md` -- update Child DOX Index if needed
- `src/models/AGENTS.md` -- add User, Department, UserDepartment to Model Index
- `src/schemas/AGENTS.md` -- add auth.py, department.py to Schema Index
- `src/services/AGENTS.md` -- add auth_service.py, department_service.py to Service Index
- `src/api/AGENTS.md` -- add auth, departments routes to Endpoints
- `src/middleware/AGENTS.md` -- update to describe JWT + API key dual auth
- `tests/AGENTS.md` -- add test_auth.py, test_department_isolation.py to Test Index
- `migrations/AGENTS.md` -- add 004, 006 SQL and 003 Cypher to Migration Index

---

## Summary of All File Changes

### New files (14):
1. `migrations/sql/004_create_departments_users.sql`
2. `migrations/sql/006_rls_departments.sql`
3. `migrations/cypher/003_department.cypher`
4. `src/models/department.py`
5. `src/models/user.py`
6. `src/models/user_department.py`
7. `src/schemas/auth.py`
8. `src/schemas/department.py`
9. `src/services/auth_service.py`
10. `src/services/department_service.py`
11. `src/api/auth.py`
12. `src/api/departments.py`
13. `tests/test_department_isolation.py`
14. `tests/test_auth.py`

### Modified files (15):
1. `src/models/tenant.py` -- add relationships
2. `src/models/document.py` -- add department_id
3. `src/schemas/tenant.py` -- add admin user fields
4. `src/schemas/document.py` -- add department_id
5. `src/services/tenant_service.py` -- admin user + default dept creation
6. `src/services/ingestion_service.py` -- department_id param
7. `src/services/vector_service.py` -- department filter
8. `src/services/rag_service.py` -- user/department context
9. `src/graph/graph_sync.py` -- department node sync
10. `src/middleware/tenant.py` -- JWT + API key dual auth
11. `src/api/documents.py` -- department_id flows through schema
12. `src/api/rag.py` -- user context params
13. `src/main.py` -- new routers
14. `src/config.py` -- JWT settings
15. `tests/conftest.py` -- user/dept/token fixtures

### DOX files to update (7):
1. `src/models/AGENTS.md`
2. `src/schemas/AGENTS.md`
3. `src/services/AGENTS.md`
4. `src/api/AGENTS.md`
5. `src/middleware/AGENTS.md`
6. `tests/AGENTS.md`
7. `migrations/AGENTS.md`

**Total: 29 new/modified code files + 7 DOX updates = 36 file changes.**

---

## Execution Order

Phases 1-3 are independent and can run in parallel. Phase 4 depends on Phase 3. Phase 5 depends on Phase 2. Phase 6 depends on Phases 2+3+4. Phase 7 depends on Phase 4. Phases 8-11 depend on Phases 2-7. Phase 12 depends on all previous. Phase 13 is independent. Phase 14 depends on all. Phase 15 is the final DOX closeout.

Recommended sequential order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11 -> 12 -> 13 -> 14 -> 15
