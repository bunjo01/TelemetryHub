from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums.device_types import DeviceType


class CreateDeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    device_type: DeviceType
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class DeviceResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    description: str | None
    device_type: DeviceType
    status: Literal["active", "inactive"]
    created_at: datetime
    updated_at: datetime


class DeviceListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["active", "inactive", "all"] = "active"
    search: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("search", mode="before")
    @classmethod
    def normalize_search(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class DeviceListResponse(BaseModel):
    items: list[DeviceResponse]
    limit: int
    offset: int
    has_more: bool
