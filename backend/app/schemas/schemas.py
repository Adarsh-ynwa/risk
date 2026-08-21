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


class VerificationRequest(BaseModel):
    method: str = Field(pattern="^(OTP|REGISTERED_DEVICE|IDENTITY_CHECK|CALLBACK|MANUAL_REVIEW)$")
    requested_by: str = Field(default="AI Risk Manager", min_length=1, max_length=64)
    notes: str | None = Field(default=None, max_length=500)


class VerificationUpdate(BaseModel):
    status: str = Field(pattern="^(PASSED|FAILED|EXPIRED|CANCELLED)$")
    resolved_by: str = Field(default="Demo Analyst", min_length=1, max_length=64)
    notes: str | None = Field(default=None, max_length=500)


class VerificationResponse(BaseModel):
    id: int
    transaction_id: str
    method: str
    status: str
    requested_by: str
    resolved_by: str | None
    notes: str | None
    created_at: datetime
    resolved_at: datetime | None


class UnblockRequestCreate(BaseModel):
    reason: str = Field(min_length=10, max_length=500)
    requested_by: str = Field(default="Demo Analyst", min_length=1, max_length=64)


class UnblockReviewRequest(BaseModel):
    decision: str = Field(pattern="^(APPROVE|REJECT)$")
    reviewed_by: str = Field(default="Senior Demo Analyst", min_length=1, max_length=64)
    notes: str | None = Field(default=None, max_length=500)


class UnblockRequestResponse(BaseModel):
    id: int
    transaction_id: str
    reason: str
    status: str
    requested_by: str
    reviewed_by: str | None
    review_notes: str | None
    created_at: datetime
    reviewed_at: datetime | None


class BehaviorSignal(BaseModel):
    label: str
    current_value: str
    baseline_value: str
    impact: str
    explanation: str


class CustomerBehaviorResponse(BaseModel):
    transaction_id: str
    customer_id: str
    history_count: int
    amount_ratio_to_median: float | None
    is_new_country: bool
    is_new_city: bool
    is_new_device: bool
    is_new_merchant_category: bool
    signals: list[BehaviorSignal] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    event_type: str
    title: str
    description: str
    actor: str
    status: str | None = None
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
    fraud_prevalence_rate: float
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
    threshold: float = 0.5
    false_positives: int = 0
    false_negatives: int = 0
    true_positives: int = 0
    true_negatives: int = 0
    alert_rate: float = 0
    estimated_total_cost_inr: float = 0
    false_positive_cost_inr: float = 0
    false_negative_cost_inr: float = 0
    validation_size: int = 0
    test_size: int = 0
    split_strategy: str = "unknown"
    threshold_selected_on: str = "unknown"
    cost_assumptions_inr: dict[str, float] = Field(default_factory=dict)
    validation_threshold_comparison: list[dict[str, Any]] = Field(default_factory=list)
    hybrid_test_metrics: dict[str, Any] = Field(default_factory=dict)


class RiskSummary(BaseModel):
    risk_distribution: dict[str, int]
    fraud_vs_legitimate: dict[str, int]
    risk_trend: list[dict[str, Any]]
    fraud_by_category: list[dict[str, Any]]
    amount_at_risk_by_level: dict[str, float]
