"""ML classifier tests for TraceGuard AI.

Tests the offline scikit-learn TF-IDF + LogisticRegression classifier,
distinct from the rule engine in ``services.analysis``.
"""

from backend.app.services.ml_analysis import (
    ML_ENGINE_VERSION,
    analyze_text as analyze_text_ml,
    classify_score as classify_score_ml,
    get_cached_metrics,
)
from backend.app.services.analysis import ENGINE_VERSION as RULES_ENGINE_VERSION


def test_ml_engine_version_distinct_from_rules():
    assert ML_ENGINE_VERSION != RULES_ENGINE_VERSION
    assert ML_ENGINE_VERSION.startswith("ml-")


def test_ml_classify_score_thresholds():
    assert classify_score_ml(0) == "Low"
    assert classify_score_ml(24) == "Low"
    assert classify_score_ml(25) == "Moderate"
    assert classify_score_ml(49) == "Moderate"
    assert classify_score_ml(50) == "Elevated"
    assert classify_score_ml(74) == "Elevated"
    assert classify_score_ml(75) == "High"
    assert classify_score_ml(100) == "High"


def test_ml_analyze_text_returns_correct_shape():
    result = analyze_text_ml("crypto payment available for 20 packs shipping to postcode")
    assert set(result.keys()) >= {
        "score",
        "risk_category",
        "matched_indicators",
        "explanations",
        "engine_version",
    }
    assert result["engine_version"] == ML_ENGINE_VERSION
    assert 0 <= result["score"] <= 100
    assert result["risk_category"] in {"Low", "Moderate", "Elevated", "High"}


def test_ml_empty_text_returns_low():
    result = analyze_text_ml("")
    assert result["score"] == 0
    assert result["risk_category"] == "Low"
    assert result["matched_indicators"] == []
    assert result["engine_version"] == ML_ENGINE_VERSION


def test_ml_risky_scores_higher_than_benign():
    risky = analyze_text_ml("crypto bitcoin gift card payment shipping to postcode")
    benign = analyze_text_ml("community garden volunteers replanted shared herb beds")
    assert risky["score"] > benign["score"]
    assert risky["risk_category"] != "Low" or benign["risk_category"] == "Low"


def test_ml_is_deterministic():
    text = "crypto payment available for 20 packs shipping to postcode"
    assert analyze_text_ml(text) == analyze_text_ml(text)


def test_ml_matched_indicators_shape():
    result = analyze_text_ml("crypto payment available for 20 packs shipping to postcode")
    for indicator in result["matched_indicators"]:
        assert "id" in indicator
        assert "label" in indicator
        assert "weight" in indicator
        assert "tfidf" in indicator
        assert isinstance(indicator["weight"], float)
        assert isinstance(indicator["tfidf"], float)


def test_ml_explanations_mention_review_priority():
    result = analyze_text_ml("crypto payment available for 20 packs shipping to postcode")
    joined = " ".join(result["explanations"])
    assert "review-priority" in joined or "review priority" in joined.lower()
    assert "not a probability or proof" in joined


def test_ml_model_is_persisted():
    import os
    from backend.app.services.ml_analysis import MODEL_PATH, METRICS_PATH
    # Force training/persistence by calling analyze_text
    analyze_text_ml("crypto payment available for 20 packs shipping to postcode")
    assert os.path.exists(MODEL_PATH), "model file should be persisted"
    assert os.path.exists(METRICS_PATH), "metrics file should be persisted"


def test_ml_metrics_have_expected_keys():
    metrics = get_cached_metrics()
    assert metrics is not None
    # Top-level keys
    expected_top = {
        "training_samples", "training_version", "test_samples",
        "test_risky", "test_benign", "challenge_samples",
        "challenge_risky", "challenge_benign", "held_out_split",
        "challenge_set", "note",
    }
    assert expected_top.issubset(set(metrics.keys())), f"missing keys: {expected_top - set(metrics.keys())}"
    assert metrics["training_samples"] > 0
    assert metrics["test_samples"] > 0
    assert metrics["challenge_samples"] > 0
    # Held-out split has proper metrics
    split = metrics["held_out_split"]
    for key in {"accuracy", "precision_macro", "recall_macro", "f1_macro",
                "precision_weighted", "recall_weighted", "f1_weighted",
                "confusion_matrix", "per_class"}:
        assert key in split, f"missing held_out_split key: {key}"
    # Challenge set has proper metrics
    challenge = metrics["challenge_set"]
    for key in {"accuracy", "precision_macro", "recall_macro", "f1_macro",
                "precision_weighted", "recall_weighted", "f1_weighted",
                "confusion_matrix", "per_class"}:
        assert key in challenge, f"missing challenge_set key: {key}"


def test_ml_vs_rule_engine_different_versions():
    text = "crypto payment available for 20 packs shipping to postcode"
    ml_result = analyze_text_ml(text)
    from backend.app.services.analysis import analyze_text as analyze_text_rules
    rules_result = analyze_text_rules(text)
    assert ml_result["engine_version"] != rules_result["engine_version"]


def test_ml_score_maps_to_risk_category():
    result = analyze_text_ml("crypto payment available for 20 packs shipping to postcode")
    assert result["risk_category"] == classify_score_ml(result["score"])


def test_ml_benign_text_low_score():
    result = analyze_text_ml("community garden volunteers replanted shared herb beds Saturday")
    assert result["risk_category"] == "Low"
    assert result["score"] < 25


def test_ml_ml_probability_in_unit_interval():
    result = analyze_text_ml("crypto payment available for 20 packs shipping to postcode")
    assert "ml_probability" in result
    assert 0.0 <= result["ml_probability"] <= 1.0
    assert result["score"] == int(round(result["ml_probability"] * 100))


def test_ml_explanation_positive_and_negative_features():
    result = analyze_text_ml("crypto payment available for 20 packs shipping to postcode")
    assert "ml_positive_features" in result
    assert "ml_negative_features" in result
    for feature in result["ml_positive_features"]:
        assert feature["weight"] > 0, f"positive feature has non-positive weight: {feature}"
    for feature in result["ml_negative_features"]:
        assert feature["weight"] < 0, f"negative feature has non-negative weight: {feature}"
    for feature in result["ml_positive_features"] + result["ml_negative_features"]:
        assert "id" in feature
        assert "label" in feature
        assert "weight" in feature
        assert "tfidf" in feature
        assert "coef" in feature


def test_ml_explanation_empty_text():
    result = analyze_text_ml("")
    assert result["score"] == 0
    assert result["risk_category"] == "Low"
    assert result["matched_indicators"] == []
    assert "ml_positive_features" not in result or result.get("ml_positive_features") == []


def test_ml_metrics_include_challenge_set():
    metrics = get_cached_metrics()
    assert metrics is not None
    assert metrics["challenge_samples"] > 0
    assert metrics["challenge_risky"] > 0
    assert metrics["challenge_benign"] > 0
    challenge = metrics["challenge_set"]
    assert "accuracy" in challenge
    assert "confusion_matrix" in challenge
    assert "per_class" in challenge
    assert "benign" in challenge["per_class"]
    assert "risky" in challenge["per_class"]

