"""Promote the 31 Excel Q&As to response_templates so the auto-matcher
has concrete templates to pick for each real-world topic.

Also resets suggested_template_id on tickets where the stored suggestion is
clearly a fallback (so re-opening re-runs matching with the richer template
set). Idempotent: skips titles that already exist.

Run:  .venv/bin/python ingest_templates.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

import db

EXCEL = Path("/Users/lenatasia/Downloads/Use_Case_7_AI_Common_Issuesνεο_QA_FINAL_25.xlsx")


def main() -> int:
    db.init_db()
    df = pd.read_excel(EXCEL, sheet_name="AI Q&A").dropna(
        subset=["Ερώτηση", "Προτεινόμενη απάντηση Auto-Responder"]
    )

    existing_titles = {t["title"].strip() for t in db.list_templates()}
    added, skipped = 0, 0
    for _, row in df.iterrows():
        title = str(row["Ερώτηση"]).strip()
        content = str(row["Προτεινόμενη απάντηση Auto-Responder"]).strip()
        category = str(row["Κατηγορία / Common Issue"]).strip()
        if not title or not content:
            continue
        if title in existing_titles:
            skipped += 1
            continue
        db.create_template(title, category, content)
        added += 1

    print(f"Templates added: {added}  skipped(dup): {skipped}")
    print(f"Templates total: {len(db.list_templates())}")

    # Clear suggestion on tickets whose current suggestion is a non-Excel template
    # (ids 1-10 are the original seeded ones); re-opening will re-match against
    # the broader pool.
    cleared = 0
    for t in db.list_tickets():
        sid = t["suggested_template_id"] if "suggested_template_id" in t.keys() else None
        if sid and sid <= 10:
            db.update_ticket(t["id"], suggested_template_id=None)
            cleared += 1
    print(f"Tickets with cleared suggestion (will re-match on open): {cleared}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
