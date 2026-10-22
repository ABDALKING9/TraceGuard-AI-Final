"""Offline evaluation script for TraceGuard AI ML classifier.

Runs the scikit-learn TF-IDF + LogisticRegression classifier and the rule engine
on the synthetic seed corpus, captures real metrics from executed code, and prints
a comparison report. All data is synthetic; no cloud/hosted AI is used.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("TRACEGUARD_SECRET_KEY", "eval-script-key")

from backend.app.db.database import Base, engine, SessionLocal  # noqa: E402
from backend.app.models import Analysis, ContentRecord  # noqa: E402
from backend.app.seed import seed  # noqa: E402
from backend.app.services.analysis import analyze_text as analyze_rules  # noqa: E402
from backend.app.services.ml_analysis import (  # noqa: E402
    analyze_text as analyze_ml,
    ML_ENGINE_VERSION,
    get_cached_metrics,
)

RULES_ENGINE_VERSION = "rules-1.1"


def main():
    # Isolated test database.
    os.environ["TRACEGUARD_DATABASE_URL"] = "sqlite:///:memory:"
    Base.metadata.create_all(bind=engine)
    seed()

    rule_results: list[dict] = []
    ml_results: list[dict] = []

    with SessionLocal() as db:
        from sqlalchemy import select

        records = db.scalars(select(ContentRecord).order_by(ContentRecord.id)).all()

        for record in records:
            # Rule engine
            r = analyze_rules(record.content_text)
            rule_results.append({"text": record.content_text, **r})

            # ML engine
            m = analyze_ml(record.content_text)
            ml_results.append({"text": record.content_text, **m})

            # Persist both analyses
            db.add(Analysis(
                record_id=record.id, score=r["score"], risk_category=r["risk_category"],
                engine_version=RULES_ENGINE_VERSION,
                matched_indicators_json=json.dumps(r["matched_indicators"]),
                explanation_json=json.dumps(r["explanations"]),
            ))
            db.add(Analysis(
                record_id=record.id, score=m["score"], risk_category=m["risk_category"],
                engine_version=ML_ENGINE_VERSION, ml_probability=m["score"] / 100.0,
                matched_indicators_json=json.dumps(m["matched_indicators"]),
                explanation_json=json.dumps(m["explanations"]),
            ))

        db.commit()

    # ---- metrics ----
    rule_dist = Counter(r["risk_category"] for r in rule_results)
    ml_dist = Counter(r["risk_category"] for r in ml_results)
    ml_metrics = get_cached_metrics()

    agreements = sum(
        1 for r, m in zip(rule_results, ml_results) if r["risk_category"] == m["risk_category"]
    )
    agreement_rate = agreements / len(rule_results)

    score_diffs = [abs(r["score"] - m["score"]) for r, m in zip(rule_results, ml_results)]
    avg_score_diff = sum(score_diffs) / len(score_diffs)

    report = {
        "total_records": len(rule_results),
        "rule_engine_version": RULES_ENGINE_VERSION,
        "ml_engine_version": ML_ENGINE_VERSION,
        "rule_distribution": dict(sorted(rule_dist.items())),
        "ml_distribution": dict(sorted(ml_dist.items())),
        "agreement_rate": round(agreement_rate, 4),
        "agreements": agreements,
        "avg_score_difference": round(avg_score_diff, 2),
        "ml_metrics": ml_metrics,
    }

    print(json.dumps(report, indent=2))

    out_path = Path(__file__).resolve().parents[1] / "data" / "ml_evaluation_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
