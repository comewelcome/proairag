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

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        user_id: uuid.UUID, tenant_id: uuid.UUID, is_tenant_admin: bool = False, is_super_admin: bool = False
    ) -> str:
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "is_tenant_admin": is_tenant_admin,
            "is_super_admin": is_super_admin,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def decode_token(token: str) -> dict[str, Any] | None:
        try:
            settings = get_settings()
            return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
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
