from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class User(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    username: str
    password: str
    role: UserRole = UserRole.user

    class Config:
        orm_mode = True
