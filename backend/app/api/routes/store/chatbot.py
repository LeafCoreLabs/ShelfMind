"""Store chat API — delegates to multi-turn chat agent."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owner_store_id, require_store_owner
from app.db.session import get_db
from app.models.user import User
from app.services.chat_agent import handle_message, to_dict

router = APIRouter(dependencies=[Depends(require_store_owner)])


class ChatMessage(BaseModel):
    message: str
    session_id: str | None = None
    fresh: bool = False


class ChatResponse(BaseModel):
    reply: str
    intent: str
    session_id: str
    status: str = "complete"
    missing: list[str] | None = None
    suggestions: list[dict] | None = None
    result: dict | None = None
    data: dict | None = None
    actions: list[dict] | None = None


@router.post("/chat")
async def chat(
    body: ChatMessage,
    db: AsyncSession = Depends(get_db),
    store_id: int = Depends(get_owner_store_id),
    user: User = Depends(require_store_owner),
) -> ChatResponse:
    resp = await handle_message(db, store_id, user.id, body.message, body.session_id, body.fresh)
    return ChatResponse(**to_dict(resp))
