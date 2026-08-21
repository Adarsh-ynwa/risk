# AI Risk Manager

AI Risk Manager is an experimental payment-fraud operations platform that helps an analyst answer three practical questions:

1. Is this transaction risky?
2. Why was it flagged?
3. What should we do next?

The project combines an XGBoost fraud model, transparent business rules, and an AI investigation agent. Instead of returning only a probability, it presents the evidence behind the decision and recommends an action such as approving, monitoring, verifying, holding, or blocking a payment.

> This is a defensive prototype built with synthetic or public data. It is not a Razorpay internal system and should not be used to make real payment decisions without further validation, security work, and compliance review.

## What the project does

- Scores new and historical transactions for fraud risk.
- Classifies payments as `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` risk.
- Shows the ML score, rule score, triggered rules, and behavioral evidence.
- Maintains a prioritized alert queue for analysts.
- Investigates suspicious transactions using LangGraph and Groq.
- Falls back to a deterministic investigator when Groq is unavailable.
- Supports customer verification, human approval, unblock requests, and case timelines.
- Reports held-out model metrics and threshold trade-offs.

## How it works

```text
Transaction
    |
    v
Feature engineering
    |
    +-------------------+
    |                   |
    v                   v
XGBoost model     Fraud rule engine
    |                   |
    +---------+---------+
              |
              v
       Combined risk score
              |
              v
 AI investigation + evidence tools
              |
              v
 Recommended action + human control
```

The final score normally uses 60% of the ML score and 40% of the rule score. A safety floor is applied when many strong deterministic signals appear together. The current rules cover large payments, international activity, nighttime activity, repeated failed attempts, recent PIN changes, unusual distance, young accounts, and abnormal transaction frequency.

## Key technical challenges

1. **Imbalanced fraud data:** Most transactions are legitimate, so accuracy alone can be misleading. I evaluated the model using precision, recall, F1, PR-AUC, ROC-AUC, and a confusion matrix with a chronological train/validation/test split.

2. **Choosing a useful threshold:** A low threshold creates too many false alerts, while a high threshold misses fraud. I selected the threshold on validation data using an illustrative merchant-cost model: INR 200 per false positive and INR 5,500 per false negative.

3. **ML does not catch every pattern:** A statistical model can miss unfamiliar attacks. I combined XGBoost with deterministic fraud rules so known high-risk signals still influence the result.

4. **AI reliability and availability:** An LLM can invent evidence, return malformed output, or be unavailable during a demo. The investigator uses allowlisted read-only tools, validates its response with Pydantic, records its tool calls, and has a deterministic fallback.

5. **Unsafe automatic blocking:** A wrong decision can affect a genuine customer. The AI recommends actions, while sensitive decisions remain part of a human-controlled verification, approval, and unblock workflow with an audit timeline.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Pydantic, SQLAlchemy |
| Machine learning | XGBoost, scikit-learn, pandas, NumPy |
| AI investigation | LangGraph, Groq, read-only investigation tools |
| Database | SQLite locally, PostgreSQL in production |
| Deployment | Vercel frontend, Render backend and database |

## Run the project locally

### Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- A Groq API key is optional

### 1. Set up the backend on Windows

The setup script creates a virtual environment, installs dependencies, generates synthetic data when needed, trains the model, and loads the SQLite database.

```powershell
cd backend
.\scripts\setup.ps1
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Check [http://localhost:8000/health](http://localhost:8000/health). A successful setup should report that the database is connected and the model is loaded.

To configure the live AI investigator, add your key to `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key
```

Without this key, the application still works and uses the deterministic investigation fallback.

### 2. Set up the frontend

Open another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The frontend expects the API at `http://localhost:8000` by default.

### Manual backend setup

If you do not want to use the PowerShell setup script:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/generate_sample_data.py
python scripts/train_model.py
python scripts/load_data.py --force-reload
uvicorn app.main:app --reload --port 8000
```

## Demo transactions

The generated dataset contains realistic synthetic legitimate and fraudulent payments. During loading, the application pre-analyzes useful fraud cases and high-signal transactions so that the dashboard is ready for a demo.

For a quick walkthrough:

1. Open the application and click **View Highest Risk Transaction** in the header.
2. Review the ML score, rule score, final risk level, and triggered rules.
3. Check the customer's behavioral evidence against earlier transactions.
4. Click **Run AI Investigation** to gather evidence through the investigation tools.
5. Review the recommendation and tool-call history.
6. Request verification or apply a human-approved demo action.
7. Open the case timeline to see the audit trail.

You can also create a transaction from **Transactions -> New Transaction**. It is saved and scored immediately, which is useful for testing individual combinations of risk signals.

### Add dedicated high-risk demo transactions

The optional generator creates varied synthetic account-takeover cases with IDs beginning with `DEMOHR`. These cases may include international activity, nighttime payments, unusual locations, repeated failures, recent PIN changes, and large amounts.

Run it only after the base dataset and database exist:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python scripts/generate_high_risk_transactions.py --count 100
python scripts/load_data.py --force-reload
```

`DEMOHR` records are excluded from model development, so hand-crafted demo cases do not leak into training, validation, or test metrics. Retraining is not required merely to display these demo transactions. If you intentionally retrain later, the training script will continue to exclude them.

## Use a Kaggle dataset instead

Place the Bank Transaction Fraud Detection CSV at:

```text
backend/data/bank_fraud.csv
```

Then run:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python scripts/inspect_dataset.py
python scripts/train_model.py
python scripts/load_data.py --force-reload
```

Training uses up to 200,000 rows by default. Database loading is controlled by `MAX_TRANSACTIONS_LOAD`, which defaults to 150,000.

## Honest model evaluation

The model uses a chronological 70/15/15 train, validation, and held-out test split. The operating threshold is selected using validation data only. Final precision, recall, false positives, false negatives, alert rate, PR-AUC, ROC-AUC, and cost estimates are then calculated on the untouched test set.

The INR 200 false-positive cost and INR 5,500 false-negative cost are illustrative assumptions, not measured merchant financials. They can be changed in `backend/scripts/train_model.py`. Generated results are stored in `backend/artifacts/metrics.json` and displayed on the Evaluation page.

## Main API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check the database, model, and Groq configuration |
| `GET` | `/stats` | Dashboard KPIs |
| `GET` | `/transactions` | Search, filter, sort, and paginate transactions |
| `POST` | `/transactions` | Create and immediately score a transaction |
| `GET` | `/transactions/{id}` | Transaction and risk details |
| `POST` | `/risk/analyze` | Analyze an existing transaction |
| `POST` | `/investigations/{id}` | Run an AI or fallback investigation |
| `POST` | `/actions/{id}` | Apply an analyst action |
| `GET` | `/transactions/{id}/behavior` | Customer behavioral evidence |
| `GET` | `/cases/{id}/timeline` | Auditable case timeline |
| `POST` | `/verifications/{id}` | Request customer verification |
| `PATCH` | `/verifications/{id}` | Resolve a verification request |
| `GET` | `/model/metrics` | Held-out evaluation results |
| `GET` | `/analytics` | Risk and fraud analytics |

Interactive API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs) while the backend is running.

## Project structure

```text
backend/
  app/
    agent/            AI investigator and read-only tools
    models/           SQLAlchemy database models
    schemas/          Pydantic request and response contracts
    services/         ML, rules, scoring, and transaction workflows
    main.py           FastAPI routes and application entry point
  artifacts/          Trained model, preprocessor, metadata, and metrics
  scripts/            Data generation, training, loading, and seeding
  tests/              Workflow tests

frontend/
  src/app/            Next.js pages
  src/components/     Dashboard, transaction, investigation, and UI components
  src/lib/api.ts      Typed backend API client
```

## Environment variables

| Variable | Location | Description |
|---|---|---|
| `GROQ_API_KEY` | `backend/.env` | Optional key for live AI investigation |
| `DATABASE_URL` | `backend/.env` | SQLite or PostgreSQL connection string |
| `CORS_ORIGINS` | `backend/.env` | Comma-separated allowed frontend origins |
| `MAX_TRANSACTIONS_LOAD` | `backend/.env` | Maximum rows loaded into the database |
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | Backend API URL |

## Deployment

The repository includes `render.yaml` for the FastAPI service and PostgreSQL database, and `frontend/vercel.json` for the Next.js application. See [DEPLOYMENT.md](./DEPLOYMENT.md) for the complete deployment process.

## License

MIT License. Built as a hackathon and learning project.
