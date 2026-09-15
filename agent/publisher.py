"""Публикация подтверждённого ответа обратно в соцсеть.

- LogPublisher — пишет в файл (демо/тесты).
- TelegramPublisher — отвечает на сообщение в TG (рабочий, через Bot API).
- YouTubePublisher — каркас под YouTube comments.insert (нужен OAuth заказчика).
"""
from __future__ import annotations

import json
from pathlib import Path


class LogPublisher:
    def __init__(self, path: str | Path = "out/published.log"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def publish(self, uid: str, text: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"uid": uid, "text": text}, ensure_ascii=False) + "\n")


class TelegramPublisher:
    def __init__(self, bot, default_chat_id: int):
        self.bot = bot
        self.default_chat_id = default_chat_id

    async def publish(self, uid: str, text: str) -> None:
        # uid вида telegram:<message_id>; в бою chat_id нужно хранить вместе с uid
        msg_id = int(uid.split(":", 1)[1])
        await self.bot.send_message(self.default_chat_id, text, reply_to_message_id=msg_id)


class YouTubePublisher:
    def __init__(self, oauth_token: str = ""):
        self.oauth_token = oauth_token

    async def publish(self, uid: str, text: str) -> None:
        # youtube.comments.insert(parentId=..., snippet.textOriginal=...)
        # Требуется OAuth-аккаунт канала; подключается после выдачи ключей заказчиком
        raise NotImplementedError("YouTube-публикация подключается после OAuth заказчика")
