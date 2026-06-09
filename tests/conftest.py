import pytest
import asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from passlib.context import CryptContext
from src.main import create_app
from src.db.session import engine, Base, async_session
from src.models.tenant import Tenant
from src.models.department import Department
from src.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def app():
    application = create_app()
    yield application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def tenant_a(db_session):
    tenant = Tenant(
        name="Tenant A",
        api_key=f"test-key-a-{uuid.uuid4()}",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def tenant_b(db_session):
    tenant = Tenant(
        name="Tenant B",
        api_key=f"test-key-b-{uuid.uuid4()}",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session
        await session.rollback()


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
def hr_token(user_hr):
    from src.services.auth_service import AuthService

    # create_access_token is a static method, doesn't need db
    return AuthService.create_access_token(
        user_hr.id, user_hr.tenant_id, user_hr.is_tenant_admin
    )


@pytest.fixture
def compta_token(user_compta):
    from src.services.auth_service import AuthService

    return AuthService.create_access_token(
        user_compta.id, user_compta.tenant_id, user_compta.is_tenant_admin
    )
