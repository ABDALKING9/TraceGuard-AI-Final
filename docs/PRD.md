# PRD — TraceGuard AI

## Objective
A local academic MVP that demonstrates review of synthetic social-media-style records, explainable heuristic scoring (deterministic rule engine plus offline scikit-learn ML classifier), case management, evidence-backed relationship review, and a dashboard with rule-versus-ML comparison.

## Scope
- Simulated Telegram, WhatsApp, Instagram labels only.
- Synthetic accounts and content in SQLite.
- Dashboard with live backend metrics including ML classifier evaluation metrics.
- Search/filter content explorer and record details.
- Explainable server-side scoring: rule engine and TF-IDF + LogisticRegression ML classifier.
- Investigation cases, linked records, notes, review disposition.
- Relationship list based on explicitly seeded synthetic edges.
- Methodology/limitations view covering both engines and their limitations.
- Rule-versus-ML comparison with agreement/disagreement flagging.

## Scope
- Simulated Telegram, WhatsApp, Instagram labels only.
- Synthetic accounts and content in SQLite.
- Dashboard with live backend metrics.
- Search/filter content explorer and record details.
- Explainable server-side scoring.
- Investigation cases, linked records, notes, review disposition.
- Relationship list based on explicitly seeded synthetic edges.
- Methodology/limitations view.

## Out of scope
- Live platform APIs or scraping.
- Real personal/private data.
- Paid services, external AI models, cloud hosting.
- Real-world criminal classification or production deployment.
- Full CSV import and PDF export in this initial code slice; add after smoke tests.

## Acceptance
- App runs locally.
- Demo seed is idempotent.
- 3 platforms, >=15 accounts, >=40 records and >=3 cases.
- Dashboard derives values from SQLite.
- Analysis results persist with explanation.
- Case creation, record attachment, notes, review changes persist.
- Graph edges show explicit evidence descriptions.
- Backend tests and frontend build pass.
- UI clearly labels all data synthetic.
