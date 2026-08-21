"""LangGraph implementation of the Groq-powered payment-risk investigator."""

import json
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from sqlalchemy.orm import Session

from app.agent.tools import execute_tool
from app.config import settings
from app.schemas.schemas import InvestigationReport, ToolCallRecord

MAX_TOOL_ROUNDS = 6


class InvestigationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    tool_rounds: int


def _summarize(result: Any) -> str:
    if isinstance(result, list):
        return f"Returned {len(result)} records"
    if isinstance(result, dict):
        return f"Returned object with {len(result)} fields" if "error" not in result else f"Error: {result['error']}"
    return str(result)[:120]


def run_langgraph_investigation(
    db: Session,
    transaction_id: str,
    customer_id: str,
    risk_assessment: dict[str, Any],
) -> tuple[InvestigationReport | None, list[ToolCallRecord]]:
    """Run the agent → tools → agent LangGraph loop and return a validated report."""

    @tool
    def get_transaction_context(transaction_id_arg: str = transaction_id) -> dict[str, Any]:
        """Get full context for a transaction, including its amount, location, device, and fraud flags."""
        return execute_tool(db, "get_transaction_context", {"transaction_id": transaction_id_arg})

    @tool
    def get_customer_profile(customer_id_arg: str = customer_id) -> dict[str, Any]:
        """Get the customer profile, account details, and activity summary."""
        return execute_tool(db, "get_customer_profile", {"customer_id": customer_id_arg})

    @tool
    def get_customer_transaction_history(customer_id_arg: str = customer_id, limit: int = 10) -> list[dict[str, Any]]:
        """Get a customer's recent payment history to identify unusual behaviour."""
        return execute_tool(db, "get_customer_transaction_history", {"customer_id": customer_id_arg, "limit": limit})

    @tool
    def get_customer_risk_history(customer_id_arg: str = customer_id, limit: int = 10) -> list[dict[str, Any]]:
        """Get a customer's prior risk scores to identify repeat high-risk patterns."""
        return execute_tool(db, "get_customer_risk_history", {"customer_id": customer_id_arg, "limit": limit})

    @tool
    def get_similar_transactions(transaction_id_arg: str = transaction_id, limit: int = 5) -> list[dict[str, Any]]:
        """Find comparable transactions that can support the fraud assessment."""
        return execute_tool(db, "get_similar_transactions", {"transaction_id": transaction_id_arg, "limit": limit})

    tools = [
        get_transaction_context,
        get_customer_profile,
        get_customer_transaction_history,
        get_customer_risk_history,
        get_similar_transactions,
    ]
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, api_key=settings.groq_api_key)

    system_prompt = """You are an AI Risk Investigator for payment fraud detection.
You must use one or more available tools before making a recommendation. Do not invent data.
When your investigation is complete, respond only with valid JSON with these fields:
risk_level, confidence, summary, primary_risk_factors, investigation_findings,
recommended_action, recommended_action_reason, requires_human_review.
recommended_action must be one of APPROVE, MONITOR, REQUIRE_VERIFICATION, HOLD, BLOCK, MANUAL_REVIEW.
"""

    def call_model(state: InvestigationState) -> dict[str, Any]:
        # The first pass must gather evidence; later passes can decide whether more tools are needed.
        model = llm.bind_tools(tools, tool_choice="any" if state["tool_rounds"] == 0 else "auto")
        return {"messages": [model.invoke(state["messages"])], "tool_rounds": state["tool_rounds"] + 1}

    def route_after_model(state: InvestigationState) -> str:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls and state["tool_rounds"] <= MAX_TOOL_ROUNDS:
            return "tools"
        return END

    builder = StateGraph(InvestigationState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_after_model, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    graph = builder.compile()

    context = {"transaction_id": transaction_id, "customer_id": customer_id, "risk_assessment": risk_assessment}
    final_state = graph.invoke({
        "messages": [SystemMessage(content=system_prompt), HumanMessage(content=json.dumps(context, indent=2))],
        "tool_rounds": 0,
    })

    results_by_call_id = {
        message.tool_call_id: message.content
        for message in final_state["messages"]
        if isinstance(message, ToolMessage)
    }
    tool_calls: list[ToolCallRecord] = []
    for message in final_state["messages"]:
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                raw_result = results_by_call_id.get(call["id"], "No result returned")
                try:
                    result = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
                except json.JSONDecodeError:
                    result = raw_result
                tool_calls.append(ToolCallRecord(
                    tool=call["name"],
                    reason=f"LangGraph agent requested {call['name']} to gather investigation evidence",
                    result_summary=_summarize(result),
                ))

    final_message = final_state["messages"][-1]
    if not isinstance(final_message, AIMessage):
        return None, tool_calls
    try:
        report = InvestigationReport(**json.loads(str(final_message.content)))
        report.tool_calls = tool_calls
        return report, tool_calls
    except (json.JSONDecodeError, ValueError, TypeError):
        return None, tool_calls
