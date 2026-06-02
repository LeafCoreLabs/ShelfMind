from fastapi import APIRouter, Depends

from app.core.deps import require_admin
from app.services.system_health import collect_system_health

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/system-health")
async def system_health():
    return collect_system_health()
