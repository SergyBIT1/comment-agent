"""Генерация черновика ответа через OpenAI-совместимый API.

Работает с любым endpoint'ом /chat/completions: OpenAI, GigaChat-прокси,
YandexGPT-прокси, локальная Ollama и т.д. Без ключа включается встроенный
mock, чтобы демо запускалось вообще без внешних сервисов.
"""
from __future__ import annotations

import os

try:
    import httpx
except ImportError:  # демо-режим без httpx
    httpx = None

SYSTEM_PROMPT = (
    "Ты — ассистент автора контента. Напиши короткий (1-3 предложения), "
    "дружелюбный ответ на комментарий подписчика от имени автора. "
    "Без эмодзи-спама, без воды, по-русски. Учитывай контекст поста. "
    "Если подписчик сообщает о проблеме — поблагодари и пообещай исправить."
)


class MockLLM:
    """Заглушка для демо без API-ключей."""

    name = "mock"

    async def draft(self, comment_text: str, context: str = "") -> str:
        return (
            "Спасибо за обратную связь! Рад, что материал оказался полезным — "
            "учту ваше замечание в следующих публикациях."
        )


class OpenAICompatLLM:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.name = model

    async def draft(self, comment_text: str, context: str = "") -> str:
        assert httpx is not None, "pip install httpx"
        user = f"Контекст поста: {context}\n\nКомментарий подписчика: {comment_text}"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.name,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()


def build_llm():
    """Фабрика: есть ключ — настоящая модель, нет — mock для демо."""
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        return MockLLM()
    return OpenAICompatLLM(
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        api_key=api_key,
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    )
