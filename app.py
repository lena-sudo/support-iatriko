"""Support_Iatriko — Streamlit dashboard for Magenta Insurance group health tickets."""
from pathlib import Path

import streamlit as st

import ai
import db
from config import (
    ASSIGNEES,
    BRAND_PRIMARY,
    BRAND_PRIMARY_DARK,
    CATEGORIES,
    CHANNELS,
    CLIENT_NAME,
    PRIORITIES,
    STATUSES,
)
from seed import seed_if_empty


def get_categories() -> list[str]:
    """Live list of categories from DB (union of seed + AI-discovered)."""
    return db.list_categories()


st.set_page_config(
    page_title="Magenta Insurance — Support Ιατρικού",
    page_icon="M",
    layout="wide",
)

ASSETS = Path(__file__).parent / "assets"


@st.cache_data
def _svg_raw(path: str) -> str:
    return (ASSETS / path).read_text(encoding="utf-8")


TELEKOM_SVG_INLINE = _svg_raw("telekom.svg")
MAGENTA_SVG_INLINE = _svg_raw("magenta.svg")


# ============================================================
# Design tokens
# ============================================================
NEUTRAL_50 = "#FAFAFA"
NEUTRAL_100 = "#F5F5F5"
NEUTRAL_200 = "#E5E5E5"
NEUTRAL_300 = "#D4D4D4"
NEUTRAL_500 = "#737373"
NEUTRAL_700 = "#404040"
NEUTRAL_900 = "#171717"


def _inject_brand_css() -> None:
    st.markdown(
        f"""
        <style>
        /* --- Hide Streamlit chrome --- */
        [data-testid="stDecoration"] {{ display: none; }}
        header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
        [data-testid="stToolbar"] {{ right: 1rem; }}
        #MainMenu, footer {{ visibility: hidden; }}

        /* --- Base layout --- */
        html, body, [class*="css"] {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", Roboto, sans-serif;
            color: {NEUTRAL_900};
            font-size: 15px;
        }}
        .stApp {{ background: {NEUTRAL_50}; }}
        .block-container {{
            padding-top: 1.6rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }}

        /* --- Typography --- */
        h1 {{
            font-size: 30px !important; font-weight: 600 !important;
            color: {NEUTRAL_900} !important; letter-spacing: -0.3px;
            margin: 0 0 6px 0 !important;
        }}
        h2 {{
            font-size: 20px !important; font-weight: 600 !important;
            color: {NEUTRAL_900} !important; letter-spacing: -0.2px;
            margin: 24px 0 12px 0 !important;
        }}
        h3 {{
            font-size: 14px !important; font-weight: 600 !important;
            color: {NEUTRAL_500} !important; text-transform: uppercase;
            letter-spacing: 0.7px; margin: 20px 0 10px 0 !important;
        }}
        p, label, div {{ font-size: 15px; }}

        /* --- Buttons --- */
        .stButton>button {{
            border-radius: 4px; font-weight: 500; font-size: 14px;
            border: 1px solid {NEUTRAL_300}; background: white; color: {NEUTRAL_900};
            padding: 9px 18px; box-shadow: none;
        }}
        .stButton>button:hover {{
            border-color: {NEUTRAL_500}; background: {NEUTRAL_50};
        }}
        .stButton>button[kind="primary"] {{
            background: {BRAND_PRIMARY}; border-color: {BRAND_PRIMARY}; color: white;
        }}
        .stButton>button[kind="primary"]:hover {{
            background: {BRAND_PRIMARY_DARK}; border-color: {BRAND_PRIMARY_DARK};
        }}

        /* --- Form inputs --- */
        .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {{
            border-radius: 4px; font-size: 14px;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: {BRAND_PRIMARY} !important; box-shadow: 0 0 0 1px {BRAND_PRIMARY};
        }}

        /* --- Sidebar --- */
        [data-testid="stSidebar"] {{
            background: white; border-right: 1px solid {NEUTRAL_200};
            min-width: 280px;
        }}
        [data-testid="stSidebar"] > div:first-child {{
            padding-top: 1rem;
        }}
        [data-testid="stSidebar"] .stRadio label p,
        [data-testid="stSidebar"] .stRadio label {{
            font-size: 17px !important; padding: 4px 0;
            font-weight: 500;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] > label {{
            padding: 10px 4px !important;
        }}

        /* --- Sidebar brand block --- */
        .sb-brand {{
            padding: 4px 6px 22px 6px;
            border-bottom: 1px solid {NEUTRAL_200};
            margin-bottom: 22px;
        }}
        .sb-brand .sb-logo-row {{
            display: flex; align-items: center; gap: 14px; margin-bottom: 14px;
        }}
        .sb-brand .sb-telekom {{
            display: inline-flex; align-items: center; justify-content: center;
            height: 48px; width: 48px;
        }}
        .sb-brand .sb-telekom svg {{ height: 44px; width: auto; }}
        .sb-brand .sb-wordmark {{
            font-size: 22px; font-weight: 700; color: {BRAND_PRIMARY};
            letter-spacing: -0.4px; line-height: 1.1;
        }}
        .sb-brand .sb-portal {{
            font-size: 11px; color: {NEUTRAL_500};
            text-transform: uppercase; letter-spacing: 0.7px;
            font-weight: 600; margin-top: 4px;
        }}
        .sb-brand .sb-tagline {{
            font-size: 13px; color: {NEUTRAL_700};
            line-height: 1.4; margin-top: 2px;
        }}

        .sb-section-label {{
            font-size: 11px; color: {NEUTRAL_500};
            text-transform: uppercase; letter-spacing: 0.7px;
            font-weight: 600; margin: 0 0 10px 6px;
        }}

        /* --- Status & priority pills --- */
        .pill {{
            display: inline-block; padding: 3px 11px; border-radius: 3px;
            font-size: 12px; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.4px; line-height: 1.7;
        }}
        .pill-status-new         {{ background: #DBEAFE; color: #1E40AF; }}
        .pill-status-progress    {{ background: #FEF3C7; color: #92400E; }}
        .pill-status-waiting     {{ background: #FCE7F3; color: #9F1239; }}
        .pill-status-answered    {{ background: #D1FAE5; color: #065F46; }}
        .pill-status-closed      {{ background: {NEUTRAL_100}; color: {NEUTRAL_500}; }}

        .pill-priority-urgent    {{ background: #FEE2E2; color: #991B1B; }}
        .pill-priority-high      {{ background: #FED7AA; color: #9A3412; }}
        .pill-priority-normal    {{ background: {NEUTRAL_100}; color: {NEUTRAL_700}; }}
        .pill-priority-low       {{ background: {NEUTRAL_100}; color: {NEUTRAL_500}; }}

        /* --- Ticket row (inbox) --- */
        .ticket-row {{
            display: grid;
            grid-template-columns: 60px 1fr 160px 130px;
            gap: 18px; align-items: start;
            padding: 16px 20px; background: white;
            border: 1px solid {NEUTRAL_200}; border-radius: 4px;
            margin-bottom: 8px;
        }}
        .ticket-row:hover {{ border-color: {BRAND_PRIMARY}; }}
        .ticket-row .tr-id {{
            font-family: "SF Mono", Menlo, monospace; font-size: 14px;
            color: {NEUTRAL_500}; font-weight: 500; padding-top: 2px;
        }}
        .ticket-row .tr-subject-row {{
            display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
            margin-bottom: 6px;
        }}
        .ticket-row .tr-subject {{
            font-size: 15px; font-weight: 600; color: {NEUTRAL_900};
        }}
        .ticket-row .tr-cat-badge {{
            display: inline-block; padding: 2px 10px;
            background: {NEUTRAL_100}; color: {NEUTRAL_700};
            border-radius: 3px; font-size: 12px; font-weight: 500;
            border: 1px solid {NEUTRAL_200};
        }}
        .ticket-row .tr-meta {{
            font-size: 12px; color: {NEUTRAL_500}; margin-bottom: 6px;
        }}
        .ticket-row .tr-body {{
            font-size: 13px; color: {NEUTRAL_700};
            line-height: 1.5;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .ticket-row .tr-assignee {{ font-size: 13px; color: {NEUTRAL_500}; margin-top: 6px; }}

        .table-header {{
            display: grid;
            grid-template-columns: 60px 1fr 160px 130px;
            gap: 18px; padding: 10px 20px; margin-bottom: 6px;
            font-size: 12px; text-transform: uppercase; letter-spacing: 0.6px;
            color: {NEUTRAL_500}; font-weight: 600;
        }}

        /* --- Metadata table (ticket detail) --- */
        .meta-table {{
            width: 100%; border-collapse: collapse; margin: 0 0 20px 0;
            background: white; border: 1px solid {NEUTRAL_200}; border-radius: 4px;
            overflow: hidden;
        }}
        .meta-table td {{
            padding: 13px 18px; font-size: 15px;
            border-bottom: 1px solid {NEUTRAL_100};
        }}
        .meta-table tr:last-child td {{ border-bottom: none; }}
        .meta-table .label {{
            width: 180px; color: {NEUTRAL_500}; font-weight: 500;
            text-transform: uppercase; font-size: 12px; letter-spacing: 0.6px;
        }}
        .meta-table .value {{ color: {NEUTRAL_900}; }}

        /* --- Section card --- */
        .card {{
            background: white; border: 1px solid {NEUTRAL_200};
            border-radius: 6px; padding: 22px 24px; margin-bottom: 16px;
            font-size: 15px; line-height: 1.6;
        }}
        .card-title {{
            font-size: 12px; text-transform: uppercase; letter-spacing: 0.6px;
            color: {NEUTRAL_500}; font-weight: 600; margin-bottom: 14px;
            padding-bottom: 12px; border-bottom: 1px solid {NEUTRAL_100};
        }}

        /* --- Response entry --- */
        .response-entry {{
            padding: 16px 20px; background: {NEUTRAL_50};
            border-left: 3px solid {NEUTRAL_300};
            margin-bottom: 10px; border-radius: 0 4px 4px 0;
        }}
        .response-entry.ai-source {{ border-left-color: {BRAND_PRIMARY}; }}
        .response-entry .re-meta {{
            font-size: 12px; color: {NEUTRAL_500}; margin-bottom: 8px;
            text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;
        }}
        .response-entry .re-body {{
            font-size: 15px; color: {NEUTRAL_900}; white-space: pre-wrap;
            line-height: 1.6;
        }}

        /* --- Metric card --- */
        [data-testid="stMetric"] {{
            background: white; border: 1px solid {NEUTRAL_200};
            border-radius: 6px; padding: 18px 22px;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 12px !important; text-transform: uppercase;
            letter-spacing: 0.6px; color: {NEUTRAL_500} !important; font-weight: 600 !important;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 34px !important; font-weight: 600 !important; color: {NEUTRAL_900} !important;
        }}

        /* --- Alerts --- */
        .stAlert {{ border-radius: 4px; font-size: 15px; }}

        /* --- Expander --- */
        [data-testid="stExpander"] {{
            border: 1px solid {NEUTRAL_200} !important; border-radius: 6px !important;
            background: white;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


_inject_brand_css()

db.init_db()
db.seed_categories(CATEGORIES)
if "seeded" not in st.session_state:
    seed_if_empty()
    st.session_state.seeded = True


# ============================================================
# Helpers
# ============================================================

STATUS_CLASS = {
    "Νέο": "pill-status-new",
    "Σε εξέλιξη": "pill-status-progress",
    "Αναμένει πληροφορίες": "pill-status-waiting",
    "Απαντήθηκε": "pill-status-answered",
    "Έκλεισε": "pill-status-closed",
}

PRIORITY_CLASS = {
    "Επείγον": "pill-priority-urgent",
    "Υψηλή": "pill-priority-high",
    "Κανονική": "pill-priority-normal",
    "Χαμηλή": "pill-priority-low",
}


def status_pill(status: str) -> str:
    cls = STATUS_CLASS.get(status, "pill-status-closed")
    return f'<span class="pill {cls}">{status}</span>'


def priority_pill(priority: str) -> str:
    cls = PRIORITY_CLASS.get(priority, "pill-priority-normal")
    return f'<span class="pill {cls}">{priority}</span>'


def fmt_date(iso: str) -> str:
    return iso[:16].replace("T", " ")


def _truncate(text: str, n: int = 140) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _html_escape(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:
    st.markdown(
        f"""
        <div class="sb-brand">
            <div class="sb-logo-row">
                <div class="sb-telekom">{TELEKOM_SVG_INLINE}</div>
                <div>
                    <div class="sb-wordmark">Magenta</div>
                    <div class="sb-wordmark" style="color:{NEUTRAL_900}; font-weight:400">Insurance</div>
                </div>
            </div>
            <div class="sb-portal">Support Portal</div>
            <div class="sb-tagline">Ομαδικό Υγείας Εργαζομένων Ομίλου OTE</div>
        </div>
        <div class="sb-section-label">Πλοήγηση</div>
        """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Πλοήγηση",
        ["Αιτήματα", "Καταχώρηση", "Γνωσιακή Βάση", "Πρότυπα Απαντήσεων", "Αναφορές"],
        label_visibility="collapsed",
    )

    if not ai.is_configured():
        st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:12px; color:#B91C1C; padding: 10px 12px; "
            f"background: #FEF2F2; border: 1px solid #FECACA; border-radius: 4px'>"
            f"Δεν έχει οριστεί GEMINI_API_KEY. Οι λειτουργίες AI είναι ανενεργές.</div>",
            unsafe_allow_html=True,
        )


# ============================================================
# INBOX
# ============================================================

def render_inbox():
    # Full-page transition: if a ticket is selected, render only the detail view
    if "selected_ticket" in st.session_state:
        render_ticket_detail(st.session_state.selected_ticket)
        return

    st.markdown("<h1>Αιτήματα</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:14px; color:{NEUTRAL_500}; margin-bottom:20px'>"
        f"Διαχείριση εισερχόμενων αιτημάτων και επικοινωνία με ασφαλισμένους.</div>",
        unsafe_allow_html=True,
    )

    # Filters row
    f1, f2, f3, f4 = st.columns([1.2, 1.5, 1.3, 2])
    f_status = f1.selectbox("Κατάσταση", ["Όλες"] + STATUSES)
    f_category = f2.selectbox("Κατηγορία", ["Όλες"] + get_categories())
    f_assignee = f3.selectbox("Ανάθεση", ["Όλοι"] + ASSIGNEES)
    f_search = f4.text_input("Αναζήτηση")

    tickets = db.list_tickets(
        status=None if f_status == "Όλες" else f_status,
        category=None if f_category == "Όλες" else f_category,
        assignee=None if f_assignee == "Όλοι" else f_assignee,
        search=f_search or None,
    )

    st.markdown(
        f"<div style='font-size:12px; color:{NEUTRAL_500}; margin: 14px 0 8px 0'>"
        f"{len(tickets)} αποτελέσματα</div>",
        unsafe_allow_html=True,
    )

    if not tickets:
        st.info("Δεν βρέθηκαν αιτήματα με αυτά τα κριτήρια.")
        return

    # Table header — same 3-column split so it aligns with ticket rows below.
    hdr_cols = st.columns([7, 1.1, 1.1])
    hdr_cols[0].markdown(
        """
        <div class="table-header">
            <div>ID</div>
            <div>Θέμα &amp; Ερώτηση</div>
            <div>Κατάσταση / Ανάθεση</div>
            <div>Προτεραιότητα</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    hdr_cols[1].markdown("&nbsp;", unsafe_allow_html=True)
    hdr_cols[2].markdown("&nbsp;", unsafe_allow_html=True)

    for t in tickets:
        subject_esc = _html_escape(t["subject"])
        body_esc = _html_escape(_truncate(t["body"], 160))
        cat_esc = _html_escape(t["category"] or "Χωρίς κατηγορία")
        sender_esc = _html_escape(t["sender_name"] or "Άγνωστος")
        assignee_esc = _html_escape(t["assignee"] or "—")

        row_html = f"""
        <div class="ticket-row">
            <div class="tr-id">#{t['id']:04d}</div>
            <div>
                <div class="tr-subject-row">
                    <span class="tr-subject">{subject_esc}</span>
                    <span class="tr-cat-badge">{cat_esc}</span>
                </div>
                <div class="tr-meta">
                    {sender_esc} · {t['channel']} · {fmt_date(t['created_at'])}
                </div>
                <div class="tr-body">{body_esc}</div>
            </div>
            <div>{status_pill(t['status'])}<div class="tr-assignee">{assignee_esc}</div></div>
            <div>{priority_pill(t['priority'])}</div>
        </div>
        """
        cols = st.columns([7, 1.1, 1.1], vertical_alignment="center")
        cols[0].markdown(row_html, unsafe_allow_html=True)
        if cols[1].button("Άνοιγμα", key=f"open_{t['id']}", use_container_width=True, type="primary"):
            st.session_state.selected_ticket = t["id"]
            st.rerun()
        with cols[2].popover("Διαγραφή", use_container_width=True):
            st.markdown(
                f"<div style='font-size:13px; color:{NEUTRAL_700}; margin-bottom:8px'>"
                f"Διαγραφή αιτήματος <strong>#{t['id']:04d}</strong>;<br>"
                f"Η ενέργεια δεν αναιρείται.</div>",
                unsafe_allow_html=True,
            )
            if st.button("Ναι, διαγραφή", type="primary", key=f"confirmdel_{t['id']}"):
                db.delete_ticket(t["id"])
                st.session_state["_toast"] = ("Το αίτημα διαγράφηκε", "🗑️")
                st.rerun()


def render_ticket_detail(ticket_id: int):
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        st.session_state.pop("selected_ticket", None)
        st.rerun()
        return

    # Breadcrumb + back button at very top
    back_col, _ = st.columns([2, 6])
    if back_col.button("← Πίσω στα αιτήματα", key="back_to_inbox", use_container_width=True):
        st.session_state.pop("selected_ticket", None)
        st.rerun()

    st.markdown(
        f"<div style='font-size:13px; color:{NEUTRAL_500}; "
        f"text-transform:uppercase; letter-spacing:0.6px; font-weight:600; "
        f"margin: 18px 0 6px 0'>Αίτημα υποστήριξης</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<h1 style='margin: 0 0 6px 0'>#{ticket['id']:04d} — {ticket['subject']}</h1>"
        f"<div style='margin: 10px 0 20px 0'>"
        f"{status_pill(ticket['status'])}&nbsp;&nbsp;{priority_pill(ticket['priority'])}"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 18px'></div>", unsafe_allow_html=True)

    # Metadata table
    st.markdown(
        f"""
        <table class="meta-table">
            <tr><td class="label">Αποστολέας</td><td class="value">{ticket['sender_name'] or '—'}</td></tr>
            <tr><td class="label">Email</td><td class="value">{ticket['sender_email'] or '—'}</td></tr>
            <tr><td class="label">Τηλέφωνο</td><td class="value">{ticket['sender_phone'] or '—'}</td></tr>
            <tr><td class="label">Κανάλι</td><td class="value">{ticket['channel']}</td></tr>
            <tr><td class="label">Κατηγορία</td><td class="value">{ticket['category'] or '—'}</td></tr>
            <tr><td class="label">Ανατέθηκε σε</td><td class="value">{ticket['assignee'] or '—'}</td></tr>
            <tr><td class="label">Ημερομηνία</td><td class="value">{fmt_date(ticket['created_at'])}</td></tr>
        </table>
        """,
        unsafe_allow_html=True,
    )

    # Request body
    st.markdown("<h3>Κείμενο αιτήματος</h3>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='card' style='white-space:pre-wrap; font-size:13px; line-height:1.5'>"
        f"{ticket['body']}</div>",
        unsafe_allow_html=True,
    )

    if ticket["ai_summary"]:
        st.markdown(
            f"<div style='font-size:12px; color:{NEUTRAL_500}; padding: 4px 12px; "
            f"border-left: 2px solid {BRAND_PRIMARY}; margin-bottom: 14px'>"
            f"<strong style='color:{BRAND_PRIMARY_DARK}'>AI περίληψη:</strong> {ticket['ai_summary']}</div>",
            unsafe_allow_html=True,
        )

    # Similar tickets — persisted at categorization time
    try:
        similar_raw = ticket["similar_ticket_ids"]
    except (KeyError, IndexError):
        similar_raw = None
    if similar_raw:
        import json as _json
        try:
            similar_ids = _json.loads(similar_raw)
        except (ValueError, TypeError):
            similar_ids = []
        if similar_ids:
            st.markdown("<h3>Παρόμοια αιτήματα</h3>", unsafe_allow_html=True)
            items = []
            for sid in similar_ids:
                sim = db.get_ticket(sid)
                if sim:
                    items.append(
                        f"<div style='padding: 8px 12px; border-left: 3px solid {BRAND_PRIMARY}; "
                        f"background: {NEUTRAL_50}; margin-bottom: 6px; border-radius: 0 4px 4px 0'>"
                        f"<div style='font-family: SF Mono, Menlo, monospace; font-size: 12px; "
                        f"color: {NEUTRAL_500}'>#{sim['id']:04d}</div>"
                        f"<div style='font-size: 14px; font-weight: 500; margin-top: 2px'>{sim['subject']}</div>"
                        f"<div style='font-size: 12px; color: {NEUTRAL_500}; margin-top: 3px'>"
                        f"{sim['category'] or '—'} · {sim['status']}</div>"
                        f"</div>"
                    )
            if items:
                st.markdown("".join(items), unsafe_allow_html=True)

    # --- Metadata edit ---
    with st.expander("Επεξεργασία στοιχείων & ανάθεση", expanded=False):
        c = st.columns(4)
        new_status = c[0].selectbox(
            "Κατάσταση", STATUSES,
            index=STATUSES.index(ticket["status"]) if ticket["status"] in STATUSES else 0,
            key=f"st_{ticket_id}",
        )
        cats = get_categories()
        new_category = c[1].selectbox(
            "Κατηγορία", cats,
            index=cats.index(ticket["category"]) if ticket["category"] in cats else 0,
            key=f"cat_{ticket_id}",
        )
        new_priority = c[2].selectbox(
            "Προτεραιότητα", PRIORITIES,
            index=PRIORITIES.index(ticket["priority"]) if ticket["priority"] in PRIORITIES else 1,
            key=f"pr_{ticket_id}",
        )
        current_assignee = ticket["assignee"] or "— Χωρίς ανάθεση —"
        new_assignee = c[3].selectbox(
            "Ανάθεση σε", ASSIGNEES,
            index=ASSIGNEES.index(current_assignee) if current_assignee in ASSIGNEES else len(ASSIGNEES) - 1,
            key=f"as_{ticket_id}",
        )
        if st.button("Αποθήκευση", key=f"save_meta_{ticket_id}", type="primary"):
            db.update_ticket(
                ticket_id, status=new_status, category=new_category,
                priority=new_priority, assignee=new_assignee,
            )
            st.session_state["_toast"] = ("Οι αλλαγές του αιτήματος αποθηκεύτηκαν", "✅")
            st.rerun()

    # --- Response history ---
    responses = db.list_responses(ticket_id)
    if responses:
        st.markdown("<h3>Ιστορικό επικοινωνίας</h3>", unsafe_allow_html=True)
        for r in responses:
            source_class = "ai-source" if r["was_ai_draft"] else ""
            source_label = "AI DRAFT" if r["was_ai_draft"] and not r["edited_from_draft"] else \
                          ("AI DRAFT (επεξεργασμένο)" if r["edited_from_draft"] else "ΧΕΙΡΟΚΙΝΗΤΟ")
            att_name = r["attachment_name"] if "attachment_name" in r.keys() else None
            att_path = r["attachment_path"] if "attachment_path" in r.keys() else None
            st.markdown(
                f"<div class='response-entry {source_class}'>"
                f"<div class='re-meta'>{r['author']} · {fmt_date(r['created_at'])} · {source_label}</div>"
                f"<div class='re-body'>{r['content']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if att_name and att_path and Path(att_path).exists():
                with open(att_path, "rb") as fh:
                    st.download_button(
                        label=f"📎 {att_name}",
                        data=fh.read(),
                        file_name=att_name,
                        key=f"dl_{r['id']}",
                    )

    # --- Draft response ---
    st.markdown("<h3>Νέα απάντηση</h3>", unsafe_allow_html=True)

    # Streamlit gotcha: text_area with `key` ignores `value` on reruns.
    # We write draft directly into the widget's own state key `ta_{id}`.
    ta_key = f"ta_{ticket_id}"
    orig_draft_key = f"orig_draft_{ticket_id}"
    used_kb_key = f"used_kb_{ticket_id}"
    sug_tpl_key = f"suggested_tpl_{ticket_id}"
    sug_reason_key = f"suggested_reason_{ticket_id}"
    auto_ran_key = f"auto_ran_{ticket_id}"

    # ----- Auto template matching on first open -----
    # Trigger only if:
    #   - No prior responses (ticket unanswered)
    #   - No draft already loaded in session
    #   - Haven't already tried auto-matching for this ticket
    #   - AI configured
    if (
        not responses
        and ta_key not in st.session_state
        and auto_ran_key not in st.session_state
        and ai.is_configured()
    ):
        # If there's already a stored suggestion in the DB, reuse it (avoid re-call)
        stored_id = None
        try:
            stored_id = ticket["suggested_template_id"]
        except (KeyError, IndexError):
            stored_id = None

        matched_template = False
        if stored_id:
            tpl = db.get_template(stored_id)
            if tpl:
                st.session_state[ta_key] = tpl["content"]
                st.session_state[sug_tpl_key] = stored_id
                matched_template = True
        else:
            with st.spinner("Ο AI αναγνωρίζει τυχόν πρότυπο που ταιριάζει..."):
                try:
                    sug = ai.suggest_template(
                        ticket["subject"],
                        ticket["body"],
                        [dict(t) for t in db.list_templates()],
                    )
                except RuntimeError as e:
                    sug = None
                    st.warning(f"AI matching δεν διαθέσιμο: {e}")
            if sug and sug.template_id:
                tpl = db.get_template(sug.template_id)
                if tpl:
                    st.session_state[ta_key] = tpl["content"]
                    st.session_state[sug_tpl_key] = sug.template_id
                    st.session_state[sug_reason_key] = sug.reason
                    db.update_ticket(ticket_id, suggested_template_id=sug.template_id)
                    matched_template = True

        # Fallback: if no template matched, auto-generate an AI draft so the
        # agent sees a pre-filled answer and doesn't need to click "Δημιουργία με AI".
        if not matched_template:
            with st.spinner("Σύνταξη αυτόματου draft από AI..."):
                try:
                    result = ai.draft_response(
                        sender_name=ticket["sender_name"] or "",
                        subject=ticket["subject"],
                        body=ticket["body"],
                        kb_entries=[dict(e) for e in db.list_kb_entries()],
                        prior_responses=[],
                    )
                except RuntimeError as e:
                    result = None
                    st.warning(f"AI draft δεν διαθέσιμο: {e}")
            if result and result.draft:
                st.session_state[ta_key] = result.draft
                st.session_state[orig_draft_key] = result.draft
                st.session_state[used_kb_key] = result.used_kb_ids

        st.session_state[auto_ran_key] = True
        st.rerun()

    # Show a callout when a suggested template is loaded
    if sug_tpl_key in st.session_state:
        sug_id = st.session_state[sug_tpl_key]
        sug_tpl = db.get_template(sug_id)
        if sug_tpl:
            reason = st.session_state.get(sug_reason_key, "")
            st.markdown(
                f"<div style='padding: 12px 16px; background: #FDF4F9; "
                f"border-left: 4px solid {BRAND_PRIMARY}; border-radius: 4px; "
                f"margin-bottom: 12px'>"
                f"<div style='font-size: 12px; color: {BRAND_PRIMARY_DARK}; "
                f"text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; "
                f"margin-bottom: 4px'>🤖 Πρότυπο που ταιριάζει (auto-matched)</div>"
                f"<div style='font-size: 15px; color: {NEUTRAL_900}; font-weight: 500'>"
                f"{sug_tpl['title']}</div>"
                + (f"<div style='font-size: 13px; color: {NEUTRAL_500}; margin-top: 4px'>"
                   f"{reason}</div>" if reason else "")
                + "<div style='font-size: 12px; color: {NEUTRAL_500}; margin-top: 6px'>"
                "Το κείμενο έχει προ-συμπληρωθεί. Μπορείς να το επεξεργαστείς, να το "
                "αποστείλεις όπως είναι, ή να ζητήσεις νέο draft από το AI."
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )

    ai_col1, ai_col2 = st.columns([1.5, 4], vertical_alignment="center")
    if ai_col1.button(
        "Δημιουργία με AI",
        disabled=not ai.is_configured(),
        key=f"gen_{ticket_id}",
        use_container_width=True,
    ):
        with st.spinner("Σύνταξη draft..."):
            kb = [dict(e) for e in db.list_kb_entries()]
            try:
                result = ai.draft_response(
                    sender_name=ticket["sender_name"] or "",
                    subject=ticket["subject"],
                    body=ticket["body"],
                    kb_entries=kb,
                    prior_responses=[dict(r) for r in responses],
                )
            except RuntimeError as e:
                st.error(str(e))
                result = None
        if result:
            st.session_state[ta_key] = result.draft
            st.session_state[orig_draft_key] = result.draft
            st.session_state[used_kb_key] = result.used_kb_ids
            st.rerun()

    if used_kb_key in st.session_state and st.session_state[used_kb_key]:
        ai_col2.markdown(
            f"<div style='font-size:11px; color:{NEUTRAL_500}; padding: 8px 12px'>"
            f"Βασίστηκε σε KB entries: {', '.join(f'#{i}' for i in st.session_state[used_kb_key])}</div>",
            unsafe_allow_html=True,
        )

    draft_text = st.text_area(
        "Κείμενο απάντησης",
        height=260,
        key=ta_key,
        label_visibility="collapsed",
    )

    uploaded_file = st.file_uploader(
        "Επισύναψη αρχείου (προαιρετικό)",
        type=None,
        key=f"upload_{ticket_id}",
        accept_multiple_files=False,
    )

    send_c = st.columns([1.5, 2.5, 1.5, 2.5], vertical_alignment="bottom")
    author = send_c[0].selectbox("Συντάκτης", ASSIGNEES[:-1], key=f"auth_{ticket_id}")
    mark_answered = send_c[1].checkbox(
        "Ενημέρωση κατάστασης σε 'Απαντήθηκε'", value=True, key=f"mark_{ticket_id}"
    )
    if send_c[2].button("Καταχώρηση", type="primary", key=f"send_{ticket_id}", use_container_width=True):
        if not draft_text.strip():
            st.error("Το κείμενο απάντησης είναι κενό.")
        else:
            was_draft = bool(st.session_state.get(orig_draft_key))
            edited = was_draft and draft_text.strip() != st.session_state.get(orig_draft_key, "").strip()

            attach_path: str | None = None
            attach_name: str | None = None
            if uploaded_file is not None:
                from datetime import datetime
                import re as _re
                attach_dir = Path(__file__).parent / "data" / "attachments"
                attach_dir.mkdir(parents=True, exist_ok=True)
                safe_name = _re.sub(r"[^\w\.\-]", "_", uploaded_file.name)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stored_name = f"t{ticket_id}_{stamp}_{safe_name}"
                stored_path = attach_dir / stored_name
                stored_path.write_bytes(uploaded_file.getbuffer())
                attach_path = str(stored_path)
                attach_name = uploaded_file.name

            db.add_response(
                ticket_id, author=author, content=draft_text.strip(),
                was_ai_draft=was_draft, edited_from_draft=edited,
                attachment_path=attach_path, attachment_name=attach_name,
            )
            if mark_answered:
                db.update_ticket(ticket_id, status="Απαντήθηκε")
            for k in (ta_key, used_kb_key, orig_draft_key):
                st.session_state.pop(k, None)
            st.session_state["_toast"] = ("Η απάντηση καταχωρήθηκε", "📧")
            st.rerun()


# ============================================================
# NEW TICKET
# ============================================================

def render_new_ticket():
    st.markdown("<h1>Καταχώρηση αιτήματος</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:13px; color:{NEUTRAL_500}; margin-bottom:20px'>"
        f"Καταχώρηση αιτήματος από τηλεφωνική επικοινωνία ή άλλο κανάλι εκτός email.</div>",
        unsafe_allow_html=True,
    )

    with st.form("new_ticket", clear_on_submit=False):
        st.markdown("<h3>Στοιχεία επικοινωνίας</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        channel = c1.selectbox("Κανάλι", CHANNELS)
        priority = c2.selectbox("Προτεραιότητα", PRIORITIES, index=1)

        c3, c4, c5 = st.columns(3)
        sender_name = c3.text_input("Ονοματεπώνυμο")
        sender_email = c4.text_input("Email")
        sender_phone = c5.text_input("Τηλέφωνο")

        st.markdown("<h3>Περιεχόμενο</h3>", unsafe_allow_html=True)
        subject = st.text_input("Θέμα", placeholder="π.χ. Ερώτηση για νοσοκομεία δικτύου")
        body = st.text_area("Περιγραφή αιτήματος", height=180,
                            placeholder="Αναλυτική περιγραφή του αιτήματος του ασφαλισμένου")

        st.markdown("<h3>Ανάθεση</h3>", unsafe_allow_html=True)
        c6, c7 = st.columns([1, 2], vertical_alignment="bottom")
        assignee = c6.selectbox("Υπεύθυνος", ASSIGNEES, index=len(ASSIGNEES) - 1)
        run_ai = c7.checkbox(
            "Αυτόματη κατηγοριοποίηση από AI",
            value=ai.is_configured(),
            disabled=not ai.is_configured(),
        )

        submitted = st.form_submit_button("Καταχώρηση αιτήματος", type="primary")

    if submitted:
        if not subject.strip() or not body.strip():
            st.error("Το θέμα και το περιεχόμενο είναι υποχρεωτικά.")
            return

        category = None
        ai_summary = None
        similar_ids: list[int] = []
        final_priority = priority
        if run_ai:
            with st.spinner("Ανάλυση αιτήματος (ταξινόμηση + έλεγχος ομοιότητας)..."):
                try:
                    cat = ai.categorize_ticket(
                        subject.strip(),
                        body.strip(),
                        existing_categories=get_categories(),
                        recent_tickets=[dict(t) for t in db.recent_tickets(30)],
                    )
                except RuntimeError as e:
                    st.error(str(e))
                    cat = None
            if cat:
                category = cat.category
                ai_summary = cat.summary
                final_priority = cat.suggested_priority
                similar_ids = cat.similar_ticket_ids

                # Auto-persist any newly discovered category
                if cat.is_new_category:
                    if db.add_category(cat.category):
                        st.success(
                            f"Δημιουργήθηκε νέα κατηγορία: **{cat.category}** "
                            f"(αυτόματα από AI — δεν υπήρχε κατάλληλη υπάρχουσα)."
                        )

                cat_badge = "🆕 ΝΕΑ · " if cat.is_new_category else ""
                st.info(
                    f"**Κατηγορία**: {cat_badge}{cat.category}  \n"
                    f"**Προτεινόμενη προτεραιότητα**: {cat.suggested_priority}  \n"
                    f"**Περίληψη**: {cat.summary}"
                )

                if similar_ids:
                    lines = []
                    for sid in similar_ids:
                        st_t = db.get_ticket(sid)
                        if st_t:
                            lines.append(f"- **#{sid:04d}** — {st_t['subject']} _({st_t['category'] or '—'})_")
                    if lines:
                        st.warning(
                            "**Παρόμοια προηγούμενα αιτήματα** (ίδια ουσία, διαφορετική διατύπωση):\n\n"
                            + "\n".join(lines)
                        )

        ticket_id = db.create_ticket(
            channel=channel, sender_name=sender_name.strip(),
            sender_email=sender_email.strip(), sender_phone=sender_phone.strip(),
            subject=subject.strip(), body=body.strip(),
            category=category, ai_summary=ai_summary,
            priority=final_priority, assignee=assignee,
        )
        # Persist similar_ticket_ids as JSON string on the new ticket
        if similar_ids:
            import json as _json
            db.update_ticket(ticket_id, similar_ticket_ids=_json.dumps(similar_ids))
        st.success(f"Το αίτημα #{ticket_id:04d} καταχωρήθηκε επιτυχώς.")


# ============================================================
# KNOWLEDGE BASE
# ============================================================

def render_kb():
    st.markdown("<h1>Γνωσιακή Βάση</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:13px; color:{NEUTRAL_500}; margin-bottom:20px'>"
        f"Καταχωρήσεις που τροφοδοτούν τον AI βοηθό για τη σύνταξη απαντήσεων.</div>",
        unsafe_allow_html=True,
    )

    kb_cats = get_categories()
    with st.expander("Προσθήκη νέας καταχώρησης", expanded=False):
        with st.form("new_kb", clear_on_submit=True):
            c1, c2 = st.columns([1, 2])
            new_cat = c1.selectbox("Κατηγορία", kb_cats)
            new_q = c2.text_input("Ερώτηση")
            new_a = st.text_area("Απάντηση", height=160)
            if st.form_submit_button("Προσθήκη", type="primary"):
                if new_q.strip() and new_a.strip():
                    db.create_kb_entry(new_cat, new_q.strip(), new_a.strip())
                    st.session_state["_toast"] = ("Νέα καταχώρηση προστέθηκε", "✅")
                    st.rerun()
                else:
                    st.error("Ερώτηση και απάντηση είναι υποχρεωτικά.")

    st.markdown("<div style='height: 14px'></div>", unsafe_allow_html=True)
    f_cat = st.selectbox("Φίλτρο κατηγορίας", ["Όλες"] + kb_cats, key="kb_filter")
    entries = db.list_kb_entries(None if f_cat == "Όλες" else f_cat)

    st.markdown(
        f"<div style='font-size:12px; color:{NEUTRAL_500}; margin: 14px 0 10px 0'>"
        f"{len(entries)} καταχωρήσεις</div>",
        unsafe_allow_html=True,
    )

    for e in entries:
        with st.expander(f"[{e['category']}]  {e['question']}", expanded=False):
            edit_q = st.text_input("Ερώτηση", value=e["question"], key=f"q_{e['id']}")
            edit_a = st.text_area("Απάντηση", value=e["answer"], height=140, key=f"a_{e['id']}")
            edit_cat = st.selectbox(
                "Κατηγορία", kb_cats,
                index=kb_cats.index(e["category"]) if e["category"] in kb_cats else 0,
                key=f"c_{e['id']}",
            )
            cols = st.columns([1, 1, 6], vertical_alignment="bottom")
            if cols[0].button("Αποθήκευση", key=f"save_{e['id']}", type="primary"):
                db.update_kb_entry(e["id"], category=edit_cat, question=edit_q, answer=edit_a)
                st.session_state["_toast"] = ("Οι αλλαγές αποθηκεύτηκαν", "✅")
                st.rerun()
            if cols[1].button("Διαγραφή", key=f"del_{e['id']}"):
                db.delete_kb_entry(e["id"])
                st.session_state["_toast"] = ("Η καταχώρηση διαγράφηκε", "🗑️")
                st.rerun()


# ============================================================
# TEMPLATES
# ============================================================

def render_templates():
    st.markdown("<h1>Πρότυπα Απαντήσεων</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:14px; color:{NEUTRAL_500}; margin-bottom:20px'>"
        f"Έτοιμα κείμενα για γρήγορη εισαγωγή στις απαντήσεις. Επιλέγονται από dropdown "
        f"στο ticket detail.</div>",
        unsafe_allow_html=True,
    )

    all_categories = sorted(set(
        [t["category"] for t in db.list_templates() if t["category"]]
        + ["Γενικά", "Αποζημιώσεις", "Δίκτυο", "Ένταξη μελών", "Παροχές"]
    ))

    with st.expander("Προσθήκη νέου προτύπου", expanded=False):
        with st.form("new_tpl", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            new_title = c1.text_input("Τίτλος", placeholder="π.χ. Επιβεβαίωση παραλαβής")
            new_tpl_cat = c2.selectbox("Κατηγορία", all_categories)
            new_content = st.text_area("Περιεχόμενο", height=220,
                                        placeholder="Το κείμενο της απάντησης...")
            if st.form_submit_button("Προσθήκη", type="primary"):
                if new_title.strip() and new_content.strip():
                    db.create_template(new_title.strip(), new_tpl_cat, new_content.strip())
                    st.session_state["_toast"] = ("Νέο πρότυπο προστέθηκε", "✅")
                    st.rerun()
                else:
                    st.error("Τίτλος και περιεχόμενο είναι υποχρεωτικά.")

    st.markdown("<div style='height: 14px'></div>", unsafe_allow_html=True)

    f_tpl_cat = st.selectbox(
        "Φίλτρο κατηγορίας",
        ["Όλες"] + all_categories,
        key="tpl_filter",
    )
    templates = db.list_templates(None if f_tpl_cat == "Όλες" else f_tpl_cat)

    st.markdown(
        f"<div style='font-size:12px; color:{NEUTRAL_500}; margin: 14px 0 10px 0'>"
        f"{len(templates)} πρότυπα</div>",
        unsafe_allow_html=True,
    )

    for t in templates:
        with st.expander(f"[{t['category'] or 'Γενικά'}]  {t['title']}", expanded=False):
            edit_title = st.text_input("Τίτλος", value=t["title"], key=f"tt_{t['id']}")
            edit_tpl_cat = st.selectbox(
                "Κατηγορία", all_categories,
                index=all_categories.index(t["category"]) if t["category"] in all_categories else 0,
                key=f"tc_{t['id']}",
            )
            edit_content = st.text_area(
                "Περιεχόμενο", value=t["content"], height=220, key=f"tp_{t['id']}",
            )
            cols = st.columns([1, 1, 6], vertical_alignment="bottom")
            if cols[0].button("Αποθήκευση", key=f"tsave_{t['id']}", type="primary"):
                db.update_template(t["id"], title=edit_title, category=edit_tpl_cat, content=edit_content)
                st.session_state["_toast"] = ("Οι αλλαγές αποθηκεύτηκαν", "✅")
                st.rerun()
            with cols[1].popover("Διαγραφή"):
                st.markdown(
                    f"<div style='font-size:13px'>Διαγραφή προτύπου <strong>{t['title']}</strong>;</div>",
                    unsafe_allow_html=True,
                )
                if st.button("Ναι, διαγραφή", type="primary", key=f"tdel_{t['id']}"):
                    db.delete_template(t["id"])
                    st.session_state["_toast"] = ("Το πρότυπο διαγράφηκε", "🗑️")
                    st.rerun()


# ============================================================
# REPORTS
# ============================================================

def _hbar_chart(data: list[tuple[str, int]]) -> str:
    """Render a static horizontal bar chart as HTML. Zero animation, zero jitter."""
    if not data:
        return f"<div style='color:{NEUTRAL_500}; font-size:13px'>—</div>"
    max_val = max(v for _, v in data) or 1
    rows = []
    for label, val in data:
        pct = (val / max_val) * 100
        rows.append(
            f"<div style='display:grid; grid-template-columns: 200px 1fr 40px; "
            f"gap: 14px; align-items: center; padding: 8px 0; "
            f"border-bottom: 1px solid {NEUTRAL_100}'>"
            f"<div style='font-size:14px; color:{NEUTRAL_900}; "
            f"overflow:hidden; text-overflow:ellipsis; white-space:nowrap'>{label}</div>"
            f"<div style='background: {NEUTRAL_100}; height: 22px; border-radius: 3px; "
            f"overflow: hidden'>"
            f"<div style='background: {BRAND_PRIMARY}; height: 100%; width: {pct:.1f}%; "
            f"border-radius: 3px'></div>"
            f"</div>"
            f"<div style='font-size:14px; font-weight:600; color:{NEUTRAL_900}; "
            f"text-align:right; font-variant-numeric: tabular-nums'>{val}</div>"
            f"</div>"
        )
    return (
        f"<div style='background:white; border:1px solid {NEUTRAL_200}; "
        f"border-radius:6px; padding: 4px 20px'>"
        + "".join(rows) + "</div>"
    )


def render_stats():
    st.markdown("<h1>Αναφορές</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:14px; color:{NEUTRAL_500}; margin-bottom:20px'>"
        f"Στατιστικά αιτημάτων και απόδοση του AI βοηθού.</div>",
        unsafe_allow_html=True,
    )

    s = db.stats()

    m = st.columns(4)
    m[0].metric("Σύνολο αιτημάτων", s["total"])

    st.markdown("<div style='height: 30px'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<h3>Κατανομή ανά κατάσταση</h3>", unsafe_allow_html=True)
        st.markdown(
            _hbar_chart([(r["status"], r["n"]) for r in s["by_status"]]),
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown("<h3>Κατανομή ανά υπεύθυνο</h3>", unsafe_allow_html=True)
        st.markdown(
            _hbar_chart([(r["assignee"], r["n"]) for r in s["by_assignee"]]),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    st.markdown("<h3>Κορυφαίες κατηγορίες αιτημάτων</h3>", unsafe_allow_html=True)
    st.markdown(
        _hbar_chart([(r["category"], r["n"]) for r in s["by_category"][:10]]),
        unsafe_allow_html=True,
    )


# ============================================================
# ROUTING
# ============================================================

# Toast from previous action — survives st.rerun()
if "_toast" in st.session_state:
    _msg, _icon = st.session_state.pop("_toast")
    st.toast(_msg, icon=_icon)

if page != "Αιτήματα":
    st.session_state.pop("selected_ticket", None)

if page == "Αιτήματα":
    render_inbox()
elif page == "Καταχώρηση":
    render_new_ticket()
elif page == "Γνωσιακή Βάση":
    render_kb()
elif page == "Πρότυπα Απαντήσεων":
    render_templates()
elif page == "Αναφορές":
    render_stats()
