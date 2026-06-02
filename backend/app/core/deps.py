from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.effective_jwt_secret, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = (await db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


async def require_store_owner(user: User = Depends(get_current_user)) -> User:
    if user.role != "user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Store owner access required")
    if not user.store_id:
        raise HTTPException(status_code=403, detail="No store linked to account")
    return user


async def get_owner_store_id(user: User = Depends(require_store_owner)) -> int:
    return user.store_id  # type: ignore[return-value]


async def require_user(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "user"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user


def resolve_store_id(user: User, store_id: int | None = None) -> int:
    if user.role == "admin":
        if store_id is None:
            raise HTTPException(status_code=400, detail="store_id required for admin")
        return store_id
    if not user.store_id:
        raise HTTPException(status_code=403, detail="No store linked to account")
    return user.store_id


async def get_store_id_param(
    user: User = Depends(require_user),
    store_id: int | None = Query(None),
) -> int:
    if user.role == "admin":
        return store_id or 1
    return resolve_store_id(user)
