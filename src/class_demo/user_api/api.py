"""FastAPI interface for the user_service.

Provides authentication endpoints and CRUD operations for users.  Internally
it obtains a :class:`~class_demo.user_service.service.UserService` instance
using a dependency so that tests can override or mock the service.

The API uses a very simple token-based scheme: clients POST their credentials
to ``/login`` and receive a random token.  That token must be presented on
subsequent requests in the ``Authorization: Bearer <token>`` header.  No
persistence is performed on the tokens; they are kept in-memory and therefore
lost when the process exits.

Exceptions raised by the service layer are translated into appropriate HTTP
status codes using a global exception handler.
"""

from typing import Any, Dict, List, Optional

import secrets
from fastapi import Depends, FastAPI, HTTPException, status, Header
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from ..user_service import service_exceptions as svc_exc
from ..user_service.service import UserService
from ..user_service.models import User, UserRole
from ..user_service import repository as repo_module
from ..config import Config
from pymongo import MongoClient

# --- application setup -----------------------------------------------------

app = FastAPI(title="User Service API")

# simple in-memory token map; tests may manipulate directly
_token_store: Dict[str, User] = {}
_security = HTTPBearer(auto_error=False)


# --- dependency helpers ----------------------------------------------------

def get_service() -> UserService:
    """Create a new UserService wired to the configured MongoDB.

    A fresh instance is returned each time so that there is no cross-request
    state.  Tests can override this dependency using ``app.dependency_overrides``.
    """
    client = MongoClient(Config.MONGODB_URI)
    db = client[Config.MONGODB_DB_NAME]
    repo = repo_module.UserRepository(db["users"])
    return UserService(repo)


def _token_from_header(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> User:
    """Dependency that returns the authenticated user or raises 401."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or malformed",
        )
    token = credentials.credentials
    user = _token_store.get(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user


def optional_current_user(
    authorization: Optional[str] = Header(None),
) -> Optional[User]:
    """Like ``get_current_user`` but returns ``None`` when no header is
    provided; used for endpoints (like registration) that permit anonymous
    access.
    """
    token = _token_from_header(authorization)
    if token is None:
        return None
    user = _token_store.get(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user


# --- pydantic schemas ------------------------------------------------------

class UserIn(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    username: str
    password: str
    role: Optional[UserRole] = None
    playlists: List[str] = Field(default_factory=list)
    liked_songs: List[str] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)


class UserOut(BaseModel):
    id: Optional[str]
    email: EmailStr
    username: str
    role: UserRole
    playlists: List[str] = Field(default_factory=list)
    liked_songs: List[str] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)


# --- exception handling ----------------------------------------------------

@app.exception_handler(svc_exc.UserServiceError)
async def service_exception_handler(request, exc: svc_exc.UserServiceError):
    """Translate service-layer errors into HTTP responses."""
    if isinstance(exc, svc_exc.UnauthorizedRequestError):
        code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, svc_exc.UserNotFoundError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, svc_exc.FailedAuthenticationError):
        code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, svc_exc.InvalidUserDataError):
        code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, (svc_exc.DuplicateEmailError, svc_exc.DuplicateUsernameError)):
        code = status.HTTP_409_CONFLICT
    elif isinstance(exc, svc_exc.RepositoryError):
        code = status.HTTP_500_INTERNAL_SERVER_ERROR
    else:
        # fallback for any other service error
        code = status.HTTP_400_BAD_REQUEST
    return JSONResponse(status_code=code, content={"detail": str(exc)})


# --- route handlers --------------------------------------------------------

@app.post("/login")
def login(
    credentials: Dict[str, str],
    service: UserService = Depends(get_service),
):
    username = credentials.get("username")
    password = credentials.get("password")
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password required",
        )
    try:
        user = service.authenticate(username, password)
    except svc_exc.UserServiceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    token = secrets.token_hex(16)
    _token_store[token] = user
    return {"token": token}


@app.post("/users", response_model=UserOut)
def create_user(
    user_in: UserIn,
    requester: Optional[User] = Depends(optional_current_user),
    service: UserService = Depends(get_service),
):
    # allow anonymous (requester=None) for self-registration
    data = user_in.dict(exclude_unset=True)
    created = service.create_user(requester, data)
    # drop password before returning
    return UserOut(**created.dict())


@app.get("/users", response_model=list[UserOut])
def list_users(
    current: User = Depends(get_current_user),
    service: UserService = Depends(get_service),
):
    users = service.list_users(current)
    return [UserOut(**u.dict()) for u in users]


@app.get("/users/{user_id}", response_model=UserOut)
def get_user(
    user_id: str,
    current: User = Depends(get_current_user),
    service: UserService = Depends(get_service),
):
    user = service.get_user(current, user_id)
    return UserOut(**user.dict())


@app.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    updates: Dict[str, Any],
    current: User = Depends(get_current_user),
    service: UserService = Depends(get_service),
):
    user = service.update_user(current, user_id, updates)
    return UserOut(**user.dict())


@app.delete("/users/{user_id}/spotify", status_code=status.HTTP_204_NO_CONTENT)
def revoke_spotify(
    user_id: str,
    current: User = Depends(get_current_user),
    service: UserService = Depends(get_service),
):
    # only the user or admin may revoke
    if current.role != UserRole.admin and current.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        # clear spotify fields
        updates = {
            "spotify_id": None,
            "spotify_refresh_token": None,
            "spotify_display_name": None,
            "spotify_token_expires_at": None,
        }
        user = service.update_user(current, user_id, updates)
    except svc_exc.UserServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return None


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    current: User = Depends(get_current_user),
    service: UserService = Depends(get_service),
):
    service.delete_user(current, user_id)
    return None


@app.get("/me", response_model=UserOut)
def get_me(
    current: User = Depends(get_current_user),
):
    return UserOut(**current.dict())
