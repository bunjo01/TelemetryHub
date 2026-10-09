from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class CreateInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_input(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()


class OwnerInvitationResponse(BaseModel):
    id: UUID
    company_id: UUID
    email: str
    role: Literal["company_owner"] = "company_owner"
    expires_at: datetime
    token: str = Field(repr=False)


class AcceptInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: SecretStr = Field(min_length=43, max_length=43)
    password: SecretStr = Field(min_length=15, max_length=128)


class MemberInvitationResponse(BaseModel):
    id: UUID
    company_id: UUID
    email: str
    role: Literal["member"] = "member"
    expires_at: datetime
    token: str = Field(repr=False)


class PreviewInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: SecretStr = Field(min_length=43, max_length=43)


class PreviewInvitationResponse(BaseModel):
    email: str
    expires_at: datetime
