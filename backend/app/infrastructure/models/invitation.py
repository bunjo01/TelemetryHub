from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.base import Base


class Invitation(Base):
    __tablename__ = "invitations"

    __table_args__ = (
        UniqueConstraint(
            "token_hash",
            name="uq_invitations_token_hash",
        ),
        CheckConstraint(
            "email = lower(trim(email)) AND length(email) > 0",
            name="ck_invitations_email_normalized",
        ),
        CheckConstraint(
            "role IN ('company_owner', 'member')",
            name="ck_invitations_role",
        ),
        CheckConstraint(
            "token_hash ~ '^[0-9a-f]{64}$'",
            name="ck_invitations_token_hash_format",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_invitations_expiration",
        ),
        CheckConstraint(
            "accepted_at IS NULL OR "
            "(accepted_at >= created_at AND accepted_at < expires_at)",
            name="ck_invitations_acceptance_time",
        ),
        Index("ix_invitations_company_id", "company_id"),
        Index("ix_invitations_invited_by_id", "invited_by_id"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "companies.id",
            name="fk_invitations_company_id_companies",
            ondelete="RESTRICT",
        ),
    )
    invited_by_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_invitations_invited_by_id_users",
            ondelete="RESTRICT",
        ),
    )
    email: Mapped[str] = mapped_column(String(254))
    role: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
