# TraceGuard AI — Executor Package

This package is a deterministic starter codebase for an offline academic MVP. It uses synthetic data only. The platform names Telegram, WhatsApp, and Instagram are simulated categories; there are no platform integrations.

## Stack
- Backend: Python, FastAPI, SQLAlchemy, SQLite
- Frontend: React, TypeScript, Vite, Recharts, Cytoscape
- Detection: transparent deterministic rules + optional offline scikit-learn ML classifier (TF-IDF + LogisticRegression)
- Authentication: local demonstration credential with signed bearer tokens

## Run backend (from project root)
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```
Backend: http://127.0.0.1:8000  
Swagger: http://127.0.0.1:8000/docs

In a second terminal, seed demo data:
```bash
python -m backend.app.seed
```
The seed is deterministic and idempotent: running it twice does not duplicate
accounts, records, cases, relationships or notes, and it never overwrites
analyst decisions that already exist.

## Run frontend
```bash
cd frontend
npm install
npm run dev
```
Open the URL printed by Vite.

## Sign in

The workspace requires a local demonstration session:

```
email:    demo@traceguard.local
password: Demo@123
```

The credential is a local demo default, not a secret. Override it with the
environment variables `TRACEGUARD_DEMO_EMAIL` and `TRACEGUARD_DEMO_PASSWORD`.
The signing key is read from `TRACEGUARD_SECRET_KEY`; when it is not set the
server falls back to a published demonstration key and logs a warning. Set the
variable before any non-local deployment.

Other supported environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `TRACEGUARD_DATABASE_URL` | `data/traceguard.db` | Point the API at another SQLite file |
| `TRACEGUARD_SECRET_KEY` | local demonstration key | HS256 token signing key |
| `TRACEGUARD_TOKEN_TTL_MINUTES` | `480` | Session token lifetime |

The frontend stores the issued token in `sessionStorage` only; nothing is
written to `localStorage` and no cookie is used.

## Test backend
```bash
pytest backend/tests -q
```
Includes ML classifier tests in `backend/tests/test_ml.py` plus API tests
for `/api/v1/analysis/run/{record_id}?engine=ml`, `/api/v1/model/info`,
and `/api/v1/analysis/compare/{record_id}`.

## Evaluate ML classifier
```bash
python scripts/evaluate_ml.py
```
Scores all 150 seed records with both engines and writes
`data/ml_evaluation_report.json` with real metrics from executed code.
Includes held-out split metrics and independent challenge-set metrics.

## Test frontend
```bash
cd frontend
npm test        # Vitest unit tests
npm run test:e2e  # headless Chrome end-to-end suite
```

## Important
This is an academic prototype, not a validated detection system. Scores are heuristic review-priority indicators, not probabilities or evidence of guilt. Do not use real personal data.
