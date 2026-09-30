from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.base import Base


class Company(Base):
    __tablename__ = "companies"

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_companies_status",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_companies_name_not_blank",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(20),
        server_default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
