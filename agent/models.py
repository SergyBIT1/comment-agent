"""Базовые модели данных агента."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Source(str, Enum):
    YOUTUBE = "youtube"
    TELEGRAM = "telegram"
    VK = "vk"
    DEMO = "demo"


class Status(str, Enum):
    NEW = "new"                # собран, ждёт генерации
    PENDING = "pending"        # черновик отправлен автору на решение
    APPROVED = "approved"      # автор подтвердил как есть
    EDITED = "edited"          # автор прислал свою правку
    SKIPPED = "skipped"        # автор решил не отвечать
    PUBLISHED = "published"    # ответ ушёл в соцсеть
    FAILED = "failed"          # ошибка публикации


@dataclass
class Comment:
    source: Source
    external_id: str           # id комментария в исходной соцсети
    author: str
    text: str
    url: str = ""
    context: str = ""          # текст поста/видео, к которому оставлен комментарий
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def uid(self) -> str:
        return f"{self.source.value}:{self.external_id}"
