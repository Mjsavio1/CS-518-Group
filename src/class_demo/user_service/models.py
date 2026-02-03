from pydantic import BaseModel, EmailStr
from typing import Optional, Literal


class User(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    username: str
    password: str
    role: Literal["admin", "user"] = "user"

    class Config:
        orm_mode = True
