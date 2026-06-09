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
