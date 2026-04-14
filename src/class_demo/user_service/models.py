from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, List, Optional
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
    playlists: List[str] = Field(default_factory=list)
    liked_songs: List[str] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)
    spotify_id: Optional[str] = None
    spotify_refresh_token: Optional[str] = None
    spotify_display_name: Optional[str] = None
    spotify_token_expires_at: Optional[float] = None

model_config = {
        "from_attributes": True
    }