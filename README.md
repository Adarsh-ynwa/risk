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

## Quick Start

See **[SETUP.md](./SETUP.md)** for full instructions including Kaggle dataset setup.

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
