"""Seed a demo ticket that will trigger retrieval from the PAN-NET policy
chunks (unique content: list of 7 critical illnesses with 20.000 € cap).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

env = Path(__file__).parent / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import ai
import db


TICKET = dict(
    channel="Email",
    sender_name="Γεώργιος Χατζηκώστας",
    sender_email="g.chatzikostas@pan-net.eu",
    sender_phone="",
    subject="Κάλυψη κρίσιμων ασθενειών — PAN-NET GREECE",
    body=(
        "Καλημέρα σας,\n\n"
        "Εργάζομαι στην PAN-NET Greece ΕΠΕ και είμαι ασφαλισμένος στο ομαδικό "
        "πρόγραμμα του Ομίλου (συμβόλαιο DEUTSCHE TELEKOM PAN-NET GREECE). "
        "Πρόσφατα διαγνώστηκε στον πατέρα μου έμφραγμα του μυοκαρδίου και "
        "εξετάζεται το ενδεχόμενο εγχείρησης bypass.\n\n"
        "Θα ήθελα να γνωρίζω:\n\n"
        "1. Ποιο είναι το ανώτατο ποσό που καλύπτει το συμβόλαιο για κρίσιμες "
        "ασθένειες όπως έμφραγμα και εγχείρηση bypass;\n"
        "2. Σε ποια νοσοκομεία του δικτύου μπορεί να πραγματοποιηθεί η επέμβαση "
        "ώστε να έχουμε την καλύτερη κάλυψη (κατά προτίμηση στην Αθήνα);\n"
        "3. Ποια είναι η διαδικασία αναγγελίας του περιστατικού πριν τη νοσηλεία;\n\n"
        "Ευχαριστώ εκ των προτέρων,\n"
        "Γεώργιος"
    ),
)


def main() -> int:
    db.init_db()
    if not ai.is_configured():
        print("ERROR: GEMINI_API_KEY/GOOGLE_API_KEY not found.")
        return 1

    existing = {t["subject"] for t in db.list_tickets()}
    if TICKET["subject"] in existing:
        print(f"skip (dup): {TICKET['subject']}")
        return 0

    categories = db.list_categories()
    try:
        cat = ai.categorize_ticket(
            subject=TICKET["subject"],
            body=TICKET["body"],
            existing_categories=categories,
            recent_tickets=[dict(t) for t in db.recent_tickets(limit=10)],
        )
    except Exception as e:
        print(f"FAIL categorize: {e}")
        return 1

    if cat and cat.is_new_category and cat.category not in categories:
        db.add_category(cat.category)

    tid = db.create_ticket(
        channel=TICKET["channel"],
        sender_name=TICKET["sender_name"],
        sender_email=TICKET["sender_email"],
        sender_phone=TICKET["sender_phone"],
        subject=TICKET["subject"],
        body=TICKET["body"],
        category=cat.category if cat else None,
        ai_summary=cat.summary if cat else None,
        priority=cat.suggested_priority if cat else "Υψηλή",
    )
    print(f"+ #{tid}  [{cat.category if cat else '—'}]  {TICKET['subject']}")
    print(f"  Priority: {cat.suggested_priority if cat else '—'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
