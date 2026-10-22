import json
import re

ENGINE_VERSION = "rules-1.1"

# Canonical risk vocabulary used by the API, the dashboard charts and the graph.
RISK_CATEGORIES = ["Low", "Moderate", "Elevated", "High"]
RISK_THRESHOLDS = {"Low": 25, "Moderate": 50, "Elevated": 75}

# Deliberately broad illustrative indicators; context and benign exclusions are applied.
RULES = [
    ("transaction_language", re.compile(r"\b(order|orders|available for sale|price list|payment)\b", re.I), 18,
     "Transactional wording appears in the record."),
    ("supply_language", re.compile(r"\b(supply|wholesale|delivery|drop off|dispatch)\b", re.I), 18,
     "Supply or delivery wording appears in the record."),
    ("quantity_language", re.compile(r"\b(\d+\s?(g|kg|grams|ounces|packs|units))\b", re.I), 10,
     "A quantity-like expression appears in the record."),
    ("coded_context", re.compile(r"\b(menu|catalogue|catalog|dm for details)\b", re.I), 8,
     "Promotional or private-contact wording appears in the record."),
    ("contact_handoff", re.compile(r"\b(text me|dm me|call me|reach me|message me)\b", re.I), 20,
     "A direct contact-handoff instruction appears in the record."),
    ("payment_method", re.compile(r"\b(crypto|cryptocurrency|bitcoin|wire transfer|gift cards|gift card)\b", re.I), 25,
     "A payment-method reference appears in the record."),
    ("shipping_destination", re.compile(r"\b(ship to|shipping to|deliver to|postcode|zip code)\b", re.I), 15,
     "A shipping or delivery-destination reference appears in the record."),
]
BENIGN_CONTEXT = re.compile(
    r"\b(anti-drug|drug prevention|recovery|rehabilitation|prescription|pharmacy|"
    r"medical research|public health|news report|fictional example|not selling)\b", re.I
)

def classify_score(score: int) -> str:
    if score < RISK_THRESHOLDS["Low"]:
        return "Low"
    if score < RISK_THRESHOLDS["Moderate"]:
        return "Moderate"
    if score < RISK_THRESHOLDS["Elevated"]:
        return "Elevated"
    return "High"

def analyze_text(text: str) -> dict:
    normalized = re.sub(r"\s+", " ", (text or "")).strip()
    if not normalized:
        return {"score": 0, "risk_category": "Low", "matched_indicators": [],
                "explanations": ["No text was available to analyze."], "engine_version": ENGINE_VERSION}
    benign = bool(BENIGN_CONTEXT.search(normalized))
    matches = []
    explanations = []
    score = 0
    if benign:
        explanations.append("Benign-context language detected; indicator contribution reduced.")
    for rule_id, pattern, weight, explanation in RULES:
        if pattern.search(normalized):
            matches.append({"id": rule_id, "label": rule_id.replace("_", " ").title(), "weight": weight})
            explanations.append(explanation)
            score += weight
    if benign:
        score = round(score * 0.2)
    score = min(100, max(0, score))
    category = classify_score(score)
    if not matches and not explanations:
        explanations.append("No configured indicators matched.")
    explanations.append("This heuristic score is a review-priority aid, not a probability or proof of wrongdoing.")
    return {"score": score, "risk_category": category, "matched_indicators": matches,
            "explanations": explanations, "engine_version": ENGINE_VERSION}

def encode_analysis(result: dict) -> tuple[str, str]:
    return json.dumps(result["matched_indicators"]), json.dumps(result["explanations"])
