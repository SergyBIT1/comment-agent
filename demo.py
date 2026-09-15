"""Демо-прогон всего контура без Telegram и без LLM-ключей.

    python demo.py          — интерактив: вы автор, принимаете решения по карточкам
    python demo.py --auto   — автомат: первая карточка публикуется как есть,
                              вторая правится, третья пропускается
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

from agent.collectors import DemoCollector
from agent.core import collect_pending
from agent.models import Status
from agent.publisher import LogPublisher
from agent.storage import Storage

AUTO_SCRIPT = {"demo:c1": "p", "demo:c2": "e", "demo:c3": "s"}


async def main() -> None:
    auto = "--auto" in sys.argv
    db = Path(tempfile.gettempdir()) / "comment_agent_demo.db"
    db.unlink(missing_ok=True)
    storage = Storage(db)
    publisher = LogPublisher("out/published.log")

    decisions: dict[str, str] = {}

    async def on_new(comment, draft):
        print("\n" + "=" * 60)
        print(f"💬 {comment.source.value} · {comment.author}\n{comment.url}\n")
        print(f"«{comment.text}»\n")
        print(f"— Черновик LLM —\n{draft}\n")
        if auto:
            decisions[comment.uid] = AUTO_SCRIPT.get(comment.uid, "p")
            print(f"[auto] решение автора: {decisions[comment.uid]}")
        else:
            answer = input("[p]убликовать / [e] править / [s] пропустить: ").strip().lower()
            decisions[comment.uid] = (answer[:1] or "s")

    fresh = await collect_pending([DemoCollector()], storage, on_new=on_new)
    print(f"\nСобрано новых комментариев: {len(fresh)}")

    for comment in fresh:
        action = decisions.get(comment.uid, "s")
        if action == "e":
            final = "Спасибо! Ссылку поправил, проверьте."
            storage.set_status(comment.uid, Status.EDITED, final_text=final)
            print(f"✏️  {comment.uid}: применена правка автора -> «{final}»")
        elif action == "p":
            item = storage.get(comment.uid)
            await publisher.publish(comment.uid, item["draft"])
            storage.set_status(comment.uid, Status.PUBLISHED)
            print(f"✅ {comment.uid}: опубликовано (см. out/published.log)")
        else:
            storage.set_status(comment.uid, Status.SKIPPED)
            print(f"⏭  {comment.uid}: пропущено")

    print("\nПовторный проход (проверка защиты от дублей):")
    again = await collect_pending([DemoCollector()], storage)
    print(f"Новых на повторном проходе: {len(again)} (ожидается 0)")


if __name__ == "__main__":
    asyncio.run(main())
