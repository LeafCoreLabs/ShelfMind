"""Redis-backed chat session store with in-memory fallback."""

from __future__ import annotations

import json
import uuid
from typing import Any

import redis

from app.config import get_settings

SESSION_TTL = 1800  # 30 minutes
_memory: dict[str, str] = {}


def _redis_client() -> redis.Redis | None:
    try:
        settings = get_settings()
        client = redis.from_url(settings.redis_url, socket_connect_timeout=2, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def _key(store_id: int, user_id: int, session_id: str) -> str:
    return f"chat:{store_id}:{user_id}:{session_id}"


def new_session_id() -> str:
    return uuid.uuid4().hex[:16]


def load_session(store_id: int, user_id: int, session_id: str) -> dict[str, Any] | None:
    key = _key(store_id, user_id, session_id)
    client = _redis_client()
    raw: str | None
    if client:
        raw = client.get(key)
    else:
        raw = _memory.get(key)
    if not raw:
        return None
    return json.loads(raw)


def save_session(store_id: int, user_id: int, session_id: str, data: dict[str, Any]) -> None:
    key = _key(store_id, user_id, session_id)
    raw = json.dumps(data)
    client = _redis_client()
    if client:
        client.setex(key, SESSION_TTL, raw)
    else:
        _memory[key] = raw


def clear_session(store_id: int, user_id: int, session_id: str) -> None:
    key = _key(store_id, user_id, session_id)
    client = _redis_client()
    if client:
        client.delete(key)
    else:
        _memory.pop(key, None)


def default_session() -> dict[str, Any]:
    return {
        "pending_action": None,
        "slots": {},
        "agent_state": None,
        "missing": [],
        "history": [],
        "awaiting_confirm": False,
    }
