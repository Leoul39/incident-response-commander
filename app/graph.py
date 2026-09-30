from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

from langgraph.checkpoint.memory import MemorySaver

from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from state import IncidentState
from models import classifier_llm, investigator_llm, investigation_llm
from tools import (
    query_logs,
    get_metrics,
    get_recent_deployments,
    execute_runbook
)

def classifier(state):
    print("Classifier")

    alert = state["alert"]

    result = classifier_llm.invoke(
        f"""
        Classify this monitoring alert.

        Service: {alert["service"]}
        Alert: {alert["message"]}
        Timestamp: {alert["timestamp"]}

        Severity rules:

        - SEV1: Immediate, critical service impact or a very serious active failure.
        - SEV2: Significant active problem requiring investigation and remediation, but not a complete critical outage.
        - SEV3: Minor active problem or warning that does not pose an immediate serious threat.
        - Noise: A transient condition that has already recovered or no longer requires investigation.

        Important:
        - A high metric alone does not automatically mean SEV1.
        - Consider the complete alert message and whether the condition is still active.
        - Choose exactly one severity.
        """
    )

    print(f"  → Severity: {result.severity}")

    return {
        "severity": result.severity
    }

def route_after_classifier(state):
    if state["severity"] == "Noise":
        return "report_writer"

    return "investigator"



def investigator(state):
    print("Investigator")

    alert = state["alert"]

    if not state["messages"]:
        message = HumanMessage(
            content=f"""
        Investigate this monitoring incident.

        Service: {alert["service"]}
        Alert: {alert["message"]}

        Use the available tools to gather evidence.
        Check logs, metrics, and recent deployments when useful.
        Do not guess the root cause without evidence.
        """
                )

        response = investigator_llm.invoke([message])

    else:
        response = investigator_llm.invoke(state["messages"])

    return {
        "messages": [response]
    }

def route_investigator(state):
    if state["tool_call_count"] >= 5:
        return "analyze_investigation"

    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return "analyze_investigation"

tool_node = ToolNode(
    [
        query_logs,
        get_metrics,
        get_recent_deployments,
    ]
)

def analyze_investigation(state):
    print("Analyze Investigation")

    response = investigation_llm.invoke(
        state["messages"]
    )

    return {
        "evidence_summary": response.evidence_summary,
        "root_cause": response.root_cause,
        "confidence": response.confidence,
    }

def run_tools(state):
    result = tool_node.invoke(state)

    return {
        "messages": result["messages"],
        "tool_call_count": state["tool_call_count"] + len(result["messages"]),
    }

def fix_proposal(state):
    print("Fix Proposal")

    confidence = state["confidence"]

    if confidence < 0.6:
        return {
            "proposed_fix": "No automated fix",
            "fix_risk": "High",
        }

    message = state["alert"]["message"].lower()

    if "disk" in message:
        return {
            "proposed_fix": "Clear old logs",
            "fix_risk": "Low",
        }

    if "cpu" in message:
        return {
            "proposed_fix": "Scale up service",
            "fix_risk": "Low",
        }

    if "deployment" in message or "deploy" in message:
        return {
            "proposed_fix": "Roll back deployment",
            "fix_risk": "High",
        }

    return {
        "proposed_fix": "No automated fix",
        "fix_risk": "High",
    }

def route_after_fix_proposal(state):
    if state["fix_risk"] == "High":
        return "human_approval"

    return "apply_fix"

def human_approval(state):
    print("Human Approval")

    decision = interrupt({
        "message": "Human approval required.",
        "proposed_fix": state["proposed_fix"],
        "evidence": state["evidence_summary"],
        "root_cause": state["root_cause"],
    })

    return {
        "approval_decision": decision
    }

def route_after_approval(state):
    if state["approval_decision"] == "approve":
        return "apply_fix"

    return "report_writer"

def apply_fix(state):
    print("Apply Fix")

    result = execute_runbook(
        state["proposed_fix"],
        state["alert"]["service"],
    )

    return {
        "fix_result": result
    }


def report_writer(state):
    print("Report Writer")
    return state



builder = StateGraph(IncidentState)

builder.add_node("classifier", classifier)
builder.add_node("investigator", investigator)
builder.add_node("analyze_investigation",analyze_investigation)
builder.add_node("tools", run_tools)
builder.add_node("fix_proposal", fix_proposal)
builder.add_node("human_approval", human_approval)
builder.add_node("apply_fix", apply_fix)
builder.add_node("report_writer", report_writer)

builder.add_edge(START, "classifier")
builder.add_conditional_edges(
    "classifier",
    route_after_classifier,
)
builder.add_conditional_edges(
    "investigator",
    route_investigator,
    {
        "tools": "tools",
        "analyze_investigation": "analyze_investigation",
    },
)
builder.add_edge("tools", "investigator")
builder.add_edge("analyze_investigation","fix_proposal")
builder.add_conditional_edges(
    "fix_proposal",
    route_after_fix_proposal,
    {
        "human_approval": "human_approval",
        "apply_fix": "apply_fix",
    },
)
builder.add_conditional_edges(
    "human_approval",
    route_after_approval,
    {
        "apply_fix": "apply_fix",
        "report_writer": "report_writer",
    },
)
builder.add_edge("apply_fix", "report_writer")
builder.add_edge("report_writer", END)

checkpointer = MemorySaver()

graph = builder.compile(
    checkpointer=checkpointer
)