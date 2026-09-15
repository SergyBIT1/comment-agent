"""Ядро: собрать -> сгенерировать черновик -> отдать автору на решение."""
from __future__ import annotations

from .llm import build_llm
from .models import Comment
from .storage import Storage


async def collect_pending(collectors, storage: Storage, llm=None, on_new=None) -> list[Comment]:
    """Один проход цикла сбора.

    on_new(comment, draft) — async-колбэк, доставляющий карточку автору
    (Telegram-бот, консоль в демо и т.п.).
    """
    llm = llm or build_llm()
    fresh: list[Comment] = []
    for collector in collectors:
        try:
            batch = await collector.fetch()
        except Exception as exc:  # упавший источник не роняет весь цикл
            print(f"[{type(collector).__name__}] ошибка сбора: {exc}")
            continue
        for comment in batch:
            if storage.is_known(comment.uid):
                continue
            draft = await llm.draft(comment.text, comment.context)
            storage.add(comment, draft)
            fresh.append(comment)
            if on_new is not None:
                await on_new(comment, draft)
    return fresh
