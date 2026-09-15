"""Сборщики комментариев из соцсетей.

- DemoCollector — работает всегда, возвращает примеры (для демо и тестов).
- YouTubeCollector — настоящий, через YouTube Data API v3 (нужен API-ключ).
- TelegramChannelCollector — настоящий, через Telethon (нужны api_id/api_hash).
- VK — добавляется по аналогии через vk_api за один вечер.
"""
from __future__ import annotations

import os

from .models import Comment, Source

try:
    import httpx
except ImportError:
    httpx = None


class DemoCollector:
    source = Source.DEMO

    SAMPLES = [
        Comment(
            source=Source.DEMO, external_id="c1", author="user_ivan",
            text="Отличное видео! А можно подробнее про настройку на Windows?",
            url="https://example.com/post/1#c1",
            context="Видео-гайд по установке редактора кода",
        ),
        Comment(
            source=Source.DEMO, external_id="c2", author="maria_k",
            text="Не работает ссылка в описании, поправьте пожалуйста",
            url="https://example.com/post/1#c2",
            context="Видео-гайд по установке редактора кода",
        ),
        Comment(
            source=Source.DEMO, external_id="c3", author="old_sub",
            text="Смотрю вас с первого ролика, прогресс огромный 👏",
            url="https://example.com/post/2#c3",
            context="Итоги года канала",
        ),
    ]

    async def fetch(self) -> list[Comment]:
        return list(self.SAMPLES)


class YouTubeCollector:
    """Свежие комментарии к видео канала через официальный Data API."""

    API = "https://www.googleapis.com/youtube/v3/commentThreads"

    def __init__(self, api_key: str, channel_id: str, max_results: int = 20):
        self.api_key = api_key
        self.channel_id = channel_id
        self.max_results = max_results

    async def fetch(self) -> list[Comment]:
        assert httpx is not None, "pip install httpx"
        params = {
            "part": "snippet",
            "allThreadsRelatedToChannelId": self.channel_id,
            "order": "time",
            "maxResults": self.max_results,
            "key": self.api_key,
            "textFormat": "plainText",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.API, params=params)
            resp.raise_for_status()
        comments = []
        for it in resp.json().get("items", []):
            top = it["snippet"]["topLevelComment"]["snippet"]
            comments.append(Comment(
                source=Source.YOUTUBE,
                external_id=it["id"],
                author=top.get("authorDisplayName", "?"),
                text=top.get("textDisplay", ""),
                url=f"https://www.youtube.com/watch?v={top.get('videoId', '')}",
                context=it["snippet"].get("videoId", ""),
            ))
        return comments


class TelegramChannelCollector:
    """Комментарии из связанного чата TG-канала. Требует: pip install telethon."""

    def __init__(self, api_id: int, api_hash: str, channel: str, limit: int = 50):
        self.api_id = api_id
        self.api_hash = api_hash
        self.channel = channel
        self.limit = limit

    async def fetch(self) -> list[Comment]:
        from telethon import TelegramClient  # отложенный импорт

        comments: list[Comment] = []
        async with TelegramClient("agent_session", self.api_id, self.api_hash) as client:
            async for msg in client.iter_messages(self.channel, limit=self.limit):
                if msg.message:
                    comments.append(Comment(
                        source=Source.TELEGRAM,
                        external_id=str(msg.id),
                        author=str(msg.sender_id),
                        text=msg.message,
                        url=f"https://t.me/{self.channel}/{msg.id}",
                    ))
        return comments


def build_collectors() -> list:
    """Собирает список активных сборщиков по переменным окружения."""
    collectors: list = [DemoCollector()]
    yt_key = os.getenv("YOUTUBE_API_KEY", "")
    yt_channel = os.getenv("YOUTUBE_CHANNEL_ID", "")
    if yt_key and yt_channel:
        collectors.append(YouTubeCollector(yt_key, yt_channel))
    tg_id = os.getenv("TG_API_ID", "")
    tg_hash = os.getenv("TG_API_HASH", "")
    tg_channel = os.getenv("TG_CHANNEL", "")
    if tg_id and tg_hash and tg_channel:
        collectors.append(TelegramChannelCollector(int(tg_id), tg_hash, tg_channel))
    return collectors
