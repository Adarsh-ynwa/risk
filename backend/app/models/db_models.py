from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(String(64), index=True)
    transaction_date: Mapped[str] = mapped_column(String(32))
    transaction_time: Mapped[str] = mapped_column(String(16))
    hour_of_day: Mapped[int] = mapped_column(Integer)
    is_weekend: Mapped[bool] = mapped_column(Boolean, default=False)
    is_night_transaction: Mapped[bool] = mapped_column(Boolean, default=False)
    country: Mapped[str] = mapped_column(String(64))
    city: Mapped[str] = mapped_column(String(64))
    merchant_category: Mapped[str] = mapped_column(String(64), index=True)
    payment_method: Mapped[str] = mapped_column(String(32), index=True)
    device_type: Mapped[str] = mapped_column(String(32))
    customer_age: Mapped[int] = mapped_column(Integer)
    credit_score: Mapped[int] = mapped_column(Integer)
    account_age_years: Mapped[float] = mapped_column(Float)
    account_balance: Mapped[float] = mapped_column(Float)
    transaction_amount: Mapped[float] = mapped_column(Float)
    num_prev_transactions: Mapped[int] = mapped_column(Integer)
    transaction_freq_monthly: Mapped[float] = mapped_column(Float)
    distance_from_home_km: Mapped[float] = mapped_column(Float)
    time_since_last_txn_hrs: Mapped[float] = mapped_column(Float)
    is_international: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    pin_changed_recently: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fraud: Mapped[bool] = mapped_column(Boolean, default=False)
    fraud_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(64), index=True)
    fraud_probability: Mapped[float] = mapped_column(Float)
    ml_score: Mapped[float] = mapped_column(Float)
    rule_score: Mapped[float] = mapped_column(Float)
    final_risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16))
    triggered_rules: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    risk_level: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    summary: Mapped[str] = mapped_column(Text)
    primary_risk_factors: Mapped[str] = mapped_column(Text)
    investigation_findings: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(String(32))
    recommended_action_reason: Mapped[str] = mapped_column(Text)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    tool_calls: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ActionLog(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(32))
    previous_status: Mapped[str] = mapped_column(String(32))
    new_status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
