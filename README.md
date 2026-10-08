# Support Iatriko — Magenta Insurance

Streamlit dashboard για το τμήμα υποστήριξης του Ομαδικού Προγράμματος Υγείας του Ομίλου ΟΤΕ.

AI-powered (Google Gemini) ticket categorization, template matching και σύνταξη απαντήσεων βάσει γνωσιακής βάσης (RAG).

## Features
- 📥 Καταχώρηση αιτημάτων με αυτόματη κατηγοριοποίηση
- 🤖 AI drafts βάσει γνωσιακής βάσης (118 KB entries)
- 📋 44 έτοιμα templates για γρήγορες απαντήσεις
- 🏥 3 ξεχωριστά συμβόλαια (ΟΤΕ 3089, EVALUE 2848, PAN-NET GREECE)
- 🚫 Scope-aware: αναγνωρίζει out-of-scope ερωτήσεις
- 📎 File attachments στις απαντήσεις

## Local setup
```bash
cp .env.example .env
# edit .env → paste real GOOGLE_API_KEY
./run.sh
# → http://localhost:8510
```

## Deployment (Streamlit Cloud)
1. Fork/push το repo
2. Στο share.streamlit.io → New app → select repo → main branch → `app.py`
3. Settings → Secrets:
   ```toml
   GOOGLE_API_KEY = "your-key-here"
   ```
