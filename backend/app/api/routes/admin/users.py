from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import UserCreate, UserUpdate
from app.schemas.auth import UserOut
from app.services.audit import log_audit

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    role: str | None = Query(None),
    store_id: int | None = Query(None),
    search: str | None = Query(None),
):
    q = select(User).order_by(User.created_at.desc())
    if role:
        q = q.where(User.role == role)
    if store_id:
        q = q.where(User.store_id == store_id)
    if search:
        q = q.where(User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%"))
    users = (await db.execute(q)).scalars().all()
    return {"users": [UserOut.model_validate(u) for u in users]}


@router.post("/users", response_model=UserOut)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        store_id=body.store_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await log_audit(db, actor.email, "create", "user", {"user_id": user.id, "email": user.email})
    return UserOut.model_validate(user)


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role
    if body.store_id is not None:
        user.store_id = body.store_id
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password:
        user.hashed_password = hash_password(body.password)
    await db.commit()
    await db.refresh(user)
    await log_audit(db, actor.email, "update", "user", {"user_id": user_id})
    return UserOut.model_validate(user)


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.commit()
    await log_audit(db, actor.email, "deactivate", "user", {"user_id": user_id})
    return {"deactivated": True, "user_id": user_id}
