"""Хранение состояния в SQLite: защита от дублей и очередь решений автора."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Comment, Status

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    uid TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    author TEXT NOT NULL,
    text TEXT NOT NULL,
    url TEXT DEFAULT '',
    context TEXT DEFAULT '',
    draft TEXT DEFAULT '',
    final_text TEXT DEFAULT '',
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class Storage:
    def __init__(self, path: str | Path = "agent.db"):
        self.conn = sqlite3.connect(str(path))
        self.conn.executescript(SCHEMA)

    def is_known(self, uid: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM items WHERE uid = ?", (uid,))
        return cur.fetchone() is not None

    def add(self, comment: Comment, draft: str) -> None:
        self.conn.execute(
            """INSERT OR IGNORE INTO items
               (uid, source, external_id, author, text, url, context, draft, status, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))""",
            (
                comment.uid, comment.source.value, comment.external_id,
                comment.author, comment.text, comment.url, comment.context,
                draft, Status.PENDING.value,
            ),
        )
        self.conn.commit()

    def set_status(self, uid: str, status: Status, final_text: str | None = None) -> None:
        if final_text is not None:
            self.conn.execute(
                "UPDATE items SET status=?, final_text=?, updated_at=datetime('now') WHERE uid=?",
                (status.value, final_text, uid),
            )
        else:
            self.conn.execute(
                "UPDATE items SET status=?, updated_at=datetime('now') WHERE uid=?",
                (status.value, uid),
            )
        self.conn.commit()

    def get(self, uid: str) -> dict | None:
        cur = self.conn.execute("SELECT * FROM items WHERE uid=?", (uid,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [c[0] for c in cur.description]
        return dict(zip(cols, row))
