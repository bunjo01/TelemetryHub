from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.base import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint(
            "email = lower(trim(email)) AND length(email) > 0",
            name="ck_users_email_normalized",
        ),
        CheckConstraint(
            "role IN ('system_admin', 'company_owner', 'member')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "(role = 'system_admin' AND company_id IS NULL) OR "
            "(role IN ('company_owner', 'member') AND company_id IS NOT NULL)",
            name="ck_users_role_company",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_users_status",
        ),
        CheckConstraint(
            "length(trim(password_hash)) > 0",
            name="ck_users_password_hash_not_blank",
        ),
        Index("ix_users_company_id", "company_id"),
        Index(
            "uq_users_company_owner",
            "company_id",
            unique=True,
            postgresql_where=text("role = 'company_owner'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    company_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "companies.id",
            name="fk_users_company_id_companies",
            ondelete="RESTRICT",
        ),
    )
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))
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
