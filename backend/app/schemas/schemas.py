from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionType(str, Enum):
    APPROVE = "APPROVE"
    MONITOR = "MONITOR"
    REQUIRE_VERIFICATION = "REQUIRE_VERIFICATION"
    HOLD = "HOLD"
    BLOCK = "BLOCK"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class TriggeredRule(BaseModel):
    rule_id: str
    name: str
    severity: str
    points: int
    explanation: str


class RiskAnalyzeRequest(BaseModel):
    transaction_id: str


class TransactionCreateRequest(BaseModel):
    """The payment fields supplied by the demo transaction-entry screen."""

    customer_id: str = Field(min_length=1, max_length=64)
    transaction_amount: float = Field(gt=0)
    country: str = Field(min_length=1, max_length=64)
    city: str = Field(min_length=1, max_length=64)
    merchant_category: str = Field(min_length=1, max_length=64)
    payment_method: str = Field(min_length=1, max_length=32)
    device_type: str = Field(default="Mobile", min_length=1, max_length=32)
    account_balance: float = Field(default=10000, ge=0)
    customer_age: int = Field(default=30, ge=18, le=120)
    credit_score: int = Field(default=650, ge=300, le=900)
    account_age_years: float = Field(default=2, ge=0)
    num_prev_transactions: int = Field(default=10, ge=0)
    transaction_freq_monthly: float = Field(default=5, ge=0)
    distance_from_home_km: float = Field(default=5, ge=0)
    time_since_last_txn_hrs: float = Field(default=24, ge=0)
    is_international: bool = False
    failed_attempts: int = Field(default=0, ge=0)
    pin_changed_recently: bool = False


class RiskAnalyzeResponse(BaseModel):
    transaction_id: str
    fraud_probability: float
    ml_score: float
    rule_score: float
    risk_score: float
    risk_level: str
    triggered_rules: list[TriggeredRule]
    automated_action: str | None = None
    requires_human_approval: bool = False


class InvestigationReport(BaseModel):
    risk_level: str
    confidence: float = Field(ge=0, le=1)
    summary: str
    primary_risk_factors: list[str]
    investigation_findings: list[str]
    recommended_action: str
    recommended_action_reason: str
    requires_human_review: bool
    tool_calls: list["ToolCallRecord"] = []


class ToolCallRecord(BaseModel):
    tool: str
    reason: str
    result_summary: str


class InvestigationResponse(BaseModel):
    transaction_id: str
    investigation: InvestigationReport
    is_fallback: bool = False
    final_status: str | None = None
    action_applied: str | None = None
    requires_human_approval: bool = False


class ActionRequest(BaseModel):
    action: ActionType


class ActionResponse(BaseModel):
    transaction_id: str
    action: str
    previous_status: str
    new_status: str
    timestamp: datetime


class TransactionSummary(BaseModel):
    transaction_id: str
    customer_id: str
    transaction_amount: float
    payment_method: str
    city: str
    country: str
    merchant_category: str
    risk_score: float | None
    risk_level: str | None
    status: str
    transaction_date: str
    is_fraud: bool


class TransactionDetail(BaseModel):
    transaction_id: str
    customer_id: str
    transaction_date: str
    transaction_time: str
    hour_of_day: int
    is_weekend: bool
    is_night_transaction: bool
    country: str
    city: str
    merchant_category: str
    payment_method: str
    device_type: str
    customer_age: int
    credit_score: int
    account_age_years: float
    account_balance: float
    transaction_amount: float
    num_prev_transactions: int
    transaction_freq_monthly: float
    distance_from_home_km: float
    time_since_last_txn_hrs: float
    is_international: bool
    failed_attempts: int
    pin_changed_recently: bool
    is_fraud: bool
    risk_score: float | None
    risk_level: str | None
    status: str
    action: str | None
    fraud_probability: float | None = None
    ml_score: float | None = None
    rule_score: float | None = None
    triggered_rules: list[TriggeredRule] = []


class PaginatedTransactions(BaseModel):
    items: list[TransactionSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class CustomerProfile(BaseModel):
    customer_id: str
    age: int
    credit_score: int
    account_age_years: float
    account_balance: float
    transaction_freq_monthly: float
    num_prev_transactions: int
    total_transactions: int
    fraud_count: int


class StatsResponse(BaseModel):
    transactions_analyzed: int
    high_risk_transactions: int
    critical_transactions: int
    amount_at_risk: float
    fraud_detection_rate: float
    total_transactions: int
    fraud_count: int


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    database_connected: bool
    groq_configured: bool


class ModelMetrics(BaseModel):
    model_type: str
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float | None
    confusion_matrix: list[list[int]]
    feature_count: int
    trained_at: str | None


class RiskSummary(BaseModel):
    risk_distribution: dict[str, int]
    fraud_vs_legitimate: dict[str, int]
    risk_trend: list[dict[str, Any]]
    fraud_by_category: list[dict[str, Any]]
    amount_at_risk_by_level: dict[str, float]
