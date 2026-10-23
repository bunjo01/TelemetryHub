from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.base import Base


class Device(Base):
    __tablename__ = "devices"

    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_devices_name_not_blank",
        ),
        CheckConstraint(
            "description IS NULL OR length(description) <= 1000",
            name="ck_devices_description_length",
        ),
        CheckConstraint(
            "device_type IN "
            "('temperature_sensor', 'environment_sensor', 'gps_tracker')",
            name="ck_devices_device_type",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_devices_status",
        ),
        Index("ix_devices_company_id", "company_id"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "companies.id",
            name="fk_devices_company_id_companies",
            ondelete="RESTRICT",
        ),
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    device_type: Mapped[str] = mapped_column(Text)
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
