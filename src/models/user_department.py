import uuid
from sqlalchemy import String, ForeignKey
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
