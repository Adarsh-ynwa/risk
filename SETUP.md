# AI Risk Manager — Setup & Run Guide

**An experimental AI-powered payment risk management prototype inspired by modern payment infrastructure.** Uses synthetic or Kaggle data — not an actual Razorpay internal system.

## Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Groq API key for live AI agent

---

## Option A: Quick start with generated sample data

### 1. Backend setup (one-time)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env and add GROQ_API_KEY=your_key (optional)

python scripts/generate_sample_data.py
python scripts/train_model.py
python scripts/load_data.py
```

The training step excludes demo-only records, selects a cost-sensitive threshold on a chronological validation set, and writes untouched held-out metrics to `artifacts/metrics.json`.

### 2. Start backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Verify: http://localhost:8000/health — should show `"model_loaded": true`

### 3. Frontend setup

```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Open: http://localhost:3000

---

## Option B: Use your Kaggle dataset

1. Download **Bank Transaction Fraud Detection Dataset** from Kaggle
2. Place the CSV at:

```
backend/data/bank_fraud.csv
```

3. Run training + load (skip `generate_sample_data.py`):

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python scripts/inspect_dataset.py
python scripts/train_model.py
python scripts/load_data.py --force-reload
```

`train_model.py` uses up to 200,000 rows by default.  
`load_data.py` loads up to 150,000 rows into SQLite (configurable via `MAX_TRANSACTIONS_LOAD` in `.env`).

---

## Demo flow (for judges)

1. Click **View Highest Risk Transaction** in the header
2. Review **Risk Panel** (ML score + rule score + triggered rules)
3. Click **Run AI Investigation** (uses LangGraph/Groq if configured, else rule-based fallback)
4. See **Agent Tool Calls** panel showing evidence gathering
5. Apply a demo action: **HOLD**, **BLOCK**, etc.
6. Explore **Dashboard** and **Analytics** charts

---

## Environment variables

| Variable | Where | Description |
|----------|-------|-------------|
| `GROQ_API_KEY` | `backend/.env` | Groq API key (optional) |
| `MAX_TRANSACTIONS_LOAD` | `backend/.env` | Max rows loaded into SQLite (default 150000) |
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | Backend URL (default http://localhost:8000) |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `model_loaded: false` | Run `python scripts/train_model.py` |
| Empty dashboard | Run `python scripts/load_data.py` |
| Backend unavailable in UI | Start uvicorn on port 8000 |
| Investigation uses fallback | Add `GROQ_API_KEY` to `backend/.env` |
| Dataset not found | Place CSV at `backend/data/bank_fraud.csv` or run `generate_sample_data.py` |

---

## Architecture

```
Transaction → Feature Engineering → XGBoost + Rule Engine → Risk Score
                                              ↓
                                    AI investigation → LangGraph/Groq Agent + Tools
                                              ↓
                                    Recommended Action → Human Approval
```

Hybrid system: **ML + Deterministic Rules + Agentic AI**
