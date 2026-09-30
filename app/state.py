from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class Alert(TypedDict):
    alert_id: str
    service: str
    message: str
    timestamp: str


class IncidentState(TypedDict, total=False):
    # Incoming alert
    alert: Alert
    severity: str

    # Investigator
    messages: Annotated[list[BaseMessage], add_messages]
    evidence_summary: str
    root_cause: str
    confidence: float
    tools_used: list[str]
    tool_call_count: int

    # Fix proposal
    proposed_fix: str
    fix_risk: str

    # Human approval
    approval_decision: str

    # Apply fix
    fix_result: str

    # Final report
    escalation_status: str
    final_report: str

    