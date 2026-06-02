from fastapi import APIRouter

from app.api.routes import auth, health
from app.api.routes.admin import router as admin_router
from app.api.routes.store import router as store_router

router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(store_router, prefix="/store", tags=["store"])
router.include_router(admin_router, prefix="/admin", tags=["admin"])
