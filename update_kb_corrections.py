"""Business-rule corrections to KB and templates:

1. Dental: ΜΟΝΟ σε περίπτωση ατυχήματος. Υπάρχουσα entry/template διορθώνεται,
   και προστίθεται ξεχωριστή για "οδοντιατρικό εκτός ατυχήματος".
2. Receipt submission deadline: εντός 6μηνου στην πλατφόρμα, μετά με φάκελο.
"""
from __future__ import annotations

import sys

import db


DENTAL_CORRECTED_ANSWER = (
    "Το ομαδικό πρόγραμμα Υγείας **καλύπτει οδοντιατρικές εργασίες μόνο σε "
    "περίπτωση ατυχήματος** (π.χ. τραυματισμός δοντιού σε τροχαίο, πτώση κλπ). "
    "Συνήθεις/προγραμματισμένες οδοντιατρικές θεραπείες (ρίζα, εμφυτεύματα, "
    "σφραγίσματα, καθαρισμός, ορθοδοντικά κ.ά.) δεν καλύπτονται από το συμβόλαιο.\n\n"
    "Για αξιολόγηση περιστατικού ΑΤΥΧΗΜΑΤΟΣ, παρακαλούμε αποστείλετε:\n\n"
    "• Αναλυτική περιγραφή του ατυχήματος και της ζημιάς\n"
    "• Ιατρική γνωμάτευση του θεράποντος οδοντιάτρου\n"
    "• Φωτογραφίες ή/και σχετικές εξετάσεις/απεικονίσεις\n"
    "• Αναλυτικά τις απαιτούμενες οδοντιατρικές εργασίες και το κόστος τους\n\n"
    "Η Εθνική Ασφαλιστική δύναται να ζητήσει επιπλέον δικαιολογητικά για την "
    "ολοκληρωμένη αξιολόγηση του περιστατικού."
)


DENTAL_NON_ACCIDENT_ANSWER = (
    "Σας ευχαριστούμε για την επικοινωνία.\n\n"
    "Το ομαδικό πρόγραμμα Υγείας του Ομίλου ΟΤΕ **δεν καλύπτει** προγραμματισμένες "
    "οδοντιατρικές εργασίες όπως ρίζα δοντιού, εμφυτεύματα, σφραγίσματα, "
    "ορθοδοντικά, καθαρισμός ή άλλες τακτικές θεραπείες.\n\n"
    "**Καλύπτονται μόνο οδοντιατρικές εργασίες που αφορούν ατύχημα** (τραυματισμός "
    "κατά τη διάρκεια που ισχύει η ασφάλιση). Εφόσον η περίπτωσή σας αφορά "
    "ατύχημα, παρακαλούμε αποστείλετε αναλυτική περιγραφή, ιατρική γνωμάτευση και "
    "φωτογραφίες ώστε να αξιολογηθεί.\n\n"
    "Στη διάθεσή μας για οποιαδήποτε διευκρίνιση,\n\n"
    "Τμήμα Υποστήριξης Ομαδικού Υγείας"
)


RECEIPT_DEADLINE_ANSWER = (
    "Η προθεσμία υποβολής αποδείξεων και παραστατικών μέσω της πλατφόρμας είναι "
    "**εντός 6 μηνών (180 ημερών)** από την ημερομηνία έκδοσης της απόδειξης.\n\n"
    "Εφόσον η προθεσμία έχει παρέλθει, μπορείτε να μας αποστείλετε τα "
    "δικαιολογητικά **με φάκελο** (έντυπα, συστημένο ή με courier) προς αξιολόγηση. "
    "Σε αυτή την περίπτωση παρακαλούμε περιλάβετε και σύντομη περιγραφή του λόγου "
    "της εκπρόθεσμης υποβολής.\n\n"
    "Οι διευθύνσεις αποστολής και το αρμόδιο τμήμα παραλαβής επιβεβαιώνονται από "
    "τη γραμματεία μας κατά περίπτωση."
)


def main() -> int:
    db.init_db()

    # ---------- 1. Dental corrections ----------
    kb_dental = next(
        (e for e in db.list_kb_entries()
         if e["category"] == "Οδοντιατρικό περιστατικό"), None,
    )
    tpl_dental = next(
        (t for t in db.list_templates()
         if t["category"] == "Οδοντιατρικό περιστατικό"), None,
    )

    if kb_dental:
        db.update_kb_entry(
            kb_dental["id"],
            category="Οδοντιατρικό περιστατικό",
            question="Καλύπτει το ομαδικό οδοντιατρικές εργασίες και τι δικαιολογητικά χρειάζονται;",
            answer=DENTAL_CORRECTED_ANSWER,
        )
        print(f"✓ Updated KB #{kb_dental['id']} (Οδοντιατρικό περιστατικό)")

    if tpl_dental:
        db.update_template(
            tpl_dental["id"],
            title="Καλύπτει το ομαδικό οδοντιατρικές εργασίες;",
            category="Οδοντιατρικό περιστατικό",
            content=DENTAL_CORRECTED_ANSWER,
        )
        print(f"✓ Updated Template #{tpl_dental['id']} (Οδοντιατρικό περιστατικό)")

    # Separate "non-accident dental" entry — explicitly denies coverage
    existing_titles_tpl = {t["title"].strip() for t in db.list_templates()}
    existing_q_kb = {e["question"].strip() for e in db.list_kb_entries()}

    non_acc_title = "Οδοντιατρικά εκτός ατυχήματος (ρίζα, εμφύτευμα, ορθοδοντικά)"
    if non_acc_title not in existing_q_kb:
        db.create_kb_entry("Οδοντιατρικό περιστατικό", non_acc_title, DENTAL_NON_ACCIDENT_ANSWER)
        print(f"+ New KB: '{non_acc_title}'")
    if non_acc_title not in existing_titles_tpl:
        db.create_template(non_acc_title, "Οδοντιατρικό περιστατικό", DENTAL_NON_ACCIDENT_ANSWER)
        print(f"+ New Template: '{non_acc_title}'")

    # ---------- 2. Receipt submission deadline ----------
    cat_deadline = "Παλαιότερες αποδείξεις"  # existing category
    deadline_title = "Ποια είναι η προθεσμία υποβολής αποδείξεων;"
    if deadline_title not in existing_q_kb:
        db.create_kb_entry(cat_deadline, deadline_title, RECEIPT_DEADLINE_ANSWER)
        print(f"+ New KB: '{deadline_title}'")
    if deadline_title not in existing_titles_tpl:
        db.create_template(deadline_title, cat_deadline, RECEIPT_DEADLINE_ANSWER)
        print(f"+ New Template: '{deadline_title}'")

    print()
    print(f"Templates: {len(db.list_templates())}")
    print(f"KB entries: {len(db.list_kb_entries())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
