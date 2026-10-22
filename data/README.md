# Data directory

The SQLite database used by the demonstration is **not** committed to the
repository. It is generated locally and is reproducible from the seed script:

```bash
python -m backend.app.seed
```

This creates `data/traceguard.db` with the full synthetic corpus
(3 platforms, 75 accounts, 150 content records, 30 cases, 56 relationships and
40 analyst notes). The seed is deterministic and idempotent, so re-running it
never duplicates rows and never overwrites analyst decisions that already
exist.

Local backups written by the maintainer live in `data/backups/` and are ignored
by git as well.

The offline ML classifier persists its fitted pipeline as `data/ml_model.joblib`
and held-out evaluation metrics as `data/ml_metrics.json`. These files are
created on first ML analysis run and are not committed to the repository.

To point the API at a different database file, set `TRACEGUARD_DATABASE_URL`:

```bash
TRACEGUARD_DATABASE_URL="sqlite:///C:/temp/traceguard.db" uvicorn backend.app.main:app
```
