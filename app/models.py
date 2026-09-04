"""Pydantic schemas for the TaskFlow demo API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Priority = Literal["low", "normal", "high"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    notes: str = Field(default="", max_length=2000)
    priority: Priority = "normal"


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=140)
    notes: str | None = Field(default=None, max_length=2000)
    priority: Priority | None = None
    done: bool | None = None


class TaskResponse(BaseModel):
    id: str
    title: str
    notes: str
    priority: Priority
    done: bool
    created_at: datetime


class TaskPage(BaseModel):
    items: list[TaskResponse]
    total: int
    limit: int
    offset: int
