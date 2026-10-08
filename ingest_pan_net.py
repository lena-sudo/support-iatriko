"""Ingest the DEUTSCHE TELEKOM PAN-NET GREECE policy as a third contract.

Chunks the PDF by section headings and stores each chunk under category
"Όροι συμβολαίου" (shared with the other two policies), with question prefix
"[Συμβόλαιο PAN-NET GREECE] <heading>" so the AI can tell which contract a
section belongs to.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pdfplumber

import db
from ingest import chunk_policy, POLICY_CATEGORY

PDF = Path("/Users/lenatasia/Downloads/DEUTSCHE_TELEKOM_PAN-NET_GREECE__3 (1).pdf")
LABEL = "[Συμβόλαιο PAN-NET GREECE]"


def extract_pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join((pg.extract_text() or "") for pg in pdf.pages)


def main() -> int:
    db.init_db()
    if not PDF.exists():
        print(f"ERROR: δεν βρέθηκε το αρχείο {PDF}")
        return 1

    text = extract_pdf_text(PDF)
    chunks = chunk_policy(text)

    existing = {e["question"].strip() for e in db.list_kb_entries()}
    if POLICY_CATEGORY not in db.list_categories():
        db.add_category(POLICY_CATEGORY)

    added, skipped = 0, 0
    for heading, body in chunks:
        q = f"{LABEL} {heading}"
        if q in existing:
            skipped += 1
            continue
        db.create_kb_entry(POLICY_CATEGORY, q, body)
        added += 1

    print(f"PAN-NET chunks added: {added}  skipped(dup): {skipped}")
    print(f"Total KB entries: {len(db.list_kb_entries())}")
    print(f"Policy entries total: "
          f"{sum(1 for e in db.list_kb_entries() if e['category'] == POLICY_CATEGORY)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
