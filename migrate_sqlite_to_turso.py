"""One-shot migration: copy local SQLite DB → Turso.

Reads data from data/tickets.db and writes it to the Turso DB specified by
TURSO_DATABASE_URL + TURSO_AUTH_TOKEN env vars.

Order of operations:
  1. Create schema on Turso (via db.init_db which runs the SCHEMA script)
  2. For each table, bulk copy rows preserving ids

Idempotent-ish: before copying, truncates target tables so a re-run gives a
clean mirror of local. Safe to run repeatedly during setup.

Run:
  TURSO_DATABASE_URL=libsql://... \\
  TURSO_AUTH_TOKEN=eyJ... \\
  .venv/bin/python migrate_sqlite_to_turso.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

TABLES_IN_ORDER = [
    "categories",
    "tickets",
    "responses",
    "kb_entries",
    "response_templates",
]


def main() -> int:
    url = os.getenv("TURSO_DATABASE_URL", "").strip()
    token = os.getenv("TURSO_AUTH_TOKEN", "").strip()
    if not (url and token):
        print("ERROR: set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN env vars first.")
        return 2

    sqlite_path = Path(__file__).parent / "data" / "tickets.db"
    if not sqlite_path.exists():
        print(f"ERROR: local DB not found at {sqlite_path}")
        return 2

    # Open local sqlite (read-only)
    src = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row

    # Open Turso via adapter — reuses the same code path as production
    from turso_adapter import TursoConnection
    dst = TursoConnection(url, token)

    # Ensure schema exists on remote
    import db as _db
    _old_url = os.environ.get("TURSO_DATABASE_URL", "")
    os.environ["TURSO_DATABASE_URL"] = url
    os.environ["TURSO_AUTH_TOKEN"] = token
    # Re-import flags evaluation
    _db.USE_TURSO = True
    _db.TURSO_URL = url
    _db.TURSO_TOKEN = token
    _db.init_db()
    print("✓ schema ensured on Turso")

    # Truncate target
    for t in TABLES_IN_ORDER:
        dst.execute(f"DELETE FROM {t}")
    print("✓ target tables cleared")

    # Copy row-by-row preserving ids
    total = 0
    for t in TABLES_IN_ORDER:
        rows = list(src.execute(f"SELECT * FROM {t}"))
        if not rows:
            print(f"  [{t}] 0 rows")
            continue
        cols = rows[0].keys()
        placeholders = ",".join(["?"] * len(cols))
        col_list = ",".join(cols)
        sql = f"INSERT INTO {t} ({col_list}) VALUES ({placeholders})"
        for r in rows:
            dst.execute(sql, tuple(r[c] for c in cols))
        print(f"  [{t}] {len(rows)} rows copied")
        total += len(rows)

    # Reset AUTOINCREMENT sequence counters if present
    try:
        src_seq = {r["name"]: r["seq"] for r in src.execute("SELECT name, seq FROM sqlite_sequence")}
        for name, seq in src_seq.items():
            # INSERT OR REPLACE into sqlite_sequence works on libsql too
            dst.execute(
                "INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES (?, ?)",
                (name, seq),
            )
        print(f"✓ sqlite_sequence synced ({len(src_seq)} tables)")
    except sqlite3.OperationalError:
        pass

    src.close()
    dst.close()
    print(f"\nTotal rows migrated: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
