# API Specification

Base URL: `http://127.0.0.1:8000`

## Authentication

All application endpoints under `/api/v1` require a bearer token except the four
public endpoints listed below.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | public | Service and database health check |
| POST | `/api/v1/auth/login` | public | Exchange the demonstration credentials for a token |
| POST | `/api/v1/auth/logout` | public | Revoke the supplied token server side |
| GET | `/api/v1/auth/session` | bearer | Validate a stored token and return the session user |
| GET | `/api/v1/meta` | public | Risk vocabulary, thresholds, engine versions, methodology principle |
| GET | `/api/v1/model/info` | bearer | Offline ML classifier version, type, and held-out evaluation metrics |

Login request:

```json
{ "email": "demo@traceguard.local", "password": "Demo@123" }
```

Login response:

```json
{
  "access_token": "<HS256 JWT>",
  "token_type": "bearer",
  "expires_at": "2026-10-22T19:00:00+00:00",
  "expires_in_minutes": 480,
  "user": { "email": "demo@traceguard.local", "role": "demonstration operator" }
}
```

Send the token on every protected call:

```
Authorization: Bearer <access_token>
```

A missing, malformed, expired or revoked token returns `401` with
`{"detail": "..."}`. Tokens carry a `jti` claim that is tracked in a server-side
revocation list.

## Application endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/platforms` | Simulated platform catalogue |
| GET | `/api/v1/dashboard/summary` | Metric cards, risk distribution, platform distribution |
| GET | `/api/v1/dashboard/activity?interval=day\|week` | Record volume per day or week |
| GET | `/api/v1/records` | Filterable record list (see below) |
| GET | `/api/v1/records/{record_id}` | Single record with its latest analysis |
| POST | `/api/v1/analysis/run/{record_id}` | Re-run the rule engine and store a new analysis |
| GET | `/api/v1/cases` | Investigation cases |
| POST | `/api/v1/cases` | Create a case |
| GET | `/api/v1/cases/{case_id}` | Case with linked records and analyst notes |
| PATCH | `/api/v1/cases/{case_id}` | Update case title, description or status |
| POST | `/api/v1/cases/{case_id}/records/{record_id}` | Attach a record to a case |
| POST | `/api/v1/cases/{case_id}/notes` | Add an analyst note |
| PATCH | `/api/v1/cases/{case_id}/notes/{note_id}` | Update an existing note or its disposition |
| PATCH | `/api/v1/records/{record_id}/review` | Update the review disposition |
| GET | `/api/v1/graph` | Relationship graph with per-node risk metadata |
| GET | `/api/v1/graph/nodes/{account_id}` | Node detail: metadata, risk, records, evidence, links |
| GET | `/api/v1/graph/edges/{edge_id}` | Edge detail with both endpoints and evidence |
| POST | `/api/v1/demo/seed` | Load or refresh the synthetic demonstration corpus |

### `GET /api/v1/records` query parameters

| Parameter | Default | Notes |
| --- | --- | --- |
| `search` | `""` | Matches record content or the account username |
| `platform` | `""` | Simulated platform name |
| `record_type` | `""` | `post` or `message` |
| `risk_category` | `""` | `Low`, `Moderate`, `Elevated` or `High` (latest analysis per record) |
| `date_from` | `""` | Inclusive ISO date (`YYYY-MM-DD`) |
| `date_to` | `""` | Inclusive ISO date (`YYYY-MM-DD`) |
| `page` | `1` | Page number |
| `page_size` | `20` | 1–200 |
| `sort` | `id_asc` | `id_asc`, `id_desc`, `created_asc` or `created_desc` |

Response shape:

```json
{
  "items": [ /* records with account and latest analysis */ ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "filters": { "search": "", "platform": "", "date_from": null, "date_to": null, "sort": "id_asc" }
}
```

### `GET /api/v1/dashboard/summary` response shape

```json
{
  "records": 150,
  "accounts": 75,
  "cases": 30,
  "pending_review": 85,
  "risk_distribution": [{ "category": "Low", "count": 60 }],
  "platform_distribution": [{ "platform": "Telegram", "count": 52 }],
  "account_distribution": [{ "platform": "Telegram", "count": 26 }],
  "risk_basis": "latest analysis per record",
  "platform_basis": "content records per platform",
  "data_mode": "Synthetic Data — Offline Demo"
}
```

`risk_distribution` always contains the four canonical categories, including
categories with a count of zero. `platform_distribution` counts content
records; `account_distribution` counts accounts.

### `GET /api/v1/graph` response shape

Nodes carry `risk_score`, `risk_category`, `record_count`, `record_ids` and
`connection_count` so the graph can be styled and inspected without extra
requests. Edge `id` values are the `relationships` primary keys and are used
by `/api/v1/graph/edges/{edge_id}`.

OpenAPI docs are available at `/docs` while the backend is running.

### ML classifier (`?engine=ml`)

The optional offline ML classifier is a scikit-learn pipeline (TF-IDF vectorization +
LogisticRegression) trained on a synthetic labelled corpus. It is selected via
`?engine=ml` on `/api/v1/analysis/run/{record_id}` and is clearly distinguishable
from the rule engine by its `engine_version` (`ml-tfidf-logreg-v1.0`).

ML analysis response adds an `ml_probability` field (0–1, the predicted-class
probability output / confidence-like score for the synthetic "risky" class — not
a calibrated probability of criminal activity). Matched indicators show TF-IDF
feature coefficients and tfidf values rather than rule weights. Positive and
negative feature contributions are available for explainability.

`GET /api/v1/model/info` returns the ML engine version, model type, training
version, and held-out + challenge-set evaluation metrics.

`GET /api/v1/analysis/compare/{record_id}` runs both engines on the same record
and returns their results side by side with an `agree` flag (whether risk
categories match). Each engine's original output is preserved; no scores are
averaged and no combined risk score is produced. Disagreement is a reason to
inspect context, not proof of wrongdoing.

ML evaluation results (run against the 150-record synthetic seed corpus):

| Metric | Value |
| --- | --- |
| Total records scored | 150 |
| Rule engine distribution | Low: 60, Moderate: 45, Elevated: 30, High: 15 |
| ML engine distribution | Low: 32, Moderate: 46, Elevated: 67, High: 5 |
| Cross-engine agreement | 55.3% (83/150) |
| Avg score difference | 17.41 points |

Held-out split (25% of training data, stratified, random_state=42):

| Metric | Value |
| --- | --- |
| Accuracy | 1.0000 |
| Precision (macro) | 1.0000 |
| Recall (macro) | 1.0000 |
| F1 (macro) | 1.0000 |
| Precision (weighted) | 1.0000 |
| Recall (weighted) | 1.0000 |
| F1 (weighted) | 1.0000 |
| ROC-AUC | 1.0000 |
| Training samples | 192 (121 risky, 71 benign) |
| Test samples | 48 (30 risky, 18 benign) |

Independent challenge set (23 samples, never used in training or tuning):

| Metric | Value |
| --- | --- |
| Accuracy | 0.8261 |
| Precision (macro) | 0.8333 |
| Recall (macro) | 0.8667 |
| F1 (macro) | 0.8231 |
| Precision (weighted) | 0.8841 |
| Recall (weighted) | 0.8261 |
| F1 (weighted) | 0.8301 |
| ROC-AUC | 0.9750 |
| Challenge samples | 23 (8 risky, 15 benign) |

Challenge-set confusion matrix: [[11, 4], [0, 8]]
(11 benign correctly classified, 4 benign false positives, 0 risky false negatives,
8 risky correctly classified).

All metrics above are produced by executed code (see `scripts/evaluate_ml.py` and
`data/ml_evaluation_report.json`). The perfect held-out scores reflect the
synthetic, keyword-separable training corpus (risky and benign vocabularies barely
overlap by design); they are demonstration metrics, not real-world performance
claims. Challenge-set results show realistic, imperfect generalization.
