"""Remove the 12 generic seed categories so only real-data categories remain:
- 31 from Excel
- 1 "Όροι συμβολαίου" from PDFs

Also reassigns any ticket currently in a seed category to the closest real one.
"""
from __future__ import annotations

import sqlite3
import sys

import db
from config import CATEGORIES as SEED_CATEGORIES, DB_PATH

# Where to redirect tickets stuck in seed categories (best-fit mapping)
REASSIGN = {
    "Κάλυψη νοσηλείας": "Επίδομα Μητρότητας",  # ticket #8 is about καισαρική
}


def main() -> int:
    db.init_db()

    # 1. Reassign tickets that use seed categories
    reassigned = 0
    for t in db.list_tickets():
        if t["category"] in SEED_CATEGORIES:
            new_cat = REASSIGN.get(t["category"]) or "Άλλο"
            if new_cat not in db.list_categories():
                # fallback: pick first Excel category — practically shouldn't happen
                new_cat = next(
                    (c for c in db.list_categories() if c not in SEED_CATEGORIES),
                    None,
                )
            if new_cat:
                db.update_ticket(t["id"], category=new_cat)
                print(f"ticket #{t['id']}: '{t['category']}' → '{new_cat}'")
                reassigned += 1
    print(f"\nReassigned tickets: {reassigned}")

    # 2. Delete seed categories from the categories table
    deleted = 0
    with sqlite3.connect(DB_PATH) as c:
        for name in SEED_CATEGORIES:
            cur = c.execute("DELETE FROM categories WHERE name = ?", (name,))
            if cur.rowcount:
                deleted += 1
        c.commit()
    print(f"Deleted seed categories: {deleted}")

    print(f"\nΚατηγορίες πλέον: {len(db.list_categories())}  (όλες από Excel + PDFs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
