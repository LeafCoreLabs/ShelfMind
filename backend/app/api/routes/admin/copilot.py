from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.services.admin_nl_query import process_admin_query

router = APIRouter(dependencies=[Depends(require_admin)])


class CopilotRequest(BaseModel):
    query: str


@router.post("/copilot/query")
async def admin_copilot(
    body: CopilotRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await process_admin_query(db, body.query)
    return {"user": user.email, **result}
