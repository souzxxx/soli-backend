from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import RoleEnum


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: RoleEnum = RoleEnum.OPERATOR


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None = None
    role: RoleEnum
    created_at: datetime
