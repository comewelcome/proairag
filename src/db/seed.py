"""Auto-seed: create super admin and dashboard tenants on startup (idempotent)."""

import uuid
import logging

from sqlalchemy import select

from src.config import get_settings
from src.db.session import async_session
from src.models.tenant import Tenant
from src.models.department import Department
from src.models.user import User
from src.models.user_department import UserDepartment
from src.services.auth_service import pwd_context

logger = logging.getLogger(__name__)


async def _user_exists(email: str) -> bool:
    """Check if a user with the given email already exists."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none() is not None


async def seed_super_admin():
    """Create the global super admin if not already present."""
    settings = get_settings()
    if not settings.super_admin_email or not settings.super_admin_password:
        return

    if await _user_exists(settings.super_admin_email):
        return

    async with async_session() as session:
        admin_user = User(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, "super-admin"),
            tenant_id=uuid.uuid5(uuid.NAMESPACE_DNS, "super-admin-tenant"),
            email=settings.super_admin_email,
            password_hash=pwd_context.hash(settings.super_admin_password),
            full_name="Super Admin",
            is_tenant_admin=True,
            is_super_admin=True,
            is_active=True,
        )
        # Super admin needs a tenant to attach to (dummy tenant)
        super_tenant = Tenant(
            id=admin_user.tenant_id,
            name="Super Admin System",
            api_key=f"sk-superadmin-{uuid.uuid4()}",
            is_active=True,
        )
        session.add(super_tenant)
        session.add(admin_user)
        await session.commit()
        logger.info(f"Seeded super admin: {settings.super_admin_email}")


async def seed_dashboard_tenants():
    """Auto-seed dashboard tenants from DASHBOARD_LOGIN_N / DASHBOARD_PASSWORD_N."""
    settings = get_settings()
    seeds = settings.get_dashboard_seeds()

    for idx, seed in enumerate(seeds, start=1):
        email = seed["email"]
        password = seed["password"]

        if await _user_exists(email):
            continue

        # Derive tenant name from email domain
        domain = email.split("@")[1] if "@" in email else "tenant"
        tenant_name = f"{domain.split('.')[0].title()} Corp"

        async with async_session() as session:
            tenant = Tenant(
                name=tenant_name,
                api_key=f"sk-dashboard-{idx}-{uuid.uuid4()}",
            )
            session.add(tenant)
            await session.flush()

            # Default department
            dept = Department(
                tenant_id=tenant.id,
                name="General",
                description="Default department",
            )
            session.add(dept)
            await session.flush()

            # Admin user
            admin = User(
                tenant_id=tenant.id,
                email=email,
                password_hash=pwd_context.hash(password),
                full_name=email.split("@")[0].replace("_", " ").title(),
                is_tenant_admin=True,
                is_super_admin=False,
                is_active=True,
            )
            session.add(admin)
            await session.flush()

            # Assign admin to default department
            ud = UserDepartment(
                user_id=admin.id,
                department_id=dept.id,
                role="admin",
            )
            session.add(ud)
            await session.commit()
            logger.info(f"Seeded dashboard tenant {idx}: {tenant_name} (admin: {email})")


async def run_seed():
    """Run all seed operations."""
    await seed_super_admin()
    await seed_dashboard_tenants()
