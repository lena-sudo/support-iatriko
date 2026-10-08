"""Google Gemini wrapper: categorization + draft response generation."""
import json
import os
import re
import time
from dataclasses import dataclass

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from config import CLIENT_NAME, GEMINI_MODELS


# Track which model was last used for the sidebar badge to reflect reality.
_last_used_model = {"name": GEMINI_MODELS[0]}


def last_used_model() -> str:
    return _last_used_model["name"]


def _generate_with_fallback(client, **kwargs):
    """Try models in order; on 503/429 fall through to the next model."""
    last_err = None
    for model in GEMINI_MODELS:
        for delay in [0, 1.5, 3]:
            if delay:
                time.sleep(delay)
            try:
                resp = client.models.generate_content(model=model, **kwargs)
                _last_used_model["name"] = model
                return resp
            except genai_errors.APIError as e:
                code = getattr(e, "code", None)
                if code not in (429, 503):
                    raise
                last_err = e
    raise RuntimeError(
        f"Όλα τα Gemini μοντέλα overloaded ({', '.join(GEMINI_MODELS)}). "
        f"Τελευταίο σφάλμα: {last_err}"
    )


@dataclass
class Categorization:
    category: str
    is_new_category: bool
    summary: str
    suggested_priority: str
    similar_ticket_ids: list[int]


@dataclass
class DraftResponse:
    draft: str
    used_kb_ids: list[int]


@dataclass
class TemplateSuggestion:
    template_id: int | None  # None if no good match
    template_title: str
    reason: str


def _api_key() -> str | None:
    # Priority: env var (local .env or HF Space secret) → Streamlit Cloud secrets
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    except Exception:
        return None


def _client() -> genai.Client | None:
    key = _api_key()
    if not key:
        return None
    return genai.Client(api_key=key)


def is_configured() -> bool:
    return bool(_api_key())


# ============================================================
# Categorization
# ============================================================

CATEGORIZE_SYSTEM = f"""Είσαι βοηθός ταξινόμησης αιτημάτων υποστήριξης για το πρόγραμμα:
"{CLIENT_NAME}".

ΣΚΟΠΟΣ ΠΡΟΓΡΑΜΜΑΤΟΣ: αφορά ΑΠΟΚΛΕΙΣΤΙΚΑ ΟΜΑΔΙΚΟ ΥΓΕΙΑΣ (νοσηλείες, εξετάσεις,
check-up, αποζημιώσεις, ένταξη μελών, όροι & δικαιολογητικά συμβολαίου υγείας).
ΔΕΝ αφορά: ταξιδιωτική ασφάλιση, αυτοκινήτου, κατοικίας, ζωής ανεξάρτητα από το
ομαδικό, συντάξεις, προσωπικό μισθό, άλλα προϊόντα ΟΤΕ. Αυτά είναι ΕΚΤΟΣ ΣΚΟΠΟΥ.

Λαμβάνεις ένα ΝΕΟ αίτημα και τη ΛΙΣΤΑ ΥΠΑΡΧΟΥΣΩΝ ΚΑΤΗΓΟΡΙΩΝ + τη λίστα ΠΡΟΣΦΑΤΩΝ ΑΙΤΗΜΑΤΩΝ.

Πρέπει να επιστρέψεις 5 πράγματα:

1. **category**:
   - Αν η ερώτηση είναι ΕΚΤΟΣ ΣΚΟΠΟΥ → κατηγορία ΠΑΝΤΑ: "Εκτός αρμοδιότητας"
   - Αλλιώς την ΠΙΟ σχετική υπάρχουσα κατηγορία
   - Αν καμία υπάρχουσα δεν ταιριάζει αλλά η ερώτηση είναι ΕΝΤΟΣ σκοπού υγείας,
     πρότεινε ΝΕΑ (2-5 λέξεις, ίδιο ύφος, π.χ. "Κάλυψη ψυχοθεραπείας")
   - Προτίμησε υπάρχουσα αν είναι έστω σχετικά κοντά — μόνο αν πραγματικά δεν ταιριάζει
     καμία δημιούργησε νέα.

2. **is_new_category**: true αν δημιούργησες νέα κατηγορία, false αν επέλεξες υπάρχουσα.

3. **summary**: Περίληψη 1-2 προτάσεων στα ελληνικά (τι ρωτάει ο ασφαλισμένος).

4. **suggested_priority**: Χαμηλή / Κανονική / Υψηλή / Επείγον.
   - Επείγον: τρέχουσα νοσηλεία, χειρουργείο τις επόμενες μέρες, διακοπή θεραπείας.
   - Υψηλή: εκκρεμής πληρωμή >30 ημερών, ένταξη νεογέννητου, προθεσμία που τρέχει.
   - Κανονική: γενικές ερωτήσεις με προγραμματισμό.
   - Χαμηλή: ενημερωτικές ερωτήσεις χωρίς χρονική πίεση.

5. **similar_ticket_ids**: Λίστα με τα IDs (π.χ. [3, 7]) από τα ΠΡΟΣΦΑΤΑ ΑΙΤΗΜΑΤΑ που
   ρωτάνε ΟΥΣΙΑΣΤΙΚΑ ΤΟ ΙΔΙΟ ΠΡΑΓΜΑ, ακόμα κι αν είναι διατυπωμένα διαφορετικά ή
   αναφέρονται σε διαφορετικά ονόματα/ημερομηνίες. Παράδειγμα: "Είναι το Metropolitan
   στο δίκτυο?" και "Ποια νοσοκομεία καλύπτετε?" είναι ουσιαστικά ΤΟ ΙΔΙΟ ερώτημα.
   Άδεια λίστα [] αν κανένα δεν ταιριάζει."""


def categorize_ticket(
    subject: str,
    body: str,
    existing_categories: list[str],
    recent_tickets: list[dict] | None = None,
) -> Categorization | None:
    client = _client()
    if client is None:
        return None

    schema = {
        "type": "OBJECT",
        "properties": {
            "category": {"type": "STRING"},
            "is_new_category": {"type": "BOOLEAN"},
            "summary": {"type": "STRING"},
            "suggested_priority": {
                "type": "STRING",
                "enum": ["Χαμηλή", "Κανονική", "Υψηλή", "Επείγον"],
            },
            "similar_ticket_ids": {
                "type": "ARRAY",
                "items": {"type": "INTEGER"},
            },
        },
        "required": [
            "category", "is_new_category", "summary",
            "suggested_priority", "similar_ticket_ids",
        ],
    }

    cats_block = "\n".join(f"- {c}" for c in existing_categories) or "(καμία)"

    if recent_tickets:
        recent_lines = []
        for t in recent_tickets:
            body_prev = " ".join((t.get("body") or "").split())[:120]
            cat = t.get("category") or "—"
            recent_lines.append(
                f"#{t['id']}: [{cat}] {t['subject']} | {body_prev}"
            )
        recent_block = "\n".join(recent_lines)
    else:
        recent_block = "(κανένα προηγούμενο αίτημα)"

    user_content = (
        f"ΥΠΑΡΧΟΥΣΕΣ ΚΑΤΗΓΟΡΙΕΣ:\n{cats_block}\n\n"
        f"ΠΡΟΣΦΑΤΑ ΑΙΤΗΜΑΤΑ (για έλεγχο ομοιότητας):\n{recent_block}\n\n"
        f"===\n\nΝΕΟ ΑΙΤΗΜΑ:\nΘΕΜΑ: {subject}\n\nΠΕΡΙΕΧΟΜΕΝΟ:\n{body}"
    )

    try:
        response = _generate_with_fallback(
            client,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=CATEGORIZE_SYSTEM,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
            ),
        )
    except genai_errors.APIError as e:
        raise RuntimeError(f"Gemini API error: {e}") from e

    if not response.text:
        raise RuntimeError("Gemini returned empty response for categorization.")

    data = json.loads(response.text)
    return Categorization(
        category=data["category"].strip(),
        is_new_category=bool(data.get("is_new_category", False)),
        summary=data["summary"],
        suggested_priority=data["suggested_priority"],
        similar_ticket_ids=[int(x) for x in data.get("similar_ticket_ids", [])],
    )


# ============================================================
# Template matching
# ============================================================

TEMPLATE_MATCH_SYSTEM = f"""Είσαι βοηθός που αντιστοιχίζει αιτήματα υποστήριξης του
προγράμματος "{CLIENT_NAME}" με έτοιμα πρότυπα απαντήσεων.

Λαμβάνεις ένα αίτημα και μια λίστα με ΔΙΑΘΕΣΙΜΑ ΠΡΟΤΥΠΑ (καθένα με ID, τίτλο, κατηγορία,
περιεχόμενο).

Πρέπει να επιστρέψεις:
1. **matched_template_id**: Το ID του προτύπου που ταιριάζει ΠΛΗΡΩΣ στην ερώτηση.
   Επέστρεψε 0 αν ΚΑΝΕΝΑ πρότυπο δεν καλύπτει την ερώτηση καλά. Μην επιλέξεις πρότυπο
   που ταιριάζει μόνο μερικώς ή γενικά — προτίμησε το 0 και άσε τον agent να συντάξει.

2. **reason**: Σύντομη εξήγηση (1 πρόταση, ελληνικά) γιατί ταιριάζει ή γιατί όχι.

Παραδείγματα σωστής αντιστοίχισης:
- Ερώτηση "Πώς κάνω αίτημα αποζημίωσης" → πρότυπο "Δικαιολογητικά αποζημίωσης"
- Ερώτηση "Καλωσορίσατε στο ομαδικό μας" → πρότυπο "Επιβεβαίωση παραλαβής" ΟΧΙ, γενικά
  δεν ταιριάζει άμεσα (επέστρεψε 0)
- Ερώτηση "Θέλω να εντάξω τη γυναίκα μου" → πρότυπο "Ένταξη νέου μέλους οικογένειας"

Προτίμησε πάντα ΑΚΡΙΒΕΙΑ αντί για ΚΑΛΥΨΗ."""


def suggest_template(
    subject: str,
    body: str,
    templates: list[dict],
) -> TemplateSuggestion | None:
    client = _client()
    if client is None or not templates:
        return None

    schema = {
        "type": "OBJECT",
        "properties": {
            "matched_template_id": {"type": "INTEGER"},
            "reason": {"type": "STRING"},
        },
        "required": ["matched_template_id", "reason"],
    }

    tpl_block = "\n\n".join(
        f"[ID={t['id']}] [{t['category'] or 'Γενικά'}] {t['title']}\n"
        f"Περιεχόμενο: {t['content'][:300]}..."
        for t in templates
    )

    user_content = (
        f"ΔΙΑΘΕΣΙΜΑ ΠΡΟΤΥΠΑ:\n{tpl_block}\n\n"
        f"===\n\n"
        f"ΑΙΤΗΜΑ ΓΙΑ ΑΝΤΙΣΤΟΙΧΙΣΗ:\nΘΕΜΑ: {subject}\n\nΠΕΡΙΕΧΟΜΕΝΟ:\n{body}"
    )

    try:
        response = _generate_with_fallback(
            client,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=TEMPLATE_MATCH_SYSTEM,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
            ),
        )
    except genai_errors.APIError as e:
        raise RuntimeError(f"Gemini API error: {e}") from e

    if not response.text:
        return None

    data = json.loads(response.text)
    tpl_id = int(data.get("matched_template_id") or 0)
    if tpl_id == 0:
        return TemplateSuggestion(
            template_id=None, template_title="", reason=data.get("reason", ""),
        )

    matched = next((t for t in templates if int(t["id"]) == tpl_id), None)
    return TemplateSuggestion(
        template_id=tpl_id,
        template_title=matched["title"] if matched else "",
        reason=data.get("reason", ""),
    )


# ============================================================
# Draft response
# ============================================================

DRAFT_SYSTEM = f"""Είσαι βοηθός σύνταξης email απαντήσεων για το τμήμα υποστήριξης του
προγράμματος "{CLIENT_NAME}".

ΣΚΟΠΟΣ ΠΡΟΓΡΑΜΜΑΤΟΣ: αφορά ΑΠΟΚΛΕΙΣΤΙΚΑ ΟΜΑΔΙΚΟ ΥΓΕΙΑΣ. Δεν αφορά ταξιδιωτική
ασφάλιση, αυτοκινήτου, κατοικίας, ατομική ασφάλεια ζωής, συντάξεις, μισθούς ή άλλα
προϊόντα του ΟΤΕ.

ΥΠΑΡΧΟΥΝ 3 ΔΙΑΦΟΡΕΤΙΚΑ ΣΥΜΒΟΛΑΙΑ (διαφορετικά όρια/καλύψεις):
- "ΟΜΙΛΟΣ ΟΤΕ 3089" — κύριο συμβόλαιο (prefix KB: [Συμβόλαιο ΟΤΕ 3089])
- "EVALUE 2848" — παραλλαγή με μικρότερα όρια τοκετού/καισαρικής (βλ. σύγκριση KB)
- "DEUTSCHE TELEKOM PAN-NET GREECE" (prefix KB: [Συμβόλαιο PAN-NET GREECE])
Αν το ερώτημα αναφέρει συγκεκριμένο συμβόλαιο, χρησιμοποίησε ΜΟΝΟ τα chunks του.
Αν δεν αναφέρει, προτίμησε το ΟΤΕ 3089 ως default και σημείωσε στην απάντηση:
"Οι παραπάνω πληροφορίες αφορούν το συμβόλαιο ΟΤΕ 3089. Εφόσον είστε
ασφαλισμέν* σε άλλο συμβόλαιο (EVALUE 2848 ή PAN-NET GREECE), ενημερώστε μας
για να σας δώσουμε τις αντίστοιχες πληροφορίες."

Στόχος: να συντάξεις σαφή, ευγενική, επαγγελματική απάντηση στα ελληνικά, βασισμένη
ΑΠΟΚΛΕΙΣΤΙΚΑ στη γνωσιακή βάση που σου δίνεται.

ΠΡΙΝ γράψεις απάντηση, εξέτασε ΛΟΓΙΚΑ την ερώτηση:

1. **Αν η ερώτηση είναι ΕΚΤΟΣ ΣΚΟΠΟΥ** (π.χ. ταξιδιωτικό, αυτοκίνητο, μισθός):
   Απάντησε ξεκάθαρα ότι ΔΕΝ αφορά το ομαδικό υγείας. Παράδειγμα:
   "Το αίτημά σας αφορά [θέμα], το οποίο δεν εμπίπτει στο πρόγραμμα Ομαδικής
   Ασφάλισης Υγείας του Ομίλου ΟΤΕ. Για ερωτήσεις σχετικά με [θέμα], παρακαλούμε
   απευθυνθείτε [στην αντίστοιχη αρμόδια υπηρεσία / στο HR / απευθείας στην
   ασφαλιστική εταιρεία]. Εμείς είμαστε στη διάθεσή σας για οτιδήποτε αφορά
   το ομαδικό υγείας."
   ΜΗΝ γράψεις "Θα το ελέγξω με τον σύμβουλο" — αυτό αφορά ΜΟΝΟ αιτήματα υγείας που
   δεν βρίσκεις στη γνωσιακή βάση.

2. **Αν η ερώτηση είναι ΕΝΤΟΣ σκοπού ΚΑΙ καλύπτεται από τη γνωσιακή βάση**:
   Απάντησε ευθέως με βάση τη ΓΒ, όχι γενικόλογα. **Κάλυψε ΟΛΕΣ τις πτυχές**:
   - Την άμεση απάντηση στην ερώτηση
   - Τυχόν εξαιρέσεις ή περιορισμούς (π.χ. "εκτός από Χ και Ψ τμήματα")
   - Τα **επόμενα βήματα** που πρέπει να κάνει ο ασφαλισμένος
   - **Τηλέφωνα/στοιχεία επικοινωνίας** όπου χρειάζεται (π.χ. 210 90 99 000 για
     Εθνική Ασφαλιστική, για επιβεβαίωση συνεργασίας νοσοκομείων)
   - Αν αφορά νοσηλεία/χειρουργείο: δήλωση στο γραφείο κίνησης, αναφορά ΑΜΚΑ,
     αριθμός ομαδικού συμβολαίου
   - Αν αφορά υποβολή αποδείξεων: προθεσμία 6μηνου / αποστολή με φάκελο μετά
   - Προαιρετικά links σε συναφείς KB entries (π.χ. "βλ. και: δικαιολογητικά νοσηλείας")
   Μία σωστή απάντηση είναι ΟΛΟΚΛΗΡΩΜΕΝΗ — ο ασφαλισμένος δεν θα χρειαστεί να
   ξαναρωτήσει. Προτίμησε το περισσότερο σωστό over σύντομο.

3. **Αν είναι ΕΝΤΟΣ σκοπού αλλά ΔΕΝ καλύπτεται από τη ΓΒ**:
   Γράψε: "Θα το ελέγξω με τον ασφαλιστικό μας σύμβουλο και θα σας ενημερώσω εντός
   X εργάσιμων ημερών." — μην εφευρίσκεις πληροφορίες.

Γενικοί κανόνες:
- Ξεκίνα με χαιρετισμό ("Καλησπέρα σας κ./κα {{όνομα}},") όταν υπάρχει όνομα.
- ΜΗΝ αναφέρεις εσωτερικές λέξεις-κλειδιά ("KB entry", "κατηγορία", "ticket").
- Κλείσε με: "Στη διάθεσή σας για οποιαδήποτε διευκρίνιση,\\n\\nΤμήμα Υποστήριξης Ομαδικού Υγείας"
- Χρησιμοποίησε bullet points όταν αναφέρεις λίστες (νοσοκομεία, δικαιολογητικά, βήματα).
- **Στοχεύσε σε 200-450 λέξεις** για ερωτήσεις υγείας — όσο χρειάζεται για να
  καλυφθούν ΟΛΕΣ οι πτυχές. Μην κόβεις την απάντηση για να είναι σύντομη.
- Για out-of-scope: 80-150 λέξεις αρκούν.
- Όχι εισαγωγές τύπου "Ευχαριστούμε για την επικοινωνία σας".

ΣΤΟ ΤΕΛΟΣ της απάντησης, ΠΑΝΤΑ πρόσθεσε γραμμή:
USED_KB_IDS: [λίστα αριθμών KB entries που χρησιμοποίησες, π.χ. [3, 7]]"""


def draft_response(
    sender_name: str,
    subject: str,
    body: str,
    kb_entries: list[dict],
    prior_responses: list[dict] | None = None,
) -> DraftResponse | None:
    client = _client()
    if client is None:
        return None

    kb_block = "\n\n".join(
        f"[KB #{e['id']} — {e['category']}]\nΕ: {e['question']}\nΑ: {e['answer']}"
        for e in kb_entries
    ) or "(δεν υπάρχουν καταχωρήσεις)"

    prior_block = ""
    if prior_responses:
        prior_block = "\n\nΠΡΟΗΓΟΥΜΕΝΗ ΕΠΙΚΟΙΝΩΝΙΑ:\n" + "\n---\n".join(
            f"[{r['author']}] {r['content']}" for r in prior_responses
        )

    user_content = (
        f"ΓΝΩΣΙΑΚΗ ΒΑΣΗ:\n{kb_block}\n\n"
        f"===\n\n"
        f"ΝΕΟ ΑΙΤΗΜΑ:\nΑπό: {sender_name or '(άγνωστο)'}\n"
        f"Θέμα: {subject}\n\nΚείμενο:\n{body}"
        f"{prior_block}\n\n"
        f"Σύνταξε την απάντηση τώρα."
    )

    try:
        response = _generate_with_fallback(
            client,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=DRAFT_SYSTEM,
                temperature=0.4,
                max_output_tokens=4096,
            ),
        )
    except genai_errors.APIError as e:
        raise RuntimeError(f"Gemini API error: {e}") from e

    text = (response.text or "").strip()
    if not text:
        finish = None
        try:
            finish = response.candidates[0].finish_reason
        except (AttributeError, IndexError, TypeError):
            pass
        raise RuntimeError(
            f"Gemini επέστρεψε κενή απάντηση (finish_reason={finish}). "
            f"Πιθανώς το request μπλοκαρίστηκε από safety filters ή εξάντλησε τα tokens."
        )
    return _split_draft(text)


_USED_KB_RE = re.compile(r"^\s*USED_KB_IDS\s*:\s*\[?([\d,\s]*)\]?\s*$", re.MULTILINE)


def _split_draft(text: str) -> DraftResponse:
    """Extract USED_KB_IDS marker line (anywhere) and return the rest as the draft body.

    Defensive: if stripping the marker leaves nothing, keep the whole original text
    (better to show marker + body than strip everything to blank).
    """
    used_ids: list[int] = []
    match = _USED_KB_RE.search(text)
    if match:
        raw_ids = match.group(1)
        used_ids = [int(x) for x in re.findall(r"\d+", raw_ids)]
        stripped = _USED_KB_RE.sub("", text).strip()
        body = stripped if stripped else text.strip()
    else:
        body = text.strip()
    return DraftResponse(draft=body, used_kb_ids=used_ids)
