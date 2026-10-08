"""One-shot ingestion of real training data into kb_entries.

Sources:
- Excel: 31 Q&A pairs (Use_Case_7_AI_Common_Issues)
- PDF:   ΟΜΙΛΟΣ ΟΤΕ 3089 policy document, chunked by section heading
- Diff:  EVALUE 2848 differs only in 3 lines (maternity amounts + 1 exam) →
         stored as a single "σύγκριση ορίων" KB entry

Idempotent: skips rows whose exact question already exists.
Run:  .venv/bin/python ingest.py  [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

import db

DOWNLOADS = Path("/Users/lenatasia/Downloads")
EXCEL = DOWNLOADS / "Use_Case_7_AI_Common_Issuesνεο_QA_FINAL_25.xlsx"
PDF_MAIN = DOWNLOADS / "ΟΜΙΛΟΣ ΟΤΕ 3089_Γ.PDF"
PDF_ALT = DOWNLOADS / "EVALUE 2848_Γ.PDF"

POLICY_CATEGORY = "Όροι συμβολαίου"


# -------------------- Excel --------------------

def ingest_excel(dry: bool) -> tuple[int, int]:
    df = pd.read_excel(EXCEL, sheet_name="AI Q&A")
    df = df.dropna(subset=["Ερώτηση", "Προτεινόμενη απάντηση Auto-Responder"])

    existing_qs = {e["question"].strip() for e in db.list_kb_entries()}
    existing_cats = set(db.list_categories())

    added, skipped = 0, 0
    for _, row in df.iterrows():
        cat = str(row["Κατηγορία / Common Issue"]).strip()
        q = str(row["Ερώτηση"]).strip()
        a = str(row["Προτεινόμενη απάντηση Auto-Responder"]).strip()
        if not q or not a:
            continue
        if q in existing_qs:
            skipped += 1
            continue
        if cat not in existing_cats:
            if not dry:
                db.add_category(cat)
            existing_cats.add(cat)
        if not dry:
            db.create_kb_entry(cat, q, a)
        added += 1
    return added, skipped


# -------------------- PDF --------------------

# Headings are all-caps Greek lines that act as section titles in the policy.
# Pattern: line consisting mostly of uppercase Greek letters/digits/punct, >= 4 chars.
_HEADING_RE = re.compile(r"^[Α-Ω0-9A-Z][Α-Ω0-9A-Z\s\.\,\(\)\/\-]{3,}$")

# Known section titles observed in the policy — used to anchor splits even when
# PDF layout concatenates text across columns.
KNOWN_HEADINGS = [
    "ΟΜΑΔΙΚΗ ΑΣΦΑΛΙΣΗ",
    "ΕΝΑΡΞΗ ΚΑΙ ΔΙΑΚΟΠΗ ΤΗΣ ΑΣΦΑΛΙΣΗΣ",
    "ΠΙΝΑΚΑΣ ΚΑΛΥΨΕΩΝ",
    "ΑΣΦΑΛΙΣΗ ΖΩΗΣ",
    "ΝΟΣΟΚΟΜΕΙΑΚΗ ΠΕΡΙΘΑΛΨΗ",
    "ΕΞΩΝΟΣΟΚΟΜΕΙΑΚΗ ΠΕΡΙΘΑΛΨΗ",
    "ΕΠΙΔΟΜΑ ΜΗΤΡΟΤΗΤΑΣ",
    "ΕΠΙΔΟΜΑ ΧΕΙΡΟΥΡΓΕΙΟΥ",
    "ΕΠΙΔΟΜΑ ΝΟΣΗΛΕΙΑΣ",
    "ΑΠΩΛΕΙΑ ΕΙΣΟΔΗΜΑΤΟΣ",
    "ΜΟΝΙΜΗ ΟΛΙΚΗ ΑΝΙΚΑΝΟΤΗΤΑ",
    "ΔΙΑΔΙΚΑΣΙΑ ΑΠΟΖΗΜΙΩΣΗΣ",
    "ΕΞΑΙΡΕΣΕΙΣ",
    "ΔΙΚΑΙΟΛΟΓΗΤΙΚΑ",
    "ΟΡΙΣΜΟΙ",
    "ΓΕΝΙΚΟΙ ΟΡΟΙ",
    "CHECK UP",
]


def extract_pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join((pg.extract_text() or "") for pg in pdf.pages)


def chunk_policy(text: str, max_chars: int = 1800) -> list[tuple[str, str]]:
    """Split policy text into (heading, body) chunks.

    Strategy: find positions of known headings in the raw text, slice between.
    Long sections get further split on blank-line boundaries to stay under max_chars.
    """
    # Find anchor positions for every known heading that appears
    anchors: list[tuple[int, str]] = []
    for h in KNOWN_HEADINGS:
        for m in re.finditer(re.escape(h), text):
            anchors.append((m.start(), h))
    anchors.sort()
    # Dedupe anchors by position (keep first occurrence)
    seen = set()
    uniq: list[tuple[int, str]] = []
    for pos, h in anchors:
        if pos in seen:
            continue
        seen.add(pos)
        uniq.append((pos, h))
    anchors = uniq

    if not anchors:
        return [("Όροι συμβολαίου", text.strip())]

    sections: list[tuple[str, str]] = []
    for i, (pos, heading) in enumerate(anchors):
        end = anchors[i + 1][0] if i + 1 < len(anchors) else len(text)
        body = text[pos + len(heading):end].strip()
        body = re.sub(r"\s+\n", "\n", body)
        body = re.sub(r"\n{3,}", "\n\n", body)
        if not body:
            continue
        # Further split overly long sections
        if len(body) <= max_chars:
            sections.append((heading, body))
        else:
            parts = _soft_split(body, max_chars)
            for j, part in enumerate(parts, 1):
                label = heading if len(parts) == 1 else f"{heading} ({j}/{len(parts)})"
                sections.append((label, part))
    return sections


def _soft_split(text: str, max_chars: int) -> list[str]:
    """Split long text on blank-line boundaries, each piece <= max_chars."""
    out: list[str] = []
    buf = ""
    for para in re.split(r"\n{2,}", text):
        if len(buf) + len(para) + 2 <= max_chars:
            buf = f"{buf}\n\n{para}" if buf else para
        else:
            if buf:
                out.append(buf.strip())
            if len(para) <= max_chars:
                buf = para
            else:
                for i in range(0, len(para), max_chars):
                    out.append(para[i:i + max_chars].strip())
                buf = ""
    if buf:
        out.append(buf.strip())
    return [s for s in out if s]


def ingest_policy(dry: bool) -> tuple[int, int]:
    text = extract_pdf_text(PDF_MAIN)
    chunks = chunk_policy(text)

    existing_qs = {e["question"].strip() for e in db.list_kb_entries()}
    existing_cats = set(db.list_categories())
    if POLICY_CATEGORY not in existing_cats and not dry:
        db.add_category(POLICY_CATEGORY)

    added, skipped = 0, 0
    for heading, body in chunks:
        q = f"[Συμβόλαιο ΟΤΕ 3089] {heading}"
        if q in existing_qs:
            skipped += 1
            continue
        if not dry:
            db.create_kb_entry(POLICY_CATEGORY, q, body)
        added += 1

    # One comparison entry for the 3 lines where EVALUE 2848 differs
    diff_q = "Σύγκριση ορίων κάλυψης: EVALUE 2848 vs ΟΜΙΛΟΣ ΟΤΕ 3089"
    diff_a = (
        "Τα δύο συμβόλαια έχουν τους ίδιους όρους εκτός από τα εξής όρια:\n\n"
        "ΕΠΙΔΟΜΑ ΜΗΤΡΟΤΗΤΑΣ\n"
        "• Φυσιολογικός τοκετός: EVALUE 2848 → 700,00 €  |  ΟΜΙΛΟΣ ΟΤΕ 3089 → 1.500,00 €\n"
        "• Καισαρική τομή:       EVALUE 2848 → 1.000,00 € |  ΟΜΙΛΟΣ ΟΤΕ 3089 → 2.000,00 €\n\n"
        "CHECK UP (προληπτικός έλεγχος)\n"
        "• Το EVALUE 2848 περιλαμβάνει επιπλέον Ακουόγραμμα· στο ΟΜΙΛΟΣ ΟΤΕ 3089 δεν περιλαμβάνεται."
    )
    if diff_q not in existing_qs:
        if not dry:
            db.create_kb_entry(POLICY_CATEGORY, diff_q, diff_a)
        added += 1
    else:
        skipped += 1

    return added, skipped


# -------------------- main --------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db.init_db()

    print(f"{'DRY RUN — no writes' if args.dry_run else 'INGESTING'}")
    print(f"DB: {db.DB_PATH if hasattr(db, 'DB_PATH') else '(see config.DB_PATH)'}")

    before = len(db.list_kb_entries())
    print(f"KB entries before: {before}")

    ex_added, ex_skip = ingest_excel(args.dry_run)
    print(f"\n[Excel] added={ex_added}  skipped(dup)={ex_skip}")

    pdf_added, pdf_skip = ingest_policy(args.dry_run)
    print(f"[PDF]   added={pdf_added}  skipped(dup)={pdf_skip}")

    after = len(db.list_kb_entries())
    print(f"\nKB entries after:  {after}  (Δ={after - before})")
    print(f"Categories now:    {len(db.list_categories())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
