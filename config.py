from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "tickets.db"

CLIENT_NAME = "Magenta Insurance — Ομαδικό Υγείας Εργαζομένων Ομίλου OTE"
BRAND_PRIMARY = "#E20074"
BRAND_PRIMARY_DARK = "#A50055"
BRAND_BG_SOFT = "#FBEEF5"

# Categories are data-driven: όλες προέρχονται από τα Excel Q&A + τα PDF συμβόλαια.
# Αν το DB αδειάσει, θα χρειαστεί re-run του ingest.py.
CATEGORIES: list[str] = []

CHANNELS = ["Email", "Τηλέφωνο", "Teams", "Άλλο"]

STATUSES = ["Νέο", "Σε εξέλιξη", "Αναμένει πληροφορίες", "Απαντήθηκε", "Έκλεισε"]

PRIORITIES = ["Χαμηλή", "Κανονική", "Υψηλή", "Επείγον"]

ASSIGNEES = [
    "Εύα Σετέν",
    "Δήμητρα Λυκοθανάση",
    "Σοφία Λοΐζου",
    "— Χωρίς ανάθεση —",
]

# Fallback chain: try primary first, fall through to lighter models on 503 (overload).
# Lite variants are less popular → rarely overloaded → reliable fallback.
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
]
GEMINI_MODEL = GEMINI_MODELS[0]  # kept for backward compatibility
