"""API tests for the TraceGuard AI backend.

Every test runs against an isolated SQLite database (see the repository root
``conftest.py``) so the demonstration dataset in ``data/`` is never modified.
"""

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.seed import LEGACY_CASES, NEW_CASES
from backend.app.services.analysis import ENGINE_VERSION, RISK_CATEGORIES, analyze_text, classify_score
from backend.app.services.ml_analysis import ML_ENGINE_VERSION, get_cached_metrics

SEEDED_CASE_TITLES = {title for title, *_ in LEGACY_CASES} | {title for title, *_ in NEW_CASES}


# --------------------------------------------------------------------------------------
# public endpoints
# --------------------------------------------------------------------------------------
def test_health_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_meta_is_public_and_documents_synthetic_mode(client):
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["data_mode"] == "synthetic_offline"
    assert body["risk_categories"] == RISK_CATEGORIES
    assert body["engine_version"] == ENGINE_VERSION
    assert "not a probability" in body["methodology_principle"]
    assert "synthetic" in body["synthetic_data_notice"].lower()


def test_openapi_documentation_stays_public(client):
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


# --------------------------------------------------------------------------------------
# authentication
# --------------------------------------------------------------------------------------
def test_login_with_demo_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@traceguard.local", "password": "Demo@123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in_minutes"] > 0
    assert body["user"]["email"] == "demo@traceguard.local"


def test_login_rejects_wrong_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@traceguard.local", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_rejects_unknown_account(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.invalid", "password": "Demo@123"},
    )
    assert response.status_code == 401


PROTECTED_ENDPOINTS = [
    ("get", "/api/v1/platforms"),
    ("get", "/api/v1/dashboard/summary"),
    ("get", "/api/v1/dashboard/activity"),
    ("get", "/api/v1/records"),
    ("get", "/api/v1/cases"),
    ("get", "/api/v1/graph"),
    ("post", "/api/v1/demo/seed"),
]


def test_protected_endpoints_require_a_token(client):
    for method, path in PROTECTED_ENDPOINTS:
        response = getattr(client, method)(path)
        assert response.status_code == 401, f"{method.upper()} {path} was not protected"
        assert "Authentication required" in response.json()["detail"]


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/api/v1/dashboard/summary", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_session_endpoint_validates_a_token(client, auth_headers):
    response = client.get("/api/v1/auth/session", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "demo@traceguard.local"


def test_logout_revokes_the_token(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@traceguard.local", "password": "Demo@123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/dashboard/summary", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard/summary", headers=headers).status_code == 401


# --------------------------------------------------------------------------------------
# dashboard
# --------------------------------------------------------------------------------------
def test_dashboard_summary_counts(client, auth_headers):
    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["records"] == 150
    assert body["accounts"] == 75
    assert body["data_mode"] == "Synthetic Data — Offline Demo"


def test_seeded_case_corpus_size(client, auth_headers):
    cases = client.get("/api/v1/cases", headers=auth_headers).json()
    seeded = [case for case in cases if case["title"] in SEEDED_CASE_TITLES]
    assert len(seeded) == 30
    assert len(SEEDED_CASE_TITLES) == 30


def test_dashboard_risk_distribution_matches_seed_targets(client, auth_headers):
    body = client.get("/api/v1/dashboard/summary", headers=auth_headers).json()
    distribution = {row["category"]: row["count"] for row in body["risk_distribution"]}
    assert distribution == {"Low": 60, "Moderate": 45, "Elevated": 30, "High": 15}
    assert sum(distribution.values()) == body["records"]


def test_dashboard_platform_distribution_counts_records(client, auth_headers):
    body = client.get("/api/v1/dashboard/summary", headers=auth_headers).json()
    distribution = {row["platform"]: row["count"] for row in body["platform_distribution"]}
    assert distribution == {"Telegram": 52, "WhatsApp": 50, "Instagram": 48}
    assert sum(distribution.values()) == body["records"]
    accounts = {row["platform"]: row["count"] for row in body["account_distribution"]}
    assert sum(accounts.values()) == body["accounts"]


def test_dashboard_activity_returns_buckets(client, auth_headers):
    response = client.get("/api/v1/dashboard/activity?interval=day", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["interval"] == "day"
    assert body["total"] == 150
    assert body["buckets"], "activity chart needs at least one bucket"
    assert sum(bucket["count"] for bucket in body["buckets"]) == 150


def test_dashboard_activity_supports_weekly_buckets(client, auth_headers):
    response = client.get("/api/v1/dashboard/activity?interval=week", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["interval"] == "week"
    assert body["total"] == 150
    assert len(body["buckets"]) < len(
        client.get("/api/v1/dashboard/activity?interval=day", headers=auth_headers).json()["buckets"]
    )


# --------------------------------------------------------------------------------------
# records
# --------------------------------------------------------------------------------------
def test_records_are_listed_with_analysis(client, auth_headers):
    response = client.get("/api/v1/records?page_size=100", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 150
    assert len(body["items"]) == 100
    first = body["items"][0]
    assert first["analysis"] is not None
    assert first["analysis"]["risk_category"] in RISK_CATEGORIES
    assert first["account"]["platform"] in {"Telegram", "WhatsApp", "Instagram"}


def test_records_filter_by_platform_and_risk(client, auth_headers):
    body = client.get("/api/v1/records?platform=Telegram&page_size=100", headers=auth_headers).json()
    assert body["total"] == 52
    assert all(item["account"]["platform"] == "Telegram" for item in body["items"])

    body = client.get("/api/v1/records?risk_category=High&page_size=100", headers=auth_headers).json()
    assert body["total"] == 15
    assert all(item["analysis"]["risk_category"] == "High" for item in body["items"])


def test_records_filter_by_search_and_record_type(client, auth_headers):
    body = client.get("/api/v1/records?record_type=message&page_size=100", headers=auth_headers).json()
    assert body["total"] > 0
    assert all(item["record_type"] == "message" for item in body["items"])

    body = client.get("/api/v1/records?search=catalogue&page_size=100", headers=auth_headers).json()
    assert body["total"] > 0
    assert all("catalogue" in item["content_text"].lower() for item in body["items"])


def test_records_filter_by_date_range(client, auth_headers):
    everything = client.get("/api/v1/records?page_size=100", headers=auth_headers).json()
    stamps = sorted(item["created_at"][:10] for item in everything["items"])
    first_day = stamps[0]

    body = client.get(
        f"/api/v1/records?date_from={first_day}&date_to={first_day}&page_size=100",
        headers=auth_headers,
    ).json()
    assert body["total"] > 0
    assert body["total"] < 150
    assert all(item["created_at"][:10] == first_day for item in body["items"])
    assert body["filters"]["date_from"] == first_day


def test_records_search_matches_username(client, auth_headers):
    body = client.get("/api/v1/records?search=tg_dune&page_size=100", headers=auth_headers).json()
    assert body["total"] >= 1
    assert all(item["account"]["username"] == "tg_dune" for item in body["items"])


def test_records_can_be_sorted_by_recency(client, auth_headers):
    body = client.get("/api/v1/records?sort=created_desc&page_size=100", headers=auth_headers).json()
    stamps = [item["created_at"] for item in body["items"]]
    assert stamps == sorted(stamps, reverse=True)
    body = client.get("/api/v1/records?sort=id_desc&page_size=5", headers=auth_headers).json()
    ids = [item["id"] for item in body["items"]]
    assert ids == sorted(ids, reverse=True)


def test_records_reject_unknown_sort_value(client, auth_headers):
    assert client.get("/api/v1/records?sort=bogus", headers=auth_headers).status_code == 422


def test_record_detail_and_missing_record(client, auth_headers):
    listing = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()
    record_id = listing["items"][0]["id"]
    assert client.get(f"/api/v1/records/{record_id}", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/records/999999", headers=auth_headers).status_code == 404


def test_analysis_run(client, auth_headers):
    listing = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()
    record_id = listing["items"][0]["id"]
    response = client.post(f"/api/v1/analysis/run/{record_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["score"] <= 100
    assert body["risk_category"] == classify_score(body["score"])
    assert body["engine_version"] == ENGINE_VERSION
    assert client.post("/api/v1/analysis/run/999999", headers=auth_headers).status_code == 404


def test_analysis_run_ml_engine(client, auth_headers):
    listing = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()
    record_id = listing["items"][0]["id"]
    response = client.post(
        f"/api/v1/analysis/run/{record_id}?engine=ml", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["score"] <= 100
    assert body["risk_category"] == classify_score(body["score"])
    assert body["engine_version"] == ML_ENGINE_VERSION
    assert body["engine_version"] != ENGINE_VERSION
    assert "ml_probability" in body
    assert 0.0 <= body["ml_probability"] <= 1.0


def test_analysis_run_ml_invalid_record(client, auth_headers):
    assert client.post("/api/v1/analysis/run/999999?engine=ml", headers=auth_headers).status_code == 404


def test_model_info_endpoint(client, auth_headers):
    response = client.get("/api/v1/model/info", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["engine_version"] == ML_ENGINE_VERSION
    assert body["engine_type"] == "offline_ml"
    assert body["model_type"] == "tfidf_logistic_regression"
    assert body["data_mode"] == "synthetic_offline"
    assert body["metrics"] is not None
    assert "held_out_split" in body["metrics"]
    assert "accuracy" in body["metrics"]["held_out_split"]


def test_meta_includes_ml_info(client):
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert "ml_engine_version" in body
    assert body["ml_engine_version"] == ML_ENGINE_VERSION
    assert body["engine_version"] == ENGINE_VERSION
    assert body["ml_engine_version"] != body["engine_version"]
    assert "ml_metrics" in body
    assert body["ml_metrics"] is not None


def test_model_info_requires_auth(client):
    assert client.get("/api/v1/model/info").status_code == 401


def test_compare_engines(client, auth_headers):
    listing = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()
    record_id = listing["items"][0]["id"]
    response = client.get(f"/api/v1/analysis/compare/{record_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["record_id"] == record_id
    assert "agree" in body
    assert isinstance(body["agree"], bool)
    assert body["rule_engine"]["engine_version"] == ENGINE_VERSION
    assert body["ml_engine"]["engine_version"] == ML_ENGINE_VERSION
    assert body["rule_engine"]["engine_version"] != body["ml_engine"]["engine_version"]
    assert 0 <= body["rule_engine"]["score"] <= 100
    assert 0 <= body["ml_engine"]["score"] <= 100
    assert body["rule_engine"]["risk_category"] in {"Low", "Moderate", "Elevated", "High"}
    assert body["ml_engine"]["risk_category"] in {"Low", "Moderate", "Elevated", "High"}
    assert "ml_probability" in body["ml_engine"]
    assert 0.0 <= body["ml_engine"]["ml_probability"] <= 1.0
    assert "positive_features" in body["ml_engine"]
    assert "negative_features" in body["ml_engine"]
    assert "comparison_note" in body
    assert "not averaged" in body["comparison_note"]


def test_compare_engines_requires_auth(client):
    assert client.get("/api/v1/analysis/compare/1").status_code == 401


def test_compare_engines_invalid_record(client, auth_headers):
    assert client.get("/api/v1/analysis/compare/999999", headers=auth_headers).status_code == 404


def test_analysis_run_includes_ml_explanation_fields(client, auth_headers):
    listing = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()
    record_id = listing["items"][0]["id"]
    response = client.post(
        f"/api/v1/analysis/run/{record_id}?engine=ml", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert "ml_positive_features" in body
    assert "ml_negative_features" in body
    for feature in body["ml_positive_features"]:
        assert "id" in feature
        assert "label" in feature
        assert "weight" in feature
        assert "tfidf" in feature
        assert "coef" in feature
        assert feature["weight"] > 0
    for feature in body["ml_negative_features"]:
        assert feature["weight"] < 0


def test_review_disposition_can_be_updated(client, auth_headers):
    listing = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()
    record_id = listing["items"][0]["id"]
    response = client.patch(
        f"/api/v1/records/{record_id}/review",
        json={"review_status": "Reviewed — No Action"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["review_status"] == "Reviewed — No Action"
    invalid = client.patch(
        f"/api/v1/records/{record_id}/review",
        json={"review_status": "Not A Status"},
        headers=auth_headers,
    )
    assert invalid.status_code == 422


# --------------------------------------------------------------------------------------
# cases
# --------------------------------------------------------------------------------------
def test_case_creation_and_detail(client, auth_headers):
    created = client.post(
        "/api/v1/cases",
        json={"title": "Test case", "description": "pytest case", "status": "Open"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    case_id = created.json()["id"]

    listing = client.get("/api/v1/cases", headers=auth_headers).json()
    assert any(case["id"] == case_id for case in listing)

    detail = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()
    assert detail["title"] == "Test case"
    assert detail["records"] == []
    assert detail["notes"] == []

    assert client.get("/api/v1/cases/999999", headers=auth_headers).status_code == 404


def test_case_record_attachment_and_note(client, auth_headers):
    case_id = client.post(
        "/api/v1/cases",
        json={"title": "Attachment case", "description": "", "status": "Open"},
        headers=auth_headers,
    ).json()["id"]
    record_id = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()["items"][0]["id"]

    attached = client.post(
        f"/api/v1/cases/{case_id}/records/{record_id}", headers=auth_headers
    )
    assert attached.status_code == 201
    assert attached.json()["attached"] is True
    repeat = client.post(f"/api/v1/cases/{case_id}/records/{record_id}", headers=auth_headers)
    assert repeat.json()["already_attached"] is True

    note = client.post(
        f"/api/v1/cases/{case_id}/notes",
        json={"note_text": "Synthetic analyst note", "record_id": record_id, "disposition": "Pending Review"},
        headers=auth_headers,
    )
    assert note.status_code == 201

    detail = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()
    assert len(detail["records"]) == 1
    assert len(detail["notes"]) == 1
    assert detail["notes"][0]["note_text"] == "Synthetic analyst note"


def test_note_disposition_can_be_updated_without_duplicating_the_note(client, auth_headers):
    case_id = client.post(
        "/api/v1/cases",
        json={"title": "Disposition case", "description": "", "status": "Open"},
        headers=auth_headers,
    ).json()["id"]
    created = client.post(
        f"/api/v1/cases/{case_id}/notes",
        json={"note_text": "Single note", "disposition": "Pending Review"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    note_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/cases/{case_id}/notes/{note_id}",
        json={"note_text": "Single note", "disposition": "Reviewed — No Action"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["disposition"] == "Reviewed — No Action"

    detail = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()
    assert len(detail["notes"]) == 1
    assert detail["notes"][0]["disposition"] == "Reviewed — No Action"

    missing = client.patch(
        f"/api/v1/cases/{case_id}/notes/999999",
        json={"note_text": "nope", "disposition": "Pending Review"},
        headers=auth_headers,
    )
    assert missing.status_code == 404


def test_case_update(client, auth_headers):
    case_id = client.post(
        "/api/v1/cases",
        json={"title": "Status case", "description": "", "status": "Open"},
        headers=auth_headers,
    ).json()["id"]
    updated = client.patch(
        f"/api/v1/cases/{case_id}",
        json={"title": "Status case", "description": "closed by pytest", "status": "Closed"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "Closed"


# --------------------------------------------------------------------------------------
# graph
# --------------------------------------------------------------------------------------
def test_graph_contains_enriched_nodes_and_edges(client, auth_headers):
    response = client.get("/api/v1/graph", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["nodes"]) == 75
    assert body["edges"], "the seeded corpus must contain relationship edges"
    node = body["nodes"][0]
    assert node["id"].startswith("account-")
    assert node["risk_category"] in RISK_CATEGORIES
    assert node["record_count"] >= 0
    assert isinstance(node["record_ids"], list)
    edge = body["edges"][0]
    assert edge["source"].startswith("account-")
    assert edge["target"].startswith("account-")
    assert edge["evidence_description"]


def test_graph_node_detail_exposes_records_and_relationships(client, auth_headers):
    graph = client.get("/api/v1/graph", headers=auth_headers).json()
    target = next(node for node in graph["nodes"] if node["record_count"] > 0)
    response = client.get(f"/api/v1/graph/nodes/{target['account_id']}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == target["account_id"]
    assert body["record_count"] == len(body["records"])
    assert body["risk_category"] in RISK_CATEGORIES
    assert "content_preview" in body["records"][0]
    assert isinstance(body["relationships"], list)
    assert client.get("/api/v1/graph/nodes/999999", headers=auth_headers).status_code == 404


def test_graph_edge_detail(client, auth_headers):
    graph = client.get("/api/v1/graph", headers=auth_headers).json()
    edge_id = graph["edges"][0]["id"]
    response = client.get(f"/api/v1/graph/edges/{edge_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == edge_id
    assert body["source_label"]
    assert body["target_label"]
    assert body["evidence_description"]
    assert client.get("/api/v1/graph/edges/999999", headers=auth_headers).status_code == 404


# --------------------------------------------------------------------------------------
# seeding and analysis rules
# --------------------------------------------------------------------------------------
def test_seed_is_idempotent(client, auth_headers):
    before = client.get("/api/v1/dashboard/summary", headers=auth_headers).json()
    before_cases = client.get("/api/v1/cases", headers=auth_headers).json()
    response = client.post("/api/v1/demo/seed", headers=auth_headers)
    assert response.status_code == 200
    after = client.get("/api/v1/dashboard/summary", headers=auth_headers).json()
    after_cases = client.get("/api/v1/cases", headers=auth_headers).json()
    assert before["records"] == after["records"] == 150
    assert before["accounts"] == after["accounts"] == 75
    assert before["cases"] == after["cases"]
    assert len(before_cases) == len(after_cases)
    assert {case["id"] for case in before_cases} == {case["id"] for case in after_cases}


def test_rule_engine_thresholds():
    assert classify_score(0) == "Low"
    assert classify_score(24) == "Low"
    assert classify_score(25) == "Moderate"
    assert classify_score(49) == "Moderate"
    assert classify_score(50) == "Elevated"
    assert classify_score(74) == "Elevated"
    assert classify_score(75) == "High"
    assert classify_score(100) == "High"


def test_rule_engine_flags_indicators_and_benign_context():
    risky = analyze_text("Orders available, ship to postcode, 20 packs, crypto payment, dm me.")
    assert risky["score"] >= 75
    assert risky["risk_category"] == "High"
    assert {match["id"] for match in risky["matched_indicators"]} >= {
        "contact_handoff",
        "payment_method",
        "shipping_destination",
    }

    benign = analyze_text("Community anti-drug awareness campaign about recovery and prevention.")
    assert benign["risk_category"] == "Low"
    assert benign["score"] < 25


def test_rule_engine_is_deterministic():
    text = "Catalogue update and DM for details, 10 packs, delivery on Friday."
    assert analyze_text(text) == analyze_text(text)


def test_app_exposes_expected_route_count():
    paths = set(app.openapi()["paths"])
    for path in (
        "/health",
        "/api/v1/auth/login",
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/activity",
        "/api/v1/graph",
    ):
        assert path in paths


# --------------------------------------------------------------------------------------
# ML metrics structure
# --------------------------------------------------------------------------------------
def test_meta_ml_metrics_nested_structure(client):
    """Meta endpoint exposes nested held-out and challenge-set metrics."""
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    metrics = body["ml_metrics"]
    assert metrics is not None
    # Held-out split metrics
    held_out = metrics["held_out_split"]
    for key in {"accuracy", "precision_macro", "recall_macro", "f1_macro", "confusion_matrix", "per_class"}:
        assert key in held_out, f"missing held_out_split key: {key}"
    # Challenge set metrics
    challenge = metrics["challenge_set"]
    for key in {"accuracy", "precision_macro", "recall_macro", "f1_macro", "confusion_matrix", "per_class"}:
        assert key in challenge, f"missing challenge_set key: {key}"
    # No top-level accuracy shortcut (must use nested structure)
    assert "accuracy" not in metrics or metrics["accuracy"] is None


def test_model_info_metrics_structure(client, auth_headers):
    """Model info endpoint exposes full nested metrics."""
    response = client.get("/api/v1/model/info", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    metrics = body["metrics"]
    assert "held_out_split" in metrics
    assert "challenge_set" in metrics
    assert "note" in metrics
    assert metrics["held_out_split"]["accuracy"] <= 1.0
    assert metrics["challenge_set"]["accuracy"] <= 1.0


# --------------------------------------------------------------------------------------
# Note validation and persistence
# --------------------------------------------------------------------------------------
def test_save_note_empty_text_rejected(client, auth_headers):
    """Empty note text is rejected with 422."""
    case_id = client.post(
        "/api/v1/cases",
        json={"title": "Note validation case", "description": "", "status": "Open"},
        headers=auth_headers,
    ).json()["id"]

    response = client.post(
        f"/api/v1/cases/{case_id}/notes",
        json={"note_text": "", "record_id": None, "disposition": "Pending Review"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_save_note_whitespace_rejected(client, auth_headers):
    """Whitespace-only note text is rejected with 422."""
    case_id = client.post(
        "/api/v1/cases",
        json={"title": "Whitespace case", "description": "", "status": "Open"},
        headers=auth_headers,
    ).json()["id"]

    response = client.post(
        f"/api/v1/cases/{case_id}/notes",
        json={"note_text": "   ", "record_id": None, "disposition": "Pending Review"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_save_note_persists_after_refetch(client, auth_headers):
    """A saved note survives a re-fetch of the case detail."""
    case_id = client.post(
        "/api/v1/cases",
        json={"title": "Persistence case", "description": "", "status": "Open"},
        headers=auth_headers,
    ).json()["id"]
    record_id = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()["items"][0]["id"]

    created = client.post(
        f"/api/v1/cases/{case_id}/notes",
        json={"note_text": "Persistent analyst observation", "record_id": record_id, "disposition": "Pending Review"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    note_id = created.json()["id"]

    detail = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers).json()
    saved = [n for n in detail["notes"] if n["id"] == note_id]
    assert len(saved) == 1
    assert saved[0]["note_text"] == "Persistent analyst observation"
    assert saved[0]["record_id"] == record_id


def test_save_note_invalid_case_404(client, auth_headers):
    """Saving a note to a nonexistent case returns 404."""
    response = client.post(
        "/api/v1/cases/999999/notes",
        json={"note_text": "Valid note text", "record_id": None, "disposition": "Pending Review"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------------------
# Add to case edge cases
# --------------------------------------------------------------------------------------
def test_add_to_case_invalid_case_404(client, auth_headers):
    """Attaching to a nonexistent case returns 404."""
    record_id = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()["items"][0]["id"]
    response = client.post(
        "/api/v1/cases/999999/records/1", headers=auth_headers
    )
    # The endpoint checks case first; 999999 case does not exist
    assert response.status_code == 404


def test_add_to_case_nonexistent_record_404(client, auth_headers):
    """Attaching a nonexistent record returns 404."""
    case_id = client.post(
        "/api/v1/cases",
        json={"title": "Record check case", "description": "", "status": "Open"},
        headers=auth_headers,
    ).json()["id"]
    response = client.post(
        f"/api/v1/cases/{case_id}/records/999999", headers=auth_headers
    )
    assert response.status_code == 404


def test_add_to_case_duplicate_handled_gracefully(client, auth_headers):
    """Attaching the same record twice returns already_attached=True on the second."""
    case_id = client.post(
        "/api/v1/cases",
        json={"title": "Duplicate attachment case", "description": "", "status": "Open"},
        headers=auth_headers,
    ).json()["id"]
    record_id = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()["items"][0]["id"]

    first = client.post(f"/api/v1/cases/{case_id}/records/{record_id}", headers=auth_headers)
    assert first.status_code == 201
    assert first.json()["already_attached"] is False

    second = client.post(f"/api/v1/cases/{case_id}/records/{record_id}", headers=auth_headers)
    assert second.status_code == 201
    assert second.json()["already_attached"] is True


# --------------------------------------------------------------------------------------
# Both engines on same record
# --------------------------------------------------------------------------------------
def test_record_shows_both_engine_results(client, auth_headers):
    """Running both engines on a record yields separate results with agreement status."""
    listing = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()
    record_id = listing["items"][0]["id"]

    # Run both engines via the compare endpoint
    response = client.get(f"/api/v1/analysis/compare/{record_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()

    # Rule engine result present
    rule = body["rule_engine"]
    assert rule["engine_version"] == "rules-1.1"
    assert 0 <= rule["score"] <= 100
    assert rule["risk_category"] in {"Low", "Moderate", "Elevated", "High"}

    # ML engine result present
    ml = body["ml_engine"]
    assert ml["engine_version"] == "ml-tfidf-logreg-v1.0"
    assert 0 <= ml["score"] <= 100
    assert ml["risk_category"] in {"Low", "Moderate", "Elevated", "High"}
    assert "ml_probability" in ml
    assert 0.0 <= ml["ml_probability"] <= 1.0

    # Agreement flag present and boolean
    assert isinstance(body["agree"], bool)

    # No combined score
    assert "combined_score" not in body
    assert "averaged_score" not in body


# --------------------------------------------------------------------------------------
# Review disposition persistence
# --------------------------------------------------------------------------------------
def test_review_disposition_persists_after_refetch(client, auth_headers):
    """Changing review status persists and is visible on re-fetch."""
    listing = client.get("/api/v1/records?page_size=1", headers=auth_headers).json()
    record_id = listing["items"][0]["id"]

    updated = client.patch(
        f"/api/v1/records/{record_id}/review",
        json={"review_status": "Further Review Required"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["review_status"] == "Further Review Required"

    # Re-fetch the record listing and confirm the status persisted
    listing2 = client.get(f"/api/v1/records?page_size=1&search=", headers=auth_headers).json()
    # The specific record should show the updated status
    record_detail = client.get(f"/api/v1/records/{record_id}", headers=auth_headers).json()
    assert record_detail["review_status"] == "Further Review Required"
