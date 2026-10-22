# TRD — TraceGuard AI

## Architecture
React/TypeScript/Vite frontend → FastAPI REST API → SQLAlchemy → SQLite local file.

## Dependencies
Backend: FastAPI, Uvicorn, SQLAlchemy, Pydantic, pytest, httpx.
Frontend: React, Vite, TypeScript, Lucide React, Recharts.
No paid services, API keys, cloud resources, or external AI.

## Runtime
Backend default: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs
Frontend default: http://127.0.0.1:5173

## Data and analysis
All records are synthetic. The deterministic analysis service returns a 0–100 heuristic score, matched indicator list, explanations, and engine version. Score is not a probability or proof.

## Security
No real data or credentials. UI displays imported text as text, not HTML. API validates inputs through Pydantic. This is an academic local prototype and not production-secure.

## Known scope trade-off
This executor package prioritizes a working end-to-end vertical slice. PDF/CSV report export and import are intentionally deferred until runtime checks pass. The report must mark them incomplete rather than claiming they exist.
