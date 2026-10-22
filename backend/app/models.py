from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Platform(Base):
    __tablename__ = "platforms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    accounts: Mapped[list["Account"]] = relationship(back_populates="platform")

class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("platform_id", "username", name="uq_account_platform_username"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"))
    username: Mapped[str] = mapped_column(String(80))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    account_type: Mapped[str] = mapped_column(String(30), default="user")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    platform: Mapped["Platform"] = relationship(back_populates="accounts")
    records: Mapped[list["ContentRecord"]] = relationship(back_populates="account")

class ContentRecord(Base):
    __tablename__ = "content_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    record_type: Mapped[str] = mapped_column(String(20))  # post or message
    content_text: Mapped[str] = mapped_column(Text)
    conversation_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    review_status: Mapped[str] = mapped_column(String(40), default="Pending Review")
    account: Mapped["Account"] = relationship(back_populates="records")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="record", cascade="all, delete-orphan")

class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("content_records.id"))
    score: Mapped[int] = mapped_column(Integer)
    risk_category: Mapped[str] = mapped_column(String(20))
    engine_version: Mapped[str] = mapped_column(String(30), default="rules-1.0")
    matched_indicators_json: Mapped[str] = mapped_column(Text, default="[]")
    explanation_json: Mapped[str] = mapped_column(Text, default="[]")
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    record: Mapped["ContentRecord"] = relationship(back_populates="analyses")

class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="Open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    records: Mapped[list["CaseRecord"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    notes: Mapped[list["AnalystNote"]] = relationship(back_populates="case", cascade="all, delete-orphan")

class CaseRecord(Base):
    __tablename__ = "case_records"
    __table_args__ = (UniqueConstraint("case_id", "record_id", name="uq_case_record"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    record_id: Mapped[int] = mapped_column(ForeignKey("content_records.id"))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    case: Mapped["Case"] = relationship(back_populates="records")
    record: Mapped["ContentRecord"] = relationship()

class RelationshipEdge(Base):
    __tablename__ = "relationships"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    target_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    relationship_type: Mapped[str] = mapped_column(String(60))
    shared_feature: Mapped[str] = mapped_column(String(180), default="")
    evidence_description: Mapped[str] = mapped_column(Text)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)

class AnalystNote(Base):
    __tablename__ = "analyst_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    record_id: Mapped[int | None] = mapped_column(ForeignKey("content_records.id"), nullable=True)
    note_text: Mapped[str] = mapped_column(Text)
    disposition: Mapped[str] = mapped_column(String(50), default="Pending Review")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    case: Mapped["Case"] = relationship(back_populates="notes")
