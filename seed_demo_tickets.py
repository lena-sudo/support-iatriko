"""Seed 8 realistic demo tickets drawn from the actual training data
(Excel Q&A + policy coverage). Each ticket is categorized live by Gemini
so the dashboard reflects true AI output, not hand-written labels.

Idempotent on subject: skips if subject already exists.
Run:  .venv/bin/python seed_demo_tickets.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Load .env so GOOGLE_API_KEY is available
env = Path(__file__).parent / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import ai
import db
from config import CHANNELS

DEMOS = [
    dict(
        channel="Email",
        sender_name="Μαρία Κουτσούκου",
        sender_email="m.koutsoukou@ote.gr",
        sender_phone="",
        subject="Κάλυψη καισαρικής τομής",
        body=(
            "Καλησπέρα σας,\n\n"
            "Είμαι ασφαλισμένη στο ομαδικό πρόγραμμα Υγείας του Ομίλου ΟΤΕ και αναμένω "
            "τη γέννηση του πρώτου μου παιδιού τον Ιανουάριο. Οι γιατροί συνιστούν "
            "καισαρική τομή. Μπορείτε να μου πείτε ποιο είναι το ανώτατο ποσό που "
            "καλύπτει το συμβόλαιο για καισαρική;\n\n"
            "Ευχαριστώ,\nΜαρία"
        ),
    ),
    dict(
        channel="Email",
        sender_name="Αλέξανδρος Παπαδημητρίου",
        sender_email="a.papadimitriou@ote.gr",
        sender_phone="",
        subject="Υπενθύμιση για το αίτημα αποζημίωσης",
        body=(
            "Καλημέρα,\n\n"
            "Ευγενική υπενθύμιση για το αίτημά μου που είχα υποβάλει πριν 3 εβδομάδες "
            "για την αποζημίωση εξετάσεων. Δεν έχω λάβει καμία ενημέρωση ακόμη. "
            "Μπορείτε να ελέγξετε πού βρίσκεται;\n\n"
            "Ευχαριστώ,\nΑλέξανδρος"
        ),
    ),
    dict(
        channel="Τηλέφωνο",
        sender_name="Σοφία Μητροπούλου",
        sender_email="s.mitropoulou@ote.gr",
        sender_phone="6944123456",
        subject="Παλαιότερες αποδείξεις φυσικοθεραπειών",
        body=(
            "Έχω αποδείξεις από φυσικοθεραπείες που έκανα τον Αύγουστο αλλά τις ξέχασα "
            "να τις υποβάλω. Μπορώ ακόμα να τις στείλω για αποζημίωση ή έχει περάσει "
            "η προθεσμία;"
        ),
    ),
    dict(
        channel="Email",
        sender_name="Δημήτρης Λαζαρίδης",
        sender_email="d.lazaridis@ote.gr",
        sender_phone="",
        subject="Αλλαγή δικαιούχου στο ομαδικό",
        body=(
            "Καλησπέρα,\n\n"
            "Παντρεύτηκα πρόσφατα και θέλω να αλλάξω τον δικαιούχο του ομαδικού "
            "από τους γονείς μου στη σύζυγό μου. Ποια είναι η διαδικασία και τι "
            "δικαιολογητικά χρειάζονται;\n\n"
            "Ευχαριστώ"
        ),
    ),
    dict(
        channel="Email",
        sender_name="Ελευθερία Νικολαΐδου",
        sender_email="e.nikolaidou@ote.gr",
        sender_phone="",
        subject="Προγραμματισμένο χειρουργείο — ποια βήματα;",
        body=(
            "Έχω προγραμματίσει χειρουργείο για αρθροσκόπηση γονάτου στις 20 του μήνα. "
            "Μπορείτε να μου εξηγήσετε τι πρέπει να κάνω πριν τη νοσηλεία ώστε να "
            "ενεργοποιηθεί η κάλυψη του ομαδικού και να μη χρειαστεί να πληρώσω εγώ "
            "αρχικά;"
        ),
    ),
    dict(
        channel="Email",
        sender_name="Νίκος Σταυρουλάκης",
        sender_email="n.stavroulakis@ote.gr",
        sender_phone="",
        subject="Απώλεια εισοδήματος μετά από ατύχημα",
        body=(
            "Είχα ένα τροχαίο την προηγούμενη εβδομάδα και ο γιατρός μου έδωσε "
            "αναρρωτική 6 εβδομάδων. Δικαιούμαι κάτι από το ομαδικό για την απώλεια "
            "εισοδήματος αυτής της περιόδου; Τι δικαιολογητικά χρειάζονται;"
        ),
    ),
    dict(
        channel="Teams",
        sender_name="Κατερίνα Αγγελοπούλου",
        sender_email="k.aggelopoulou@ote.gr",
        sender_phone="",
        subject="Οδοντιατρική κάλυψη",
        body=(
            "Χρειάζομαι μια θεραπεία για ρίζα δοντιού. Καλύπτει κάτι το ομαδικό "
            "υγείας για οδοντιατρικές εργασίες; Τι δικαιολογητικά να στείλω αρχικά;"
        ),
    ),
    dict(
        channel="Email",
        sender_name="Παναγιώτης Ρίζος",
        sender_email="p.rizos@ote.gr",
        sender_phone="",
        subject="Σχόλια διακανονιστή — πού τα βλέπω;",
        body=(
            "Μου είπατε ότι ο διακανονιστής άφησε σχόλιο στο αίτημά μου αλλά δεν "
            "ξέρω πού να το δω. Μπορείτε να μου εξηγήσετε;"
        ),
    ),
]


def main() -> int:
    db.init_db()
    if not ai.is_configured():
        print("ERROR: GEMINI_API_KEY/GOOGLE_API_KEY δεν βρέθηκε στο env.")
        return 1

    existing_subjects = {t["subject"] for t in db.list_tickets()}
    categories = db.list_categories()

    added, skipped, failed = 0, 0, 0
    for d in DEMOS:
        if d["subject"] in existing_subjects:
            print(f"skip (dup): {d['subject']}")
            skipped += 1
            continue

        # Live categorization against the ingested KB
        try:
            cat = ai.categorize_ticket(
                subject=d["subject"],
                body=d["body"],
                existing_categories=categories,
                recent_tickets=[dict(t) for t in db.recent_tickets(limit=10)],
            )
        except Exception as e:
            print(f"FAIL categorize {d['subject']!r}: {e}")
            failed += 1
            continue

        if cat and cat.is_new_category and cat.category not in categories:
            db.add_category(cat.category)
            categories.append(cat.category)

        tid = db.create_ticket(
            channel=d["channel"],
            sender_name=d["sender_name"],
            sender_email=d["sender_email"],
            sender_phone=d["sender_phone"],
            subject=d["subject"],
            body=d["body"],
            category=cat.category if cat else None,
            ai_summary=cat.summary if cat else None,
            priority=cat.suggested_priority if cat else "Κανονική",
        )
        print(f"+ #{tid}  [{cat.category if cat else '—'}]  {d['subject']}")
        added += 1

    print(f"\nDone. added={added}  skipped={skipped}  failed={failed}")
    print(f"Total tickets: {len(db.list_tickets())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
