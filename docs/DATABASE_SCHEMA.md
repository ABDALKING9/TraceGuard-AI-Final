# Database Schema

- `platforms`: simulated platform name and description.
- `accounts`: fictional username, display name, platform FK.
- `content_records`: fictional post/message, account FK, type, text, review status, synthetic flag.
- `analyses`: record FK, score 0–100, risk category, engine version, matched indicators JSON, explanations JSON.
- `cases`: title, description, status, timestamps.
- `case_records`: unique case/record join.
- `relationships`: source/target account FKs, type, shared synthetic feature, evidence description.
- `analyst_notes`: case FK, optional record FK, note, disposition, timestamp.

Foreign keys are enabled for SQLite. Demo seed uses stable uniqueness checks and may be rerun without duplicating seeded accounts/records/cases/edges.
