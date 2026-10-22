"""Offline ML text classifier for TraceGuard AI.

This module is deliberately separate from ``services.analysis`` (the rule engine).
It trains a TF-IDF + LogisticRegression pipeline on a synthetic labelled corpus,
persists the fitted model to disk with joblib, and scores records using only local
compute.  No cloud/hosted AI is used and no real platform data is ingested.

The ML classifier is a *review-priority aid*: its score is the model's
predicted-class probability output (confidence-like score) for the synthetic
"risky" label mapped to 0-100.  It is not a calibrated probability of criminal
activity and is never evidence of wrongdoing.  It is clearly distinguishable
from the rule engine through its own engine version, matched indicator
representation, and explanation text.

Evaluation integrity:
- TF-IDF is fitted exclusively on training data (never on test or challenge data).
- Train/test split is stratified with a fixed random seed for reproducibility.
- A separate, independent synthetic challenge set is held out from training
  and model tuning and is used only for final reporting.
- The synthetic corpus is keyword-separable by design (risky and benign
  vocabularies barely overlap), so perfect held-out scores reflect the
  artificial separation of the demonstration data, not real-world performance.
"""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
)

from ..data.ml_training_data import (
    TRAINING_DATA,
    TRAINING_VERSION,
    LABEL_RISKY,
    LABEL_BENIGN,
    CHALLENGE_SET,
)

ML_ENGINE_VERSION = "ml-tfidf-logreg-v1.0"
MODEL_FILENAME = "ml_model.joblib"
METRICS_FILENAME = "ml_metrics.json"

# The ML classifier shares the canonical risk vocabulary and thresholds with the
# rule engine so both engines are comparable on the same four bands.
RISK_CATEGORIES = ["Low", "Moderate", "Elevated", "High"]
RISK_THRESHOLDS = {"Low": 25, "Moderate": 50, "Elevated": 75}

# Top-k TF-IDF features exposed as "matched indicators" for explainability.
TOP_K_INDICATORS = 8

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
MODEL_PATH = DATA_DIR / MODEL_FILENAME
METRICS_PATH = DATA_DIR / METRICS_FILENAME


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def classify_score(score: int) -> str:
    if score < RISK_THRESHOLDS["Low"]:
        return "Low"
    if score < RISK_THRESHOLDS["Moderate"]:
        return "Moderate"
    if score < RISK_THRESHOLDS["Elevated"]:
        return "Elevated"
    return "High"


def _build_pipeline() -> Pipeline:
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.9,
        max_features=5000,
    )
    classifier = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
    )
    return Pipeline([("tfidf", vectorizer), ("clf", classifier)])


def _binary_metrics(y_true, y_pred, y_proba, label_names):
    """Compute per-class and aggregate binary/multiclass-style metrics."""
    labels = sorted(set(y_true))
    report = classification_report(
        y_true, y_pred, labels=labels, target_names=label_names,
        zero_division=0, output_dict=True,
    )
    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()

    per_class = {}
    for label in labels:
        name = label_names[int(label)] if int(label) < len(label_names) else str(label)
        entry = report.get(name, {})
        per_class[name] = {
            "precision": round(float(entry.get("precision", 0.0)), 4),
            "recall": round(float(entry.get("recall", 0.0)), 4),
            "f1": round(float(entry.get("f1-score", 0.0)), 4),
            "support": int(entry.get("support", 0)),
        }

    macro = report.get("macro avg", {})
    weighted = report.get("weighted avg", {})

    try:
        roc_auc = round(float(roc_auc_score(y_true, y_proba)), 4)
    except Exception:
        roc_auc = None

    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision_macro": round(float(macro.get("precision", 0.0)), 4),
        "recall_macro": round(float(macro.get("recall", 0.0)), 4),
        "f1_macro": round(float(macro.get("f1-score", 0.0)), 4),
        "precision_weighted": round(float(weighted.get("precision", 0.0)), 4),
        "recall_weighted": round(float(weighted.get("recall", 0.0)), 4),
        "f1_weighted": round(float(weighted.get("f1-score", 0.0)), 4),
        "roc_auc": roc_auc,
        "confusion_matrix": cm,
        "per_class": per_class,
    }


def _train_and_persist() -> tuple[Pipeline, dict[str, Any]]:
    """Train on the synthetic corpus, evaluate on held-out split + challenge set."""
    texts = [t for t, _ in TRAINING_DATA]
    labels = [l for _, l in TRAINING_DATA]

    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels
    )

    pipeline = _build_pipeline()
    pipeline.fit(train_texts, train_labels)

    # --- held-out split evaluation (TF-IDF fitted on train only) ---
    test_proba = pipeline.predict_proba(test_texts)[:, 1]
    test_pred = (test_proba >= 0.5).astype(int)
    test_metrics = _binary_metrics(
        test_labels, test_pred, test_proba, ["benign", "risky"],
    )

    # --- independent challenge set evaluation (never seen in training) ---
    challenge_texts = [t for t, _ in CHALLENGE_SET]
    challenge_labels = [l for _, l in CHALLENGE_SET]
    challenge_proba = pipeline.predict_proba(challenge_texts)[:, 1]
    challenge_pred = (challenge_proba >= 0.5).astype(int)
    challenge_metrics = _binary_metrics(
        challenge_labels, challenge_pred, challenge_proba, ["benign", "risky"],
    )

    metrics = {
        "training_samples": len(TRAINING_DATA),
        "training_version": TRAINING_VERSION,
        "test_samples": len(test_labels),
        "test_risky": int(sum(test_labels)),
        "test_benign": int(len(test_labels) - sum(test_labels)),
        "challenge_samples": len(CHALLENGE_SET),
        "challenge_risky": int(sum(challenge_labels)),
        "challenge_benign": int(len(challenge_labels) - sum(challenge_labels)),
        "held_out_split": test_metrics,
        "challenge_set": challenge_metrics,
        "note": (
            "The synthetic corpus is keyword-separable by design; perfect or "
            "near-perfect scores reflect artificial label-phrase alignment in "
            "demonstration data, not real-world detection performance."
        ),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return pipeline, metrics


def _load_pipeline() -> Pipeline | None:
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def get_or_train_model() -> Pipeline:
    """Return the fitted pipeline, training it first if no persisted model exists."""
    pipeline = _load_pipeline()
    if pipeline is None:
        pipeline, _metrics = _train_and_persist()
    return pipeline


def get_cached_metrics() -> dict[str, Any] | None:
    if not METRICS_PATH.exists():
        return None
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def _explain(pipeline: Pipeline, text: str) -> dict[str, Any]:
    """Compute feature contributions using fitted vectorizer and classifier coefficients.

    Returns the strongest positive and negative contributions for the predicted
    (risky) class, plus an overall explanation string.  Contributions are
    model evidence only -- not proof of criminal intent.
    """
    normalized = _normalize(text)
    if not normalized:
        return {
            "indicators": [],
            "positive": [],
            "negative": [],
            "explanation": "No text was available to analyze.",
        }

    vectorizer: TfidfVectorizer = pipeline.named_steps["tfidf"]
    classifier: LogisticRegression = pipeline.named_steps["clf"]

    tfidf_vector = vectorizer.transform([normalized])
    feature_names = np.array(vectorizer.get_feature_names_out())
    coef = classifier.coef_[0]

    present_indices = tfidf_vector.indices
    present_values = tfidf_vector.data
    contributions = present_values * coef[present_indices]

    entries = []
    for idx in range(len(present_indices)):
        feature_index = int(present_indices[idx])
        entries.append(
            {
                "id": str(feature_names[feature_index]).replace(" ", "_"),
                "label": str(feature_names[feature_index]),
                "weight": round(float(contributions[idx]), 4),
                "tfidf": round(float(present_values[idx]), 4),
                "coef": round(float(coef[feature_index]), 4),
            }
        )

    # Sort: positive contributions descending first, then negative ascending.
    positive = sorted(
        [e for e in entries if e["weight"] > 0], key=lambda e: -e["weight"]
    )[:TOP_K_INDICATORS]
    negative = sorted(
        [e for e in entries if e["weight"] < 0], key=lambda e: e["weight"]
    )[:TOP_K_INDICATORS]

    top_indicators = sorted(entries, key=lambda e: -abs(e["weight"]))[:TOP_K_INDICATORS]

    explanation = (
        "ML prediction uses fitted TF-IDF features and LogisticRegression "
        "coefficients. Top contributing features shown below; positive weights "
        "push toward the synthetic 'risky' class, negative weights pull toward "
        "'benign'. Model evidence only -- not proof of wrongdoing."
    )

    return {
        "indicators": top_indicators,
        "positive": positive,
        "negative": negative,
        "explanation": explanation,
    }


def analyze_text(text: str) -> dict[str, Any]:
    """Analyze text with the offline ML classifier.

    Returns a dict compatible with the rule engine's output shape so both
    engines can be stored in the same Analysis table and rendered by the same
    frontend components.
    """
    normalized = _normalize(text)
    pipeline = get_or_train_model()

    if not normalized:
        return {
            "score": 0,
            "risk_category": "Low",
            "matched_indicators": [],
            "explanations": ["No text was available to analyze."],
            "engine_version": ML_ENGINE_VERSION,
        }

    # Predicted-class probability output for the risky class (confidence-like
    # score), mapped to 0-100.  Not a calibrated probability of criminal activity.
    proba = float(pipeline.predict_proba([normalized])[0][1])
    score = int(round(proba * 100))
    score = min(100, max(0, score))
    category = classify_score(score)

    explanation_data = _explain(pipeline, normalized)
    indicators = explanation_data["indicators"]
    explanations = [explanation_data["explanation"]]
    if not indicators:
        explanations.append("No strong contributing TF-IDF features found.")
    explanations.append(
        "This ML score is a review-priority aid, not a probability or proof of wrongdoing."
    )

    return {
        "score": score,
        "risk_category": category,
        "matched_indicators": indicators,
        "explanations": explanations,
        "engine_version": ML_ENGINE_VERSION,
        "ml_probability": round(proba, 4),
        "ml_positive_features": explanation_data["positive"],
        "ml_negative_features": explanation_data["negative"],
    }


def encode_analysis(result: dict[str, Any]) -> tuple[str, str]:
    return json.dumps(result["matched_indicators"]), json.dumps(result["explanations"])
