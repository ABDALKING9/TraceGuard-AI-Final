# Test Plan

## Automated test suites

Run from the repository root.

### Backend

```bash
python -m pytest backend/tests -q
```

The suite runs against an isolated SQLite database that is created by the
repository root `conftest.py` and injected through `TRACEGUARD_DATABASE_URL`.
The demonstration database in `data/` is never modified by the tests.

Coverage: public endpoints, login/logout/session handling, protection of every
application endpoint, dashboard metrics, risk and platform distributions,
activity buckets, record filters (search, platform, record type, risk, date
range, sorting), record analysis, review dispositions, case lifecycle, note
creation and disposition updates, graph enrichment, node and edge detail, seed
idempotency and the rule engine thresholds.

ML classifier coverage:
- Engine version distinct from rule engine (`ml-tfidf-logreg-v1.0` vs `rules-1.1`)
- Score 0-100, risk category mapping, deterministic output
- Empty text returns Low/0 with no indicators
- Risky text scores higher than benign text
- ML matched indicators have id/label/weight/tfidf/coef shape
- Explanations mention review-priority aid, not proof of wrongdoing
- Model persisted to disk (joblib) and metrics written (JSON)
- Held-out split metrics: accuracy, macro/weighted precision/recall/F1, ROC-AUC, confusion matrix, per-class
- Independent challenge set metrics reported separately (never used in training)
- `ml_probability` in [0, 1], mapped to 0-100 score
- Meta endpoint exposes nested `held_out_split` and `challenge_set` metrics (not top-level shortcuts)

API tests for ML endpoints:
- `POST /api/v1/analysis/run/{record_id}?engine=ml` returns 200 with ML result
- `GET /api/v1/model/info` returns 200 with auth, 401 without
- `GET /api/v1/analysis/compare/{record_id}` returns rule + ML side by side with agree flag
- Compare endpoint requires auth (401 without token)
- Compare preserves each engine's original output, does not average scores

Note and case tests:
- Empty note text rejected with 422
- Whitespace-only note text rejected with 422
- Valid note persists and survives case re-fetch
- Note to nonexistent case returns 404
- Attach record to case succeeds
- Duplicate attachment handled gracefully (`already_attached: true`)
- Attach to nonexistent case returns 404
- Attach nonexistent record returns 404
- Review disposition changes persist after re-fetch

### Frontend unit tests

```bash
cd frontend
npm install
npm test
```

Vitest with jsdom and React Testing Library. Coverage: the API client
(bearer header, 401 handling, error surfacing, login/logout), the login
screen, shared UI components, chart empty states and the content explorer
filter behaviour.

### Frontend end-to-end tests

```bash
cd frontend
npm run test:e2e
```

The suite builds the frontend, starts an isolated backend on
`http://127.0.0.1:8000` (using a copy of `data/traceguard.db`) and the Vite
preview server on `http://127.0.0.1:4173`, then drives headless Chrome through
`puppeteer-core`. Set `CHROME_PATH` if Chrome is installed somewhere else.

## Manual smoke test

1. Start the backend: `uvicorn backend.app.main:app --reload`.
2. Start the frontend: `cd frontend && npm run dev`.
3. Open the frontend URL. The login screen appears; the application endpoints
   are not reachable without a session.
4. Sign in with `demo@traceguard.local` / `Demo@123`.
5. Confirm the dashboard metrics update (150 records, 75 accounts, 30 cases).
6. Confirm the risk, platform and activity charts render, and that switching
   the activity interval between daily and weekly reloads the chart.
7. Search and filter records in Content Explorer: free text, platform, risk
   category, record type and the date range. Confirm the empty state appears
   for a range without data.
8. Open a record and run the analysis. Confirm the matched indicators and the
   explanation are listed.
9. On record selection, confirm both rule engine and ML classifier results are
   shown side by side with agreement/disagreement status.
10. Confirm ML positive features (supporting risky) and negative features
    (supporting benign) are displayed with coefficients.
11. Create a case, attach a record and add an analyst note; change the note
    disposition and confirm it persists after a reload.
12. Confirm empty or whitespace-only notes are rejected with a validation error.
13. Inspect the relationship graph: select a node and an edge and confirm the
    metadata, risk level, related records and evidence are shown.
14. Confirm the Methodology page states the core principle and the
    synthetic-data notice.
15. Open the Overview page and confirm ML metrics show held-out and challenge-set
    values as percentages (not dashes).
16. Restart the backend and confirm records, cases and notes remain.
17. Sign out and confirm the application endpoints are no longer reachable.

Report each item as PASS, FAIL, PARTIAL, or NOT RUN. Include exact commands
and error text. Do not claim a check passed unless it was run.
