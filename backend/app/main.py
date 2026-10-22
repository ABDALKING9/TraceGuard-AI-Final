import json
import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from .auth import authenticate, create_access_token, require_session, revoke_access_token
from .config import CORS_ORIGINS, DEMO_EMAIL, using_default_secret
from .db.database import Base, engine, get_db, migrate
from .models import (
    Account,
    Analysis,
    AnalystNote,
    Case,
    CaseRecord,
    ContentRecord,
    Platform,
    RelationshipEdge,
)
from .schemas.api import (
    CaseCreate,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    NoteCreate,
    ReviewUpdate,
)
from .services.analysis import ENGINE_VERSION, RISK_CATEGORIES, RISK_THRESHOLDS, analyze_text, classify_score, encode_analysis
from .services.ml_analysis import (
    ML_ENGINE_VERSION as ML_ENGINE_VERSION,
    analyze_text as analyze_text_ml,
    classify_score as classify_score_ml,
    encode_analysis as encode_analysis_ml,
    get_cached_metrics as get_ml_metrics,
)
from .data.ml_training_data import TRAINING_VERSION

logger = logging.getLogger("traceguard")

Base.metadata.create_all(bind=engine)
migrate()

app = FastAPI(
    title="TraceGuard AI API",
    version="1.1.0",
    description=(
        "Offline academic prototype using synthetic data only. "
        "All application endpoints require a bearer token obtained from "
        "/api/v1/auth/login."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if using_default_secret():
    logger.warning(
        "TRACEGUARD_SECRET_KEY is not set; the local demonstration signing key is in use. "
        "Set the environment variable before any non-local deployment."
    )

# Endpoints that stay reachable without a session token.
public_root = APIRouter()
public_api = APIRouter(prefix="/api/v1")
# Everything below /api/v1 that is not explicitly public requires a session token.
api = APIRouter(prefix="/api/v1", dependencies=[Depends(require_session)])


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def _latest_analysis_subquery():
    """Latest analysis row per record (highest analysis id wins)."""
    return (
        select(
            Analysis.record_id.label("record_id"),
            Analysis.score.label("score"),
            Analysis.risk_category.label("risk_category"),
            Analysis.matched_indicators_json.label("matched_indicators_json"),
            Analysis.explanation_json.label("explanation_json"),
            Analysis.engine_version.label("engine_version"),
            Analysis.analyzed_at.label("analyzed_at"),
        )
        .where(Analysis.id.in_(select(func.max(Analysis.id)).group_by(Analysis.record_id)))
        .subquery()
    )


def record_dict(record: ContentRecord, db: Session) -> dict:
    analysis = db.scalar(
        select(Analysis).where(Analysis.record_id == record.id).order_by(Analysis.id.desc())
    )
    return {
        "id": record.id,
        "record_type": record.record_type,
        "content_text": record.content_text,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "review_status": record.review_status,
        "is_synthetic": record.is_synthetic,
        "account": {
            "id": record.account.id,
            "username": record.account.username,
            "display_name": record.account.display_name,
            "platform": record.account.platform.name,
        },
        "analysis": (
            {
                "score": analysis.score,
                "risk_category": analysis.risk_category,
                "matched_indicators": json.loads(analysis.matched_indicators_json),
                "explanations": json.loads(analysis.explanation_json),
                "engine_version": analysis.engine_version,
                "ml_probability": analysis.ml_probability,
                "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
            }
            if analysis
            else None
        ),
    }


def _record_preview(text: str, limit: int = 180) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


# --------------------------------------------------------------------------------------
# public endpoints
# --------------------------------------------------------------------------------------
@public_root.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok", "database": "connected", "data_mode": "synthetic_offline"}


@public_api.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    if not authenticate(payload.email, payload.password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    token, expires_at, ttl = create_access_token(payload.email.strip().lower())
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at.isoformat(),
        expires_in_minutes=ttl,
        user={"email": payload.email.strip().lower(), "role": "demonstration operator"},
    )


@public_api.post("/auth/logout", response_model=LogoutResponse)
def logout(authorization: str | None = Header(default=None)):
    """Revoke the supplied token.  Safe to call without a valid session."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return LogoutResponse(revoked=False)
    return LogoutResponse(revoked=revoke_access_token(authorization.split(" ", 1)[1].strip()))


@public_api.get("/auth/session")
def session_info(session: dict = Depends(require_session)):
    """Validate a stored token so the frontend can restore a session."""
    return {
        "user": {"email": session.get("sub"), "role": "demonstration operator"},
        "expires_at": datetime.fromtimestamp(session.get("exp", 0)).isoformat(),
        "engine_version": ENGINE_VERSION,
    }


@api.get("/model/info")
def model_info():
    """Public metadata about the offline ML classifier (distinct from the rule engine)."""
    metrics = get_ml_metrics()
    return {
        "engine_version": ML_ENGINE_VERSION,
        "engine_type": "offline_ml",
        "model_type": "tfidf_logistic_regression",
        "data_mode": "synthetic_offline",
        "training_version": TRAINING_VERSION,
        "metrics": metrics,
        "methodology_principle": (
            "The ML classifier is a synthetic-data offline demonstration. TF-IDF vectorization "
            "plus LogisticRegression produces a predicted-class probability output (confidence-like "
            "score) mapped to a 0-100 review priority score. It is not evidence of wrongdoing and "
            "requires human review. Not a calibrated probability of criminal activity."
        ),
    }


@public_api.get("/meta")
def meta():
    """Public metadata describing the synthetic data mode and the risk vocabulary."""
    ml_metrics = get_ml_metrics()
    return {
        "app": "TraceGuard AI",
        "version": app.version,
        "data_mode": "synthetic_offline",
        "engine_version": ENGINE_VERSION,
        "ml_engine_version": ML_ENGINE_VERSION,
        "risk_categories": RISK_CATEGORIES,
        "risk_thresholds": RISK_THRESHOLDS,
        "ml_metrics": ml_metrics,
        "methodology_principle": (
            "TraceGuard AI is a synthetic-data research demonstration. Rule-based scores "
            "rank records for human review; a score is not a probability and never evidence "
            "that an account is involved in criminal activity. The optional ML classifier "
            "produces a predicted-class probability output from a synthetic labelled corpus, "
            "also for review prioritization only."
        ),
        "synthetic_data_notice": (
            "Every account, content record, case and relationship in this instance is "
            "synthetic and offline. No real platform data is collected, stored or analysed."
        ),
        "demo_auth": {
            "enabled": True,
            "mode": "local demonstration credential",
            "email": DEMO_EMAIL,
            "note": "Local demo only. Replace with a real identity provider before any deployment.",
        },
    }


# --------------------------------------------------------------------------------------
# protected endpoints
# --------------------------------------------------------------------------------------
@api.get("/platforms")
def platforms(db: Session = Depends(get_db)):
    return [
        {"id": p.id, "name": p.name, "is_simulated": p.is_simulated}
        for p in db.scalars(select(Platform).order_by(Platform.name)).all()
    ]


@api.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    records = db.scalar(select(func.count(ContentRecord.id))) or 0
    accounts = db.scalar(select(func.count(Account.id))) or 0
    cases = db.scalar(select(func.count(Case.id))) or 0
    pending = (
        db.scalar(
            select(func.count(ContentRecord.id)).where(ContentRecord.review_status == "Pending Review")
        )
        or 0
    )

    latest = _latest_analysis_subquery()
    risk_rows = db.execute(
        select(latest.c.risk_category, func.count(ContentRecord.id))
        .select_from(ContentRecord)
        .join(latest, latest.c.record_id == ContentRecord.id)
        .group_by(latest.c.risk_category)
    ).all()
    risk_counts = {category: 0 for category in RISK_CATEGORIES}
    for category, count in risk_rows:
        risk_counts[category] = risk_counts.get(category, 0) + count

    platform_rows = db.execute(
        select(Platform.name, func.count(ContentRecord.id))
        .select_from(Platform)
        .outerjoin(Account, Account.platform_id == Platform.id)
        .outerjoin(ContentRecord, ContentRecord.account_id == Account.id)
        .group_by(Platform.name)
        .order_by(Platform.name)
    ).all()
    account_rows = db.execute(
        select(Platform.name, func.count(Account.id))
        .select_from(Platform)
        .outerjoin(Account, Account.platform_id == Platform.id)
        .group_by(Platform.name)
        .order_by(Platform.name)
    ).all()

    return {
        "records": records,
        "accounts": accounts,
        "cases": cases,
        "pending_review": pending,
        "risk_distribution": [
            {"category": category, "count": risk_counts[category]} for category in RISK_CATEGORIES
        ],
        "platform_distribution": [
            {"platform": platform, "count": count} for platform, count in platform_rows
        ],
        "account_distribution": [
            {"platform": platform, "count": count} for platform, count in account_rows
        ],
        "risk_basis": "latest analysis per record",
        "platform_basis": "content records per platform",
        "data_mode": "Synthetic Data — Offline Demo",
    }


@api.get("/dashboard/activity")
def dashboard_activity(
    interval: str = Query("day", pattern="^(day|week)$"),
    db: Session = Depends(get_db),
):
    """Record volume over time, used by the dashboard activity chart."""
    if interval == "week":
        bucket_expr = func.date(
            ContentRecord.created_at,
            func.printf("-%d days", (func.strftime("%w", ContentRecord.created_at) + 6) % 7),
        )
    else:
        bucket_expr = func.date(ContentRecord.created_at)

    rows = db.execute(
        select(bucket_expr.label("bucket"), func.count(ContentRecord.id))
        .group_by(bucket_expr)
        .order_by(bucket_expr)
    ).all()

    counts = {}
    for bucket, count in rows:
        counts[str(bucket)] = count

    if counts:
        start = min(datetime.fromisoformat(k).date() for k in counts)
        end = max(datetime.fromisoformat(k).date() for k in counts)
        step = timedelta(days=7 if interval == "week" else 1)
        buckets = []
        cursor = start
        while cursor <= end:
            buckets.append({"bucket": cursor.isoformat(), "count": counts.get(cursor.isoformat(), 0)})
            cursor += step
    else:
        buckets = []

    return {
        "interval": interval,
        "buckets": buckets,
        "total": sum(counts.values()),
        "distinct_buckets": len(counts),
        "data_mode": "Synthetic Data — Offline Demo",
    }


@api.get("/records")
def list_records(
    search: str = "",
    platform: str = "",
    record_type: str = "",
    risk_category: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    sort: str = Query("id_asc", pattern="^(id_asc|id_desc|created_desc|created_asc)$"),
    db: Session = Depends(get_db),
):
    stmt = select(ContentRecord).options(
        joinedload(ContentRecord.account).joinedload(Account.platform)
    )
    if sort == "id_desc":
        stmt = stmt.order_by(ContentRecord.id.desc())
    elif sort == "created_desc":
        stmt = stmt.order_by(ContentRecord.created_at.desc(), ContentRecord.id.desc())
    elif sort == "created_asc":
        stmt = stmt.order_by(ContentRecord.created_at.asc(), ContentRecord.id.asc())
    else:
        stmt = stmt.order_by(ContentRecord.id)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.join(Account, Account.id == ContentRecord.account_id).where(
            or_(ContentRecord.content_text.ilike(pattern), Account.username.ilike(pattern))
        )
    if platform:
        stmt = stmt.join(Account, Account.id == ContentRecord.account_id).join(
            Platform, Platform.id == Account.platform_id
        ).where(Platform.name.ilike(platform))
    if record_type in {"post", "message"}:
        stmt = stmt.where(ContentRecord.record_type == record_type)
    if date_from is not None:
        stmt = stmt.where(func.date(ContentRecord.created_at) >= date_from.isoformat())
    if date_to is not None:
        stmt = stmt.where(func.date(ContentRecord.created_at) <= date_to.isoformat())
    if risk_category:
        latest = _latest_analysis_subquery()
        stmt = stmt.join(latest, latest.c.record_id == ContentRecord.id).where(
            latest.c.risk_category == risk_category
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all()
    output = [record_dict(r, db) for r in rows]
    return {
        "items": output,
        "total": total,
        "page": page,
        "page_size": page_size,
        "filters": {
            "search": search,
            "platform": platform,
            "record_type": record_type,
            "risk_category": risk_category,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "sort": sort,
        },
    }


@api.get("/records/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)):
    record = db.scalar(
        select(ContentRecord)
        .options(joinedload(ContentRecord.account).joinedload(Account.platform))
        .where(ContentRecord.id == record_id)
    )
    if not record:
        raise HTTPException(404, "Record not found")
    return record_dict(record, db)


@api.post("/analysis/run/{record_id}")
def run_analysis(
    record_id: int,
    engine: str = Query("rules", pattern="^(rules|ml)$"),
    db: Session = Depends(get_db),
):
    record = db.get(ContentRecord, record_id)
    if not record:
        raise HTTPException(404, "Record not found")
    if engine == "ml":
        result = analyze_text_ml(record.content_text)
        matched, explanations = encode_analysis_ml(result)
        ml_probability = result.get("ml_probability")
        engine_version = ML_ENGINE_VERSION
        ml_positive = result.get("ml_positive_features", [])
        ml_negative = result.get("ml_negative_features", [])
    else:
        result = analyze_text(record.content_text)
        matched, explanations = encode_analysis(result)
        ml_probability = None
        engine_version = ENGINE_VERSION
        ml_positive = None
        ml_negative = None
    analysis = Analysis(
        record_id=record.id,
        score=result["score"],
        risk_category=result["risk_category"],
        engine_version=engine_version,
        ml_probability=ml_probability,
        matched_indicators_json=matched,
        explanation_json=explanations,
    )
    db.add(analysis)
    db.commit()
    payload = {"record_id": record.id, **result, "ml_probability": ml_probability}
    if ml_positive is not None:
        payload["ml_positive_features"] = ml_positive
        payload["ml_negative_features"] = ml_negative
    return payload


@api.get("/analysis/compare/{record_id}")
def compare_engines(record_id: int, db: Session = Depends(get_db)):
    """Run both engines on the same record and return side-by-side results.

    Preserves each engine's original output and flags category agreement.
    Does not average scores or create a combined risk score.
    """
    record = db.get(ContentRecord, record_id)
    if not record:
        raise HTTPException(404, "Record not found")

    rules_result = analyze_text(record.content_text)
    ml_result = analyze_text_ml(record.content_text)

    rules_matched, rules_explanations = encode_analysis(rules_result)
    ml_matched, ml_explanations = encode_analysis_ml(ml_result)

    rules_analysis = Analysis(
        record_id=record.id,
        score=rules_result["score"],
        risk_category=rules_result["risk_category"],
        engine_version=ENGINE_VERSION,
        ml_probability=None,
        matched_indicators_json=rules_matched,
        explanation_json=rules_explanations,
    )
    ml_analysis = Analysis(
        record_id=record.id,
        score=ml_result["score"],
        risk_category=ml_result["risk_category"],
        engine_version=ML_ENGINE_VERSION,
        ml_probability=ml_result.get("ml_probability"),
        matched_indicators_json=ml_matched,
        explanation_json=ml_explanations,
    )
    db.add(rules_analysis)
    db.add(ml_analysis)
    db.commit()

    agree = rules_result["risk_category"] == ml_result["risk_category"]

    return {
        "record_id": record.id,
        "content_text": record.content_text,
        "agree": agree,
        "rule_engine": {
            "engine_version": ENGINE_VERSION,
            "score": rules_result["score"],
            "risk_category": rules_result["risk_category"],
            "matched_indicators": rules_result["matched_indicators"],
            "explanations": rules_result["explanations"],
        },
        "ml_engine": {
            "engine_version": ML_ENGINE_VERSION,
            "score": ml_result["score"],
            "risk_category": ml_result["risk_category"],
            "ml_probability": ml_result.get("ml_probability"),
            "matched_indicators": ml_result["matched_indicators"],
            "positive_features": ml_result.get("ml_positive_features", []),
            "negative_features": ml_result.get("ml_negative_features", []),
            "explanations": ml_result["explanations"],
        },
        "comparison_note": (
            "Agreement means both engines assigned the same risk category; "
            "disagreement is a reason to inspect context, not proof of wrongdoing. "
            "Scores are not averaged and no combined score is produced."
        ),
    }


@api.get("/cases")
def list_cases(db: Session = Depends(get_db)):
    cases = db.scalars(select(Case).order_by(Case.id)).all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "status": c.status,
            "record_count": len(c.records),
            "created_at": c.created_at.isoformat(),
        }
        for c in cases
    ]


@api.post("/cases", status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    case = Case(title=payload.title, description=payload.description, status=payload.status)
    db.add(case)
    db.commit()
    db.refresh(case)
    return {"id": case.id, "title": case.title, "description": case.description, "status": case.status}


@api.get("/cases/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return {
        "id": case.id,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "records": [record_dict(link.record, db) for link in case.records],
        "notes": [
            {
                "id": n.id,
                "record_id": n.record_id,
                "note_text": n.note_text,
                "disposition": n.disposition,
                "created_at": n.created_at.isoformat(),
            }
            for n in case.notes
        ],
    }


@api.patch("/cases/{case_id}")
def update_case(case_id: int, payload: CaseCreate, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    case.title, case.description, case.status = payload.title, payload.description, payload.status
    db.commit()
    return {"id": case.id, "title": case.title, "description": case.description, "status": case.status}


@api.post("/cases/{case_id}/records/{record_id}", status_code=201)
def attach_record(case_id: int, record_id: int, db: Session = Depends(get_db)):
    case, record = db.get(Case, case_id), db.get(ContentRecord, record_id)
    if not case or not record:
        raise HTTPException(404, "Case or record not found")
    existing = db.scalar(
        select(CaseRecord).where(CaseRecord.case_id == case_id, CaseRecord.record_id == record_id)
    )
    if existing:
        return {"attached": True, "already_attached": True}
    db.add(CaseRecord(case_id=case_id, record_id=record_id))
    db.commit()
    return {"attached": True, "already_attached": False}


@api.post("/cases/{case_id}/notes", status_code=201)
def add_note(case_id: int, payload: NoteCreate, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "Case not found")
    if payload.record_id is not None and not db.get(ContentRecord, payload.record_id):
        raise HTTPException(404, "Record not found")
    note = AnalystNote(
        case_id=case_id,
        record_id=payload.record_id,
        note_text=payload.note_text,
        disposition=payload.disposition,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {
        "id": note.id,
        "case_id": case_id,
        "record_id": note.record_id,
        "note_text": note.note_text,
        "disposition": note.disposition,
    }


@api.patch("/cases/{case_id}/notes/{note_id}")
def update_note(case_id: int, note_id: int, payload: NoteCreate, db: Session = Depends(get_db)):
    """Update the disposition (and optionally the text) of an existing analyst note."""
    if not db.get(Case, case_id):
        raise HTTPException(404, "Case not found")
    note = db.get(AnalystNote, note_id)
    if not note or note.case_id != case_id:
        raise HTTPException(404, "Note not found")
    note.note_text = payload.note_text
    note.disposition = payload.disposition
    if payload.record_id is not None and not db.get(ContentRecord, payload.record_id):
        raise HTTPException(404, "Record not found")
    note.record_id = payload.record_id
    db.commit()
    db.refresh(note)
    return {
        "id": note.id,
        "case_id": note.case_id,
        "record_id": note.record_id,
        "note_text": note.note_text,
        "disposition": note.disposition,
        "created_at": note.created_at.isoformat(),
    }


@api.patch("/records/{record_id}/review")
def update_review(record_id: int, payload: ReviewUpdate, db: Session = Depends(get_db)):
    record = db.get(ContentRecord, record_id)
    if not record:
        raise HTTPException(404, "Record not found")
    record.review_status = payload.review_status
    db.commit()
    return {"id": record.id, "review_status": record.review_status}


@api.get("/graph")
def graph(db: Session = Depends(get_db)):
    """Relationship graph enriched with per-account risk and record metadata."""
    accounts = db.scalars(select(Account).options(joinedload(Account.platform)).order_by(Account.id)).all()
    edges = db.scalars(select(RelationshipEdge).order_by(RelationshipEdge.id)).all()

    latest = _latest_analysis_subquery()
    account_rows = db.execute(
        select(
            Account.id,
            func.count(ContentRecord.id),
            func.max(latest.c.score),
        )
        .select_from(Account)
        .outerjoin(ContentRecord, ContentRecord.account_id == Account.id)
        .outerjoin(latest, latest.c.record_id == ContentRecord.id)
        .group_by(Account.id)
    ).all()
    stats = {row[0]: (row[1], row[2]) for row in account_rows}

    record_ids = db.execute(
        select(ContentRecord.account_id, ContentRecord.id).order_by(ContentRecord.id)
    ).all()
    by_account: dict[int, list[int]] = {}
    for account_id, record_id in record_ids:
        by_account.setdefault(account_id, []).append(record_id)

    degree: dict[int, int] = {}
    for edge in edges:
        degree[edge.source_account_id] = degree.get(edge.source_account_id, 0) + 1
        degree[edge.target_account_id] = degree.get(edge.target_account_id, 0) + 1

    nodes = []
    for account in accounts:
        record_count, top_score = stats.get(account.id, (0, None))
        score = int(top_score) if top_score is not None else 0
        nodes.append(
            {
                "id": f"account-{account.id}",
                "account_id": account.id,
                "label": account.username,
                "display_name": account.display_name,
                "platform": account.platform.name,
                "account_type": account.account_type,
                "synthetic": account.is_synthetic,
                "created_at": account.created_at.isoformat() if account.created_at else None,
                "record_count": record_count,
                "record_ids": by_account.get(account.id, []),
                "risk_score": score,
                "risk_category": classify_score(score),
                "connection_count": degree.get(account.id, 0),
            }
        )

    return {
        "nodes": nodes,
        "edges": [
            {
                "id": e.id,
                "source": f"account-{e.source_account_id}",
                "target": f"account-{e.target_account_id}",
                "relationship_type": e.relationship_type,
                "shared_feature": e.shared_feature,
                "evidence_description": e.evidence_description,
                "synthetic": e.is_synthetic,
            }
            for e in edges
        ],
        "risk_categories": RISK_CATEGORIES,
        "engine_version": ENGINE_VERSION,
    }


@api.get("/graph/nodes/{account_id}")
def graph_node(account_id: int, db: Session = Depends(get_db)):
    """Full detail for a single graph node: metadata, risk, records and evidence."""
    account = db.scalar(
        select(Account).options(joinedload(Account.platform)).where(Account.id == account_id)
    )
    if not account:
        raise HTTPException(404, "Account not found")

    records = db.scalars(
        select(ContentRecord)
        .options(joinedload(ContentRecord.account))
        .where(ContentRecord.account_id == account_id)
        .order_by(ContentRecord.id)
    ).all()
    record_payload = []
    top_score = 0
    for record in records:
        payload = record_dict(record, db)
        score = payload["analysis"]["score"] if payload["analysis"] else 0
        top_score = max(top_score, score)
        payload["content_preview"] = _record_preview(record.content_text)
        record_payload.append(payload)

    edges = db.scalars(
        select(RelationshipEdge).where(
            (RelationshipEdge.source_account_id == account_id)
            | (RelationshipEdge.target_account_id == account_id)
        )
    ).all()
    edge_payload = []
    for edge in edges:
        counterpart = (
            edge.target_account_id if edge.source_account_id == account_id else edge.source_account_id
        )
        other = db.get(Account, counterpart)
        edge_payload.append(
            {
                "id": edge.id,
                "direction": "outgoing" if edge.source_account_id == account_id else "incoming",
                "counterpart_account_id": counterpart,
                "counterpart_label": other.username if other else None,
                "counterpart_platform": other.platform.name if other and other.platform else None,
                "relationship_type": edge.relationship_type,
                "shared_feature": edge.shared_feature,
                "evidence_description": edge.evidence_description,
                "synthetic": edge.is_synthetic,
            }
        )

    return {
        "id": f"account-{account.id}",
        "account_id": account.id,
        "label": account.username,
        "display_name": account.display_name,
        "platform": account.platform.name,
        "account_type": account.account_type,
        "synthetic": account.is_synthetic,
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "record_count": len(record_payload),
        "risk_score": top_score,
        "risk_category": classify_score(top_score),
        "records": record_payload,
        "relationships": edge_payload,
    }


@api.get("/graph/edges/{edge_id}")
def graph_edge(edge_id: int, db: Session = Depends(get_db)):
    """Full detail for a single relationship edge, including both endpoints."""
    edge = db.get(RelationshipEdge, edge_id)
    if not edge:
        raise HTTPException(404, "Relationship not found")
    source = db.scalar(
        select(Account).options(joinedload(Account.platform)).where(Account.id == edge.source_account_id)
    )
    target = db.scalar(
        select(Account).options(joinedload(Account.platform)).where(Account.id == edge.target_account_id)
    )
    return {
        "id": edge.id,
        "source": f"account-{edge.source_account_id}",
        "target": f"account-{edge.target_account_id}",
        "source_label": source.username if source else None,
        "source_platform": source.platform.name if source and source.platform else None,
        "target_label": target.username if target else None,
        "target_platform": target.platform.name if target and target.platform else None,
        "relationship_type": edge.relationship_type,
        "shared_feature": edge.shared_feature,
        "evidence_description": edge.evidence_description,
        "synthetic": edge.is_synthetic,
    }


@api.post("/demo/seed")
def seed_demo():
    from .seed import seed

    return seed()


app.include_router(public_root)
app.include_router(public_api)
app.include_router(api)
