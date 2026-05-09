"""M01 Pydantic schemas（design §7）。"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

UserRoleLiteral = Literal["platform_admin", "user"]
UserStatusLiteral = Literal["active", "disabled", "pending"]


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str
    role: UserRoleLiteral
    status: UserStatusLiteral
    avatar_url: str | None = None
    version: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserProfile


class RefreshRequest(BaseModel):
    # Phase 2.2 子片 2: cookie 优先 / body 兜底（ADR-004 P3 字面合规）
    # None 表示走 cookie 通道；空字符串仍 422（保 1619 baseline）
    refresh_token: str | None = Field(default=None, min_length=1)


class RefreshResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class LogoutResponse(BaseModel):
    status: Literal["ok"] = "ok"


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int
    name: str | None = Field(None, min_length=1, max_length=255)
    old_password: str | None = None
    new_password: str | None = Field(None, min_length=8, max_length=128)


class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRoleLiteral = "user"


class CreateUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str
    role: UserRoleLiteral


class UpdateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int
    role: UserRoleLiteral | None = None
    status: UserStatusLiteral | None = None


class UserListItem(UserProfile):
    created_at: datetime


class UserListResponse(BaseModel):
    users: list[UserListItem]
    total: int
