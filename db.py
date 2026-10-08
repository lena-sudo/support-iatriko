import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    channel TEXT NOT NULL,
    sender_name TEXT,
    sender_email TEXT,
    sender_phone TEXT,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT,
    ai_summary TEXT,
    status TEXT NOT NULL DEFAULT 'Νέο',
    priority TEXT NOT NULL DEFAULT 'Κανονική',
    assignee TEXT,
    similar_ticket_ids TEXT
);

CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    author TEXT NOT NULL,
    content TEXT NOT NULL,
    was_ai_draft INTEGER NOT NULL DEFAULT 0,
    edited_from_draft INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS kb_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    is_seed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS response_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with conn() as c:
        c.executescript(SCHEMA)
        # Idempotent migrations for pre-existing dev DBs
        existing_cols = {row["name"] for row in c.execute("PRAGMA table_info(tickets)")}
        if "similar_ticket_ids" not in existing_cols:
            c.execute("ALTER TABLE tickets ADD COLUMN similar_ticket_ids TEXT")
        if "suggested_template_id" not in existing_cols:
            c.execute("ALTER TABLE tickets ADD COLUMN suggested_template_id INTEGER")
        resp_cols = {row["name"] for row in c.execute("PRAGMA table_info(responses)")}
        if "attachment_path" not in resp_cols:
            c.execute("ALTER TABLE responses ADD COLUMN attachment_path TEXT")
        if "attachment_name" not in resp_cols:
            c.execute("ALTER TABLE responses ADD COLUMN attachment_name TEXT")


def seed_categories(seed_names: list[str]) -> int:
    """Insert seed categories if the table is empty. Returns count inserted."""
    ts = now()
    inserted = 0
    with conn() as c:
        existing = c.execute("SELECT COUNT(*) AS n FROM categories").fetchone()["n"]
        if existing:
            return 0
        for name in seed_names:
            c.execute(
                "INSERT OR IGNORE INTO categories (name, is_seed, created_at) VALUES (?, 1, ?)",
                (name, ts),
            )
            inserted += 1
    return inserted


def list_categories() -> list[str]:
    with conn() as c:
        return [r["name"] for r in c.execute("SELECT name FROM categories ORDER BY is_seed DESC, name")]


def add_category(name: str) -> bool:
    """Add a new category. Returns True if newly inserted, False if already exists."""
    name = name.strip()
    if not name:
        return False
    with conn() as c:
        existing = c.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
        if existing:
            return False
        c.execute(
            "INSERT INTO categories (name, is_seed, created_at) VALUES (?, 0, ?)",
            (name, now()),
        )
        return True


# ---------- Response templates ----------

def list_templates(category: str | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM response_templates"
    args: list[Any] = []
    if category:
        sql += " WHERE category = ?"
        args.append(category)
    sql += " ORDER BY category, title"
    with conn() as c:
        return list(c.execute(sql, args))


def get_template(template_id: int) -> sqlite3.Row | None:
    with conn() as c:
        return c.execute(
            "SELECT * FROM response_templates WHERE id = ?", (template_id,)
        ).fetchone()


def create_template(title: str, category: str | None, content: str) -> int:
    ts = now()
    with conn() as c:
        cur = c.execute(
            "INSERT INTO response_templates (title, category, content, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, category, content, ts, ts),
        )
        return cur.lastrowid


def update_template(template_id: int, *, title: str, category: str | None, content: str) -> None:
    with conn() as c:
        c.execute(
            "UPDATE response_templates SET title = ?, category = ?, content = ?, updated_at = ? "
            "WHERE id = ?",
            (title, category, content, now(), template_id),
        )


def delete_template(template_id: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM response_templates WHERE id = ?", (template_id,))


def seed_templates_if_empty(items: list[dict]) -> int:
    """Insert seed templates only if table is empty. Returns count added."""
    with conn() as c:
        existing = c.execute("SELECT COUNT(*) AS n FROM response_templates").fetchone()["n"]
        if existing:
            return 0
    added = 0
    for it in items:
        create_template(it["title"], it.get("category"), it["content"])
        added += 1
    return added


def recent_tickets(limit: int = 30, exclude_id: int | None = None) -> list[sqlite3.Row]:
    """Recent tickets for similarity context (excluding one if provided)."""
    with conn() as c:
        if exclude_id is not None:
            return list(c.execute(
                "SELECT id, subject, body, category FROM tickets "
                "WHERE id != ? ORDER BY created_at DESC LIMIT ?",
                (exclude_id, limit),
            ))
        return list(c.execute(
            "SELECT id, subject, body, category FROM tickets "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ))


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_ticket(
    *,
    channel: str,
    sender_name: str,
    sender_email: str,
    sender_phone: str,
    subject: str,
    body: str,
    category: str | None = None,
    ai_summary: str | None = None,
    priority: str = "Κανονική",
    assignee: str | None = None,
) -> int:
    ts = now()
    with conn() as c:
        cur = c.execute(
            """
            INSERT INTO tickets (
                created_at, updated_at, channel, sender_name, sender_email,
                sender_phone, subject, body, category, ai_summary, status,
                priority, assignee
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Νέο', ?, ?)
            """,
            (
                ts, ts, channel, sender_name, sender_email, sender_phone,
                subject, body, category, ai_summary, priority, assignee,
            ),
        )
        return cur.lastrowid


def update_ticket(ticket_id: int, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = now()
    keys = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [ticket_id]
    with conn() as c:
        c.execute(f"UPDATE tickets SET {keys} WHERE id = ?", values)


def delete_ticket(ticket_id: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))


def list_tickets(
    *,
    status: str | None = None,
    category: str | None = None,
    assignee: str | None = None,
    search: str | None = None,
) -> list[sqlite3.Row]:
    sql = "SELECT * FROM tickets WHERE 1=1"
    args: list[Any] = []
    if status:
        sql += " AND status = ?"
        args.append(status)
    if category:
        sql += " AND category = ?"
        args.append(category)
    if assignee:
        sql += " AND assignee = ?"
        args.append(assignee)
    if search:
        sql += " AND (subject LIKE ? OR body LIKE ? OR sender_name LIKE ? OR sender_email LIKE ?)"
        pat = f"%{search}%"
        args.extend([pat, pat, pat, pat])
    sql += " ORDER BY (status = 'Έκλεισε') ASC, updated_at DESC"
    with conn() as c:
        return list(c.execute(sql, args))


def get_ticket(ticket_id: int) -> sqlite3.Row | None:
    with conn() as c:
        return c.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()


def add_response(
    ticket_id: int,
    *,
    author: str,
    content: str,
    was_ai_draft: bool = False,
    edited_from_draft: bool = False,
    attachment_path: str | None = None,
    attachment_name: str | None = None,
) -> int:
    with conn() as c:
        cur = c.execute(
            """
            INSERT INTO responses (
                ticket_id, created_at, author, content,
                was_ai_draft, edited_from_draft,
                attachment_path, attachment_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ticket_id, now(), author, content, int(was_ai_draft), int(edited_from_draft),
             attachment_path, attachment_name),
        )
        c.execute("UPDATE tickets SET updated_at = ? WHERE id = ?", (now(), ticket_id))
        return cur.lastrowid


def list_responses(ticket_id: int) -> list[sqlite3.Row]:
    with conn() as c:
        return list(
            c.execute(
                "SELECT * FROM responses WHERE ticket_id = ? ORDER BY created_at ASC",
                (ticket_id,),
            )
        )


def create_kb_entry(category: str, question: str, answer: str) -> int:
    ts = now()
    with conn() as c:
        cur = c.execute(
            "INSERT INTO kb_entries (category, question, answer, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (category, question, answer, ts, ts),
        )
        return cur.lastrowid


def update_kb_entry(entry_id: int, *, category: str, question: str, answer: str) -> None:
    with conn() as c:
        c.execute(
            "UPDATE kb_entries SET category = ?, question = ?, answer = ?, updated_at = ? WHERE id = ?",
            (category, question, answer, now(), entry_id),
        )


def delete_kb_entry(entry_id: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM kb_entries WHERE id = ?", (entry_id,))


def list_kb_entries(category: str | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM kb_entries"
    args: list[Any] = []
    if category:
        sql += " WHERE category = ?"
        args.append(category)
    sql += " ORDER BY category, question"
    with conn() as c:
        return list(c.execute(sql, args))


def stats() -> dict[str, Any]:
    with conn() as c:
        total = c.execute("SELECT COUNT(*) AS n FROM tickets").fetchone()["n"]
        by_status = list(
            c.execute("SELECT status, COUNT(*) AS n FROM tickets GROUP BY status")
        )
        by_category = list(
            c.execute(
                "SELECT COALESCE(category, 'Χωρίς κατηγορία') AS category, COUNT(*) AS n "
                "FROM tickets GROUP BY category ORDER BY n DESC"
            )
        )
        by_assignee = list(
            c.execute(
                "SELECT COALESCE(assignee, '— Χωρίς ανάθεση —') AS assignee, COUNT(*) AS n "
                "FROM tickets GROUP BY assignee ORDER BY n DESC"
            )
        )
        drafts = c.execute(
            "SELECT COUNT(*) AS n FROM responses WHERE was_ai_draft = 1"
        ).fetchone()["n"]
        edited = c.execute(
            "SELECT COUNT(*) AS n FROM responses WHERE edited_from_draft = 1"
        ).fetchone()["n"]
    return {
        "total": total,
        "by_status": by_status,
        "by_category": by_category,
        "by_assignee": by_assignee,
        "ai_drafts_used": drafts,
        "ai_drafts_edited": edited,
    }
