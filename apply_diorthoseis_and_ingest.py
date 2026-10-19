"""Apply the 6 Q&A corrections from Diorthoseis_QA_Link.docx and ingest 3 new PDFs.

Idempotent: skips questions that already exist with identical answer; otherwise updates.
Run: .venv/bin/python apply_diorthoseis_and_ingest.py
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pdfplumber

import db

# -------- 6 QA corrections (exact text from docx) --------

CORRECTIONS: list[tuple[int, str, str, str]] = [
    (
        15,
        "Χρόνος αξιολόγησης",
        "Σε πόσες ημέρες αξιολογούνται συνήθως τα αιτήματα;",
        "Σας ενημερώνουμε ότι γενικά τα αιτήματα αξιολογούνται από την Εθνική Ασφαλιστική "
        "μέσα σε 5 εργάσιμες ημέρες. Παρόλα αυτά, λόγω της διαδικασίας αξιολόγησης, "
        "ενδέχεται σε ορισμένες περιπτώσεις να απαιτηθεί επιπλέον χρόνος.",
    ),
    (
        91,
        "Παλαιότερες αποδείξεις",
        "Ποια είναι η προθεσμία υποβολής αποδείξεων;",
        "Η υποβολή αποδείξεων και παραστατικών μέσω της πλατφόρμας μπορεί να πραγματοποιηθεί "
        "εντός 6 μηνών (180 ημερών) από την ημερομηνία έκδοσής τους.\n\n"
        "Μετά την παρέλευση της προθεσμίας, τα δικαιολογητικά μπορούν να αποσταλούν σε έντυπη "
        "μορφή, με συστημένη επιστολή ή courier, μαζί με την αίτηση αποζημίωσης, στη διεύθυνση: "
        "Διοικητικό Μέγαρο ΟΤΕ, Λεωφόρος Κηφισίας 99, Μαρούσι 15124 – 10Β - 1R.",
    ),
    (
        14,
        "Σχόλια διακανονιστή",
        "Μπορείτε να ελέγξετε την πορεία του αιτήματός μου;",
        "Παρακαλώ ενημερώστε μας για την ημερομηνία υποβολής του αιτήματος και ελέγξτε αν "
        "εσωτερικά στο αίτημα υπάρχουν περαιτέρω σχόλια διακανονιστή, καθώς δεν έχουμε online "
        "εικόνα της πλατφόρμας.",
    ),
    (
        90,
        "Οδοντιατρικό περιστατικό",
        "Οδοντιατρικά εκτός ατυχήματος (ρίζα, εμφύτευμα, ορθοδοντικά)",
        "Το ομαδικό πρόγραμμα Υγείας του Ομίλου ΟΤΕ δεν καλύπτει προγραμματισμένες οδοντιατρικές "
        "εργασίες.\n\n"
        "Στο συνημμένο, το οποίο είναι αναρτημένο και στο MyNet, θα βρείτε πληροφορίες για "
        "οδοντιατρικές υπηρεσίες που παρέχονται από το Διαγνωστικό Κέντρο Κηφισιάς σε ειδικές "
        "τιμές για τους εργαζομένους του ΟΤΕ. Η συγκεκριμένη παροχή δεν αφορά το ομαδικό "
        "ασφαλιστήριο.\n\n"
        "Επειδή οι παροχές ενδέχεται να έχουν αλλάξει, συνιστάται τηλεφωνική επιβεβαίωση των "
        "ειδικών τιμών πριν από τον προγραμματισμό ραντεβού.",
    ),
    (
        27,
        "Επέκταση ομαδικού",
        "Μπορώ να κάνω επέκταση του ομαδικού συμβολαίου;",
        "Θα θέλαμε να σας ενημερώσουμε ότι δεν προβλέπεται διαδικασία επέκτασης ομαδικού "
        "συμβολαίου. Ωστόσο, μπορείτε να επικοινωνήσετε με συνεργαζόμενους ασφαλιστές μας για "
        "εναλλακτικές λύσεις που ενδέχεται να σας καλύψουν σε ατομικό επίπεδο. Στοιχεία "
        "επικοινωνίας: «Οι ασφαλιστές μας | Magenta Insurance».",
    ),
    (
        79,
        "Ταξιδιωτική ασφάλιση",
        "Ερώτηση για ταξιδιωτική ασφάλιση",
        "Το Ομαδικό Πρόγραμμα παρέχει Ταξιδιωτική Βοήθεια για επαγγελματικά και προσωπικά "
        "ταξίδια, για εσάς και τα εξαρτώμενα μέλη σας.\n\n"
        "Για νοσηλεία στο εξωτερικό, η κάλυψη εξετάζεται απολογιστικά. Μετά τη νοσηλεία, "
        "μπορείτε να υποβάλετε στην Εθνική τα σχετικά δικαιολογητικά προς αξιολόγηση, "
        "μεταφρασμένα και επικυρωμένα, όπως προβλέπεται από το Ομαδικό Συμβόλαιο. Για "
        "ενεργοποίηση και εξέταση των παροχών, επικοινωνήστε με το τηλεφωνικό κέντρο του "
        "σχετικού ενημερωτικού εντύπου.\n\n"
        "Η ταξιδιωτική κάλυψη της AXA αφορά επαγγελματικά ταξίδια και δεν απαιτεί προηγούμενη "
        "αναγγελία ή ενημέρωση για το ταξίδι. Αν προκύψει ανάγκη, επικοινωνήστε με το Call "
        "Center της AXA για καθοδήγηση και ενεργοποίηση υπηρεσιών.\n\n"
        "Επισυνάπτονται οι σχετικές πληροφορίες, οι παροχές και τα απαραίτητα τηλέφωνα "
        "επικοινωνίας.",
    ),
]


# -------- PDF ingestion --------

def _soft_split(text: str, max_chars: int) -> list[str]:
    out: list[str] = []
    buf = ""
    for para in re.split(r"\n{2,}", text):
        para = para.strip()
        if not para:
            continue
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


def extract_text_plumber(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join((pg.extract_text() or "") for pg in pdf.pages)


def extract_text_ocr(path: Path, lang: str = "eng") -> str:
    import pymupdf  # type: ignore
    import pytesseract  # type: ignore
    from PIL import Image

    doc = pymupdf.open(path)
    out = []
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        out.append(pytesseract.image_to_string(img, lang=lang))
    return "\n\n".join(out)


# Chunk strategies per PDF — small docs get 1-2 chunks, big ones split by section
PDF_PLAN: list[dict] = [
    {
        "path": Path("/Users/lenatasia/Downloads/Ταξιδιωτική Βοήθεια.pdf"),
        "label": "[Ταξιδιωτική Βοήθεια — ΕΘΝΙΚΗ ASSISTANCE]",
        "category": "Ταξιδιωτική Βοήθεια (ΕΘΝΙΚΗ)",
        "extractor": "plumber",
        "section_pattern": None,  # single chunk, soft split
        "max_chars": 2200,
    },
    {
        "path": Path("/Users/lenatasia/Downloads/ΕΝΗΜΕΡΩΤΙΚΟ ΕΝΤΥΠΟ ΥΠΑΛΛΗΛΩΝ ΟΤΕ ΓΙΑ ΠΑΡΟΧΕΣ ΒΙΟΙΑΤΡΙΚΗΣ.PDF"),
        "label": "[Παροχές Βιοιατρικής]",
        "category": "Πρόσθετες παροχές (Βιοιατρική)",
        "extractor": "plumber",
        "section_pattern": r"^❖\s*(.+)$",  # headings start with ❖
        "max_chars": 2200,
    },
    {
        "path": Path("/Users/lenatasia/Downloads/Infosheet FlexMed Global Travel Telekom_01.2022_EN.pdf"),
        "label": "[AXA FlexMed Global Travel]",
        "category": "Ταξιδιωτική Βοήθεια (AXA)",
        "extractor": "ocr",
        "section_pattern": None,
        "max_chars": 2200,
    },
]


def ingest_pdf(plan: dict) -> tuple[int, int]:
    path = plan["path"]
    if not path.exists():
        print(f"  SKIP (not found): {path}")
        return 0, 0

    if plan["extractor"] == "ocr":
        text = extract_text_ocr(path, lang="eng")
    else:
        text = extract_text_plumber(path)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    chunks: list[tuple[str, str]] = []
    pat = plan.get("section_pattern")
    if pat:
        rx = re.compile(pat, re.MULTILINE)
        matches = list(rx.finditer(text))
        if matches:
            for i, m in enumerate(matches):
                heading = m.group(1).strip()
                start = m.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                body = text[start:end].strip()
                if not body:
                    continue
                if len(body) <= plan["max_chars"]:
                    chunks.append((heading, body))
                else:
                    parts = _soft_split(body, plan["max_chars"])
                    for j, p in enumerate(parts, 1):
                        label = heading if len(parts) == 1 else f"{heading} ({j}/{len(parts)})"
                        chunks.append((label, p))
        else:
            parts = _soft_split(text, plan["max_chars"])
            for j, p in enumerate(parts, 1):
                chunks.append((f"Μέρος {j}/{len(parts)}", p))
    else:
        parts = _soft_split(text, plan["max_chars"])
        for j, p in enumerate(parts, 1):
            label = "Σύνοψη" if len(parts) == 1 else f"Μέρος {j}/{len(parts)}"
            chunks.append((label, p))

    existing_qs = {e["question"].strip() for e in db.list_kb_entries()}
    existing_cats = set(db.list_categories())
    if plan["category"] not in existing_cats:
        db.add_category(plan["category"])

    added, skipped = 0, 0
    for heading, body in chunks:
        q = f"{plan['label']} {heading}"
        if q in existing_qs:
            skipped += 1
            continue
        db.create_kb_entry(plan["category"], q, body)
        added += 1
    return added, skipped


# -------- main --------

def apply_corrections() -> tuple[int, int]:
    updated, missing = 0, 0
    with db.conn() as c:
        for kb_id, cat, q, a in CORRECTIONS:
            row = c.execute("SELECT answer FROM kb_entries WHERE id = ?", (kb_id,)).fetchone()
            if row is None:
                print(f"  MISSING id={kb_id}: {q[:60]}")
                missing += 1
                continue
            c.execute(
                "UPDATE kb_entries SET category = ?, question = ?, answer = ?, updated_at = ? WHERE id = ?",
                (cat, q, a, db.now(), kb_id),
            )
            updated += 1
            print(f"  UPDATED id={kb_id}: {q[:70]}")
    return updated, missing


def main() -> int:
    db.init_db()
    before = len(db.list_kb_entries())
    print(f"KB entries before: {before}")

    print("\n=== Applying 6 Q&A corrections ===")
    upd, miss = apply_corrections()
    print(f"  → updated={upd}  missing={miss}")

    print("\n=== Ingesting 3 PDFs ===")
    for plan in PDF_PLAN:
        print(f"\n[{plan['label']}]  {plan['path'].name}")
        a, s = ingest_pdf(plan)
        print(f"  → added={a}  skipped(dup)={s}")

    after = len(db.list_kb_entries())
    print(f"\nKB entries after:  {after}  (Δ={after - before})")
    print(f"Categories total:  {len(db.list_categories())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
