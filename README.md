# AI Risk Manager

**An AI-powered payment risk operations platform** that detects suspicious transactions, explains why they are risky, investigates them using an AI agent, and recommends the appropriate action.

> An experimental AI-powered payment risk management prototype inspired by modern payment infrastructure. Uses synthetic data — not an actual Razorpay internal system.

## Architecture

```
Transaction → Feature Engineering → ML Model + Rule Engine → Risk Score
                                              ↓
                                    AI investigation → LangGraph AI Investigator (Groq + Tools)
                                              ↓
                                    Recommended Action → Human Approval
```

**Hybrid system:** ML (XGBoost) + Deterministic Rules + Agentic AI (LangGraph + Groq)

## Track 02 Scope and Safety

AI Risk Manager targets one defensive loss class: fraudulent payment transactions that can create direct merchant loss and downstream chargebacks. It does not provide offensive fraud capabilities. Investigation tools are allowlisted and read-only, recommendations are audited, and transaction blocking requires human approval.

## Honest Model Evaluation

Training uses a chronological 70/15/15 train, validation, and held-out test split. Demo-only `DEMOHR` transactions are excluded from model development. The operating threshold is selected on validation data only, then precision, recall, false positives, false negatives, alert rate, PR-AUC, and ROC-AUC are reported on the untouched test set.

Threshold selection includes an explicit illustrative merchant-cost model:

- False positive: ₹200 for review and legitimate-payment friction.
- False negative: ₹5,500 for fraud loss and chargeback handling.

These are scenario assumptions, not measured merchant financials. Adjust the constants in `backend/scripts/train_model.py` for a real merchant's economics. Results and threshold comparisons are saved to `backend/artifacts/metrics.json`.

## Quick Start

See **[SETUP.md](./SETUP.md)** for full instructions including Kaggle dataset setup.

For production deployment with Render, PostgreSQL, and Vercel, see **[DEPLOYMENT.md](./DEPLOYMENT.md)**.

### Windows (automated)

```powershell
cd backend
.\scripts\setup.ps1
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

### Manual

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # Add GROQ_API_KEY (optional)

# Generate sample data (or place bank_fraud.csv in backend/data/)
python scripts/generate_sample_data.py

# Train ML model
python scripts/train_model.py

# Load data into SQLite + pre-analyze sample
python scripts/load_data.py

# Start API
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Demo Mode

Click **"View Highest Risk Transaction"** in the header to jump directly to the highest-risk analyzed transaction for live demos.

## Risk Operations Workflow

- **Evaluation:** held-out precision, recall, confusion matrix, threshold trade-offs, and illustrative merchant cost.
- **Alert Queue:** HIGH and CRITICAL payments prioritized for analyst review.
- **Behavioral Evidence:** each payment is compared only with the customer's earlier activity, including amount, location, device type, category, and time.
- **Verification Timeline:** simulated OTP, registered-device, or callback verification is persisted alongside model, agent, and analyst events.
- **Human Control:** the AI can recommend a block, but final blocking remains analyst-controlled.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/stats` | Dashboard KPIs |
| GET | `/transactions` | Paginated transaction list |
| GET | `/transactions/{id}` | Transaction detail |
| POST | `/risk/analyze` | Run risk analysis |
| POST | `/investigations/{id}` | Trigger AI investigation |
| POST | `/actions/{id}` | Apply demo action |
| GET | `/analytics` | Analytics data |
| GET | `/transactions/{id}/behavior` | Customer behavioral evidence |
| GET | `/cases/{id}/timeline` | Auditable case timeline |
| POST | `/verifications/{id}` | Request defensive verification |
| PATCH | `/verifications/{id}` | Resolve a verification |

## Project Structure

```
backend/
  app/
    agent/          # LangGraph/Groq AI investigator + tools
    services/       # ML, rules, risk engine
    main.py         # FastAPI app
  scripts/          # Data generation, training, loading
  artifacts/        # Trained model + metrics
  data/             # CSV dataset

frontend/
  src/app/          # Next.js pages
  src/components/   # UI components
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key (optional — fallback works without it) |
| `NEXT_PUBLIC_API_URL` | Backend URL (default: http://localhost:8000) |

## License

MIT — Hackathon demo project
