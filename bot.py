"""Telegram-интерфейс автора: карточки с кнопками решений.

Каждый новый комментарий приходит автору карточкой:
  [✅ Опубликовать] [✏️ Править] [⏭ Пропустить]
"""
from __future__ import annotations

import asyncio
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from agent.collectors import build_collectors
from agent.core import collect_pending
from agent.llm import build_llm
from agent.models import Comment, Status
from agent.publisher import LogPublisher
from agent.storage import Storage

router = Router()
storage = Storage(os.getenv("AGENT_DB", "agent.db"))
publisher = LogPublisher()
OWNER_ID = int(os.getenv("OWNER_CHAT_ID", "0"))


class EditFlow(StatesGroup):
    waiting_text = State()


def card_kb(uid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"pub:{uid}"),
        InlineKeyboardButton(text="✏️ Править", callback_data=f"edit:{uid}"),
        InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip:{uid}"),
    ]])


def card_text(comment: Comment, draft: str) -> str:
    return (
        f"💬 {comment.source.value} · {comment.author}\n"
        f"{comment.url}\n\n"
        f"«{comment.text}»\n\n"
        f"— Черновик ответа —\n{draft}"
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Агент комментариев запущен. Новые комментарии из соцсетей "
        "будут приходить сюда карточками с черновиком ответа."
    )


@router.callback_query(F.data.startswith("pub:"))
async def approve(cb: CallbackQuery) -> None:
    uid = cb.data[4:]
    item = storage.get(uid) or {}
    text = item.get("final_text") or item.get("draft") or ""
    try:
        await publisher.publish(uid, text)
    except Exception as exc:
        storage.set_status(uid, Status.FAILED)
        await cb.answer(f"Ошибка публикации: {exc}", show_alert=True)
        return
    storage.set_status(uid, Status.PUBLISHED)
    await cb.message.edit_text(cb.message.text + "\n\n✅ Опубликовано")
    await cb.answer()


@router.callback_query(F.data.startswith("skip:"))
async def skip(cb: CallbackQuery) -> None:
    uid = cb.data[5:]
    storage.set_status(uid, Status.SKIPPED)
    await cb.message.edit_text(cb.message.text + "\n\n⏭ Пропущено")
    await cb.answer()


@router.callback_query(F.data.startswith("edit:"))
async def edit_begin(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(EditFlow.waiting_text)
    await state.update_data(uid=cb.data[5:])
    await cb.message.answer("Пришлите исправленный текст ответа одним сообщением.")
    await cb.answer()


@router.message(EditFlow.waiting_text)
async def edit_apply(message: Message, state: FSMContext) -> None:
    uid = (await state.get_data())["uid"]
    storage.set_status(uid, Status.EDITED, final_text=message.text)
    await state.clear()
    await message.answer("Правка сохранена. Теперь можно публиковать:", reply_markup=card_kb(uid))


async def polling_loop(bot: Bot) -> None:
    collectors = build_collectors()
    llm = build_llm()

    async def on_new(comment: Comment, draft: str) -> None:
        await bot.send_message(OWNER_ID, card_text(comment, draft), reply_markup=card_kb(comment.uid))

    while True:
        await collect_pending(collectors, storage, llm, on_new=on_new)
        await asyncio.sleep(int(os.getenv("POLL_INTERVAL", "300")))


async def main() -> None:
    bot = Bot(os.environ["TG_BOT_TOKEN"])
    dp = Dispatcher()
    dp.include_router(router)
    asyncio.create_task(polling_loop(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
