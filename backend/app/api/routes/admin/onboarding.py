import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.store import Product, Store, Transaction
from app.models.user import OnboardingDraft, User
from app.schemas.admin import OnboardingStepPayload
from app.services.forecast import run_all_forecasts

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/onboarding/start")
async def start_onboarding(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    draft = OnboardingDraft(admin_id=admin.id, step=1, payload={}, status="draft")
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return {"draft_id": draft.id, "step": draft.step}


@router.get("/onboarding/{draft_id}")
async def get_onboarding(draft_id: int, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    draft = (await db.execute(select(OnboardingDraft).where(OnboardingDraft.id == draft_id))).scalar_one_or_none()
    if not draft or draft.admin_id != admin.id:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"draft_id": draft.id, "step": draft.step, "payload": draft.payload, "status": draft.status}


@router.put("/onboarding/{draft_id}/step/{step_num}")
async def save_onboarding_step(
    draft_id: int,
    step_num: int,
    body: OnboardingStepPayload,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if step_num < 1 or step_num > 5:
        raise HTTPException(status_code=400, detail="Step must be 1-5")
    draft = (await db.execute(select(OnboardingDraft).where(OnboardingDraft.id == draft_id))).scalar_one_or_none()
    if not draft or draft.admin_id != admin.id or draft.status != "draft":
        raise HTTPException(status_code=404, detail="Draft not found")
    payload = dict(draft.payload or {})
    payload[f"step_{step_num}"] = body.data
    draft.payload = payload
    draft.step = max(draft.step, step_num + 1)
    await db.commit()
    return {"draft_id": draft.id, "step": draft.step, "saved": step_num}


@router.post("/onboarding/{draft_id}/complete")
async def complete_onboarding(
    draft_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    draft = (await db.execute(select(OnboardingDraft).where(OnboardingDraft.id == draft_id))).scalar_one_or_none()
    if not draft or draft.admin_id != admin.id or draft.status != "draft":
        raise HTTPException(status_code=404, detail="Draft not found")

    payload = draft.payload or {}
    s1 = payload.get("step_1", {})
    s2 = payload.get("step_2", {})
    s3 = payload.get("step_3", {})
    s5 = payload.get("step_5", {})

    email = s1.get("email")
    password = s1.get("password")
    full_name = s1.get("full_name")
    if not all([email, password, full_name]):
        raise HTTPException(status_code=400, detail="Step 1 account data incomplete")

    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    store = Store(
        name=s2.get("store_name", "New Store"),
        location=s3.get("location", "India"),
        lat=float(s3.get("lat", 19.0760)),
        lon=float(s3.get("lon", 72.8777)),
        salary_cycle_day=int(s3.get("salary_cycle_day", 1)),
        phone=s2.get("phone"),
        business_type=s2.get("business_type"),
        timezone=s3.get("timezone", "Asia/Kolkata"),
        preferences={
            "categories": s5.get("categories", []),
            "notification_email": s5.get("notification_email"),
            "forecast_horizon_days": s5.get("forecast_horizon_days", 7),
        },
    )
    db.add(store)
    await db.flush()

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role="user",
        store_id=store.id,
    )
    db.add(user)

    s4 = payload.get("step_4", {})
    csv_content = s4.get("csv_content")
    if csv_content:
        reader = csv.DictReader(io.StringIO(csv_content))
        for row in reader:
            sku = row.get("sku", "").strip()
            if not sku:
                continue
            product = Product(
                store_id=store.id,
                sku=sku,
                name=row.get("product_name", sku),
                category=row.get("category", "General"),
            )
            db.add(product)
            await db.flush()
            sold_at = datetime.fromisoformat(row["sold_at"].replace("Z", "+00:00"))
            db.add(
                Transaction(
                    store_id=store.id,
                    product_id=product.id,
                    quantity=int(row.get("quantity", 1)),
                    unit_price=float(row.get("unit_price", 0)),
                    sold_at=sold_at,
                )
            )

    draft.status = "completed"
    await db.commit()
    await db.refresh(user)
    await db.refresh(store)

    from app.db.session import SyncSessionLocal
    sync = SyncSessionLocal()
    try:
        run_all_forecasts(sync)
    finally:
        sync.close()

    return {"store_id": store.id, "user_id": user.id, "email": user.email}


@router.delete("/onboarding/{draft_id}")
async def discard_onboarding(
    draft_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    draft = (await db.execute(select(OnboardingDraft).where(OnboardingDraft.id == draft_id))).scalar_one_or_none()
    if not draft or draft.admin_id != admin.id:
        raise HTTPException(status_code=404, detail="Draft not found")
    await db.delete(draft)
    await db.commit()
    return {"discarded": True}
