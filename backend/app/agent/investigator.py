"""AI risk investigator with Groq tool calling and a deterministic fallback."""

import json
import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.agent.tools import TOOL_DEFINITIONS, execute_tool
from app.config import settings
from app.schemas.schemas import InvestigationReport, ToolCallRecord
from app.services.risk_engine import score_to_level

logger = logging.getLogger(__name__)

INVESTIGATION_SCHEMA = """
Return ONLY valid JSON matching this schema:
{
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "confidence": 0.0-1.0,
  "summary": "2-3 sentence investigation summary",
  "primary_risk_factors": ["factor1", "factor2"],
  "investigation_findings": ["finding1", "finding2"],
  "recommended_action": "APPROVE|MONITOR|REQUIRE_VERIFICATION|HOLD|BLOCK|MANUAL_REVIEW",
  "recommended_action_reason": "explanation",
  "requires_human_review": true|false
}
"""

MAX_TOOL_ROUNDS = 6

# JSON response contract for Groq-backed investigations. Responses are still
# validated with the Pydantic model before they reach the API.
GROQ_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "risk_level": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
        "confidence": {"type": "number"},
        "summary": {"type": "string"},
        "primary_risk_factors": {"type": "array", "items": {"type": "string"}},
        "investigation_findings": {"type": "array", "items": {"type": "string"}},
        "recommended_action": {
            "type": "string",
            "enum": ["APPROVE", "MONITOR", "REQUIRE_VERIFICATION", "HOLD", "BLOCK", "MANUAL_REVIEW"],
        },
        "recommended_action_reason": {"type": "string"},
        "requires_human_review": {"type": "boolean"},
    },
    "required": [
        "risk_level",
        "confidence",
        "summary",
        "primary_risk_factors",
        "investigation_findings",
        "recommended_action",
        "recommended_action_reason",
        "requires_human_review",
    ],
}


def _build_fallback_report(
    evidence: dict[str, Any],
    tool_calls: list[ToolCallRecord],
) -> InvestigationReport:
    """Generate an investigation from rules when Groq is unavailable."""
    assessment = evidence.get("risk_assessment") or {}
    triggered = assessment.get("triggered_rules", [])
    risk_score = assessment.get("final_risk_score", 50)
    risk_level = assessment.get("risk_level") or score_to_level(risk_score)

    factors = [r.get("name", "Unknown rule") for r in triggered] or ["Elevated ML fraud probability"]
    findings = [r.get("explanation", "") for r in triggered if r.get("explanation")]

    profile = evidence.get("customer_profile") or {}
    if profile.get("fraud_count", 0) > 0:
        findings.append(f"Customer has {profile['fraud_count']} prior fraud-flagged transactions.")

    similar = evidence.get("similar_transactions") or []
    fraud_similar = sum(1 for s in similar if s.get("is_fraud"))
    if fraud_similar:
        findings.append(f"{fraud_similar} of {len(similar)} similar transactions were fraudulent.")

    action_map = {
        "LOW": ("APPROVE", "Low risk score with minimal rule triggers."),
        "MEDIUM": ("MONITOR", "Moderate risk — continue monitoring."),
        "HIGH": ("REQUIRE_VERIFICATION", "High risk signals require customer verification."),
        "CRITICAL": ("HOLD", "Critical risk — hold transaction pending manual review."),
    }
    action, reason = action_map.get(risk_level, ("MANUAL_REVIEW", "Requires analyst review."))

    return InvestigationReport(
        risk_level=risk_level,
        confidence=min(0.5 + len(triggered) * 0.08, 0.92),
        summary=(
            f"Rule-based fallback investigation for transaction with risk score {risk_score:.0f}/100. "
            f"{len(triggered)} risk rules triggered. {len(tool_calls)} investigation tools executed. "
            f"Groq API unavailable — using deterministic analysis."
        ),
        primary_risk_factors=factors[:5],
        investigation_findings=findings[:5] or ["No additional findings from rule engine."],
        recommended_action=action,
        recommended_action_reason=reason,
        requires_human_review=risk_level in ("HIGH", "CRITICAL"),
        tool_calls=tool_calls,
    )


def _run_fallback_agent(
    db: Session,
    transaction_id: str,
    customer_id: str,
    risk_assessment: dict[str, Any],
) -> tuple[InvestigationReport, bool]:
    """Execute all tools sequentially when Groq is unavailable."""
    tool_calls: list[ToolCallRecord] = []
    evidence: dict[str, Any] = {"risk_assessment": risk_assessment}

    planned = [
        ("get_transaction_context", {"transaction_id": transaction_id}, "Retrieve full transaction context"),
        ("get_customer_profile", {"customer_id": customer_id}, "Review customer profile and account history"),
        ("get_customer_behavior", {"transaction_id": transaction_id}, "Compare this payment with earlier customer behavior"),
        ("get_customer_transaction_history", {"customer_id": customer_id, "limit": 10}, "Analyze recent spending patterns"),
        ("get_customer_risk_history", {"customer_id": customer_id, "limit": 10}, "Check prior risk assessments"),
        ("get_similar_transactions", {"transaction_id": transaction_id, "limit": 5}, "Compare with similar transactions"),
    ]

    key_map = {
        "get_transaction_context": "transaction_context",
        "get_customer_profile": "customer_profile",
        "get_customer_behavior": "customer_behavior",
        "get_customer_transaction_history": "transaction_history",
        "get_customer_risk_history": "risk_history",
        "get_similar_transactions": "similar_transactions",
    }

    for tool_name, args, reason in planned:
        result = execute_tool(db, tool_name, args)
        tool_calls.append(ToolCallRecord(tool=tool_name, reason=reason, result_summary=_summarize(result)))
        evidence[key_map[tool_name]] = result

    return _build_fallback_report(evidence, tool_calls), True


def _summarize(result: Any) -> str:
    if isinstance(result, list):
        return f"Returned {len(result)} records"
    if isinstance(result, dict):
        if "error" in result:
            return f"Error: {result['error']}"
        return f"Returned object with {len(result)} fields"
    return str(result)[:120]


def _parse_investigation_json(text: str, tool_calls: list[ToolCallRecord]) -> InvestigationReport | None:
    try:
        # Strip markdown fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = json.loads(cleaned)
        data["tool_calls"] = [t.model_dump() for t in tool_calls]
        return InvestigationReport(**data)
    except Exception as e:
        logger.warning("Failed to parse investigation JSON: %s", e)
        return None


def _run_groq_agent(
    db: Session,
    transaction_id: str,
    customer_id: str,
    risk_assessment: dict[str, Any],
) -> tuple[InvestigationReport | None, list[ToolCallRecord], dict[str, Any]]:
    """Run a Groq tool-calling loop, with tools executed safely by this app."""
    tools = [{"type": "function", "function": definition} for definition in TOOL_DEFINITIONS]

    initial_context = {
        "transaction_id": transaction_id,
        "customer_id": customer_id,
        "risk_assessment": risk_assessment,
    }

    system_prompt = """You are an AI Risk Investigator for payment fraud detection.
You MUST use the available tools to gather evidence before making conclusions.
Call tools to investigate — do not invent data.
After gathering sufficient evidence, provide your final investigation as JSON only.

Available investigation tools:
- get_transaction_context
- get_customer_profile
- get_customer_behavior
- get_customer_transaction_history
- get_customer_risk_history
- get_similar_transactions
"""

    tool_calls_log: list[ToolCallRecord] = []
    collected_evidence: dict[str, Any] = {"risk_assessment": risk_assessment}
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Investigate this high-risk transaction:\n{json.dumps(initial_context, indent=2)}\n\n"
                "Start by calling the tools you need. When done investigating, respond with ONLY the investigation JSON."
            ),
        },
    ]
    headers = {"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"}

    with httpx.Client(timeout=45) as client:
        for round_number in range(MAX_TOOL_ROUNDS):
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "required" if round_number == 0 else "auto",
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
            function_calls = message.get("tool_calls") or []

            if not function_calls:
                report = _parse_investigation_json(message.get("content") or "", tool_calls_log)
                if report:
                    return report, tool_calls_log, collected_evidence
                break

            messages.append({"role": "assistant", "content": message.get("content"), "tool_calls": function_calls})

            for function_call in function_calls:
                function = function_call["function"]
                tool_name = function["name"]
                try:
                    args = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}

                if tool_name in {"get_transaction_context", "get_similar_transactions", "get_customer_behavior"}:
                    args.setdefault("transaction_id", transaction_id)
                if "customer" in tool_name:
                    args.setdefault("customer_id", customer_id)

                result = execute_tool(db, tool_name, args)
                tool_calls_log.append(ToolCallRecord(
                    tool=tool_name,
                    reason=f"Agent requested {tool_name} to gather investigation evidence",
                    result_summary=_summarize(result),
                ))
                collected_evidence[tool_name] = result
                messages.append({
                    "role": "tool",
                    "tool_call_id": function_call["id"],
                    "content": json.dumps(result, default=str),
                })

        messages.append({"role": "user", "content": f"Based on the tool results, provide the final investigation report.\n{INVESTIGATION_SCHEMA}"})
        final = client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
        )
        final.raise_for_status()
        text = final.json()["choices"][0]["message"].get("content") or ""
        return _parse_investigation_json(text, tool_calls_log), tool_calls_log, collected_evidence


def run_investigation(
    db: Session,
    transaction_id: str,
    customer_id: str,
    risk_assessment: dict[str, Any],
) -> tuple[InvestigationReport, bool]:
    """
    Run AI investigation with agentic tool calling.
    Returns (report, is_fallback).
    """
    if settings.groq_api_key:
        try:
            from app.agent.langgraph_investigator import run_langgraph_investigation

            report, tool_calls = run_langgraph_investigation(
                db, transaction_id, customer_id, risk_assessment
            )
            if report:
                report.tool_calls = tool_calls
                return report, False
        except Exception as e:
            logger.warning("Groq agent failed: %s", e)

    return _run_fallback_agent(db, transaction_id, customer_id, risk_assessment)
