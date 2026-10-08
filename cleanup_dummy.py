"""Remove all placeholder/seed data from the DB so only real training data remains:
- 31 Excel Q&A (as both templates and KB entries)
- 36 policy KB entries from the PDFs
- 8 realistic demo tickets

Deletes:
- Seeded templates (ids 1-10)
- Seeded KB entries (those in the original CATEGORIES seed list, pre-Excel)
- Seeded tickets (subjects known to come from seed.py)

Idempotent.
"""
from __future__ import annotations

import sys

import db
from config import CATEGORIES as SEED_CATEGORIES

# Subjects that came from seed.py (handwritten, not real data)
SEED_TICKET_SUBJECTS = {
    "Ερώτηση για νοσοκομεία στο δίκτυο",
    "Αποζημίωση για μικροβιολογικές εξετάσεις",
    "Ένταξη νεογέννητου παιδιού",
    "Check-up 2026",
    "Πληρωμή αποζημίωσης",
    "Ρώτηση για νοσοκομεία δικτύου",
}


def main() -> int:
    db.init_db()

    # 1. Templates with id 1-10 are the original seed placeholders
    seed_template_ids = [t["id"] for t in db.list_templates() if t["id"] <= 10]
    for tid in seed_template_ids:
        db.delete_template(tid)
    print(f"Deleted {len(seed_template_ids)} seed templates (ids 1-10)")

    # 2. KB entries in seed CATEGORIES — these were the 11 handwritten seeds.
    #    Keep "Όροι συμβολαίου" (PDF) and all Excel-category entries (specific names).
    seed_cat_set = set(SEED_CATEGORIES)
    seed_kb = [e for e in db.list_kb_entries() if e["category"] in seed_cat_set]
    for e in seed_kb:
        db.delete_kb_entry(e["id"])
    print(f"Deleted {len(seed_kb)} seed KB entries")

    # 3. Seed tickets
    seed_tickets = [t for t in db.list_tickets() if t["subject"] in SEED_TICKET_SUBJECTS]
    for t in seed_tickets:
        db.delete_ticket(t["id"])
    print(f"Deleted {len(seed_tickets)} seed tickets")

    # Summary
    print()
    print(f"After cleanup:")
    print(f"  Templates: {len(db.list_templates())}  (should be 31 — Excel only)")
    kb = db.list_kb_entries()
    policy = [e for e in kb if e["category"] == "Όροι συμβολαίου"]
    print(f"  KB entries: {len(kb)}  ({len(policy)} policy + {len(kb)-len(policy)} Excel)")
    print(f"  Tickets:    {len(db.list_tickets())}  (should be 8 — all real)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
