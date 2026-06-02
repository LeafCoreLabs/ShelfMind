import json
import re

from openai import OpenAI

from app.config import get_settings


def _strip_json_fences(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    return content.strip()


def chat_json(prompt: str, fallback: dict) -> dict:
    """Call Groq (OpenAI-compatible) and parse JSON response."""
    return chat_json_messages([{"role": "user", "content": prompt}], fallback)


def chat_json_messages(messages: list[dict[str, str]], fallback: dict) -> dict:
    """Call LLM with a message list and parse JSON response."""
    settings = get_settings()
    if not settings.llm_api_key:
        return fallback

    client_kwargs: dict = {"api_key": settings.llm_api_key}
    if settings.llm_base_url:
        client_kwargs["base_url"] = settings.llm_base_url

    client = OpenAI(**client_kwargs)
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = _strip_json_fences(response.choices[0].message.content or "{}")
        return json.loads(content)
    except Exception:
        return fallback
