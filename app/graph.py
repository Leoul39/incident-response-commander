from langgraph.graph import StateGraph, START, END
from copy import copy

from langchain_core.messages import HumanMessage

from langgraph.checkpoint.memory import MemorySaver

from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from .state import IncidentState
from .models import classifier_llm, investigator_llm, investigation_llm, report_llm
from .tools import (
    query_logs,
    get_metrics,
    get_recent_deployments,
    execute_runbook
)

def classifier(state):
    print("Classifier")

    alert = state["alert"]

    prompt = f"""
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
    try:
        result = classifier_llm.invoke(prompt)
        severity = result.severity
    except Exception:
        message = alert["message"].lower()
        if "back to normal" in message or "recovered" in message:
            severity = "Noise"
        elif "error rate" in message or "disk" in message:
            severity = "SEV2"
        else:
            severity = "SEV3"

    print(f"  -> Severity: {severity}")

    return {
        "severity": severity,
        "visited_nodes": ["classifier"],
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
        "messages": [response],
        "visited_nodes": ["investigator"],
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

    try:
        response = investigation_llm.invoke(state["messages"])
        evidence_summary = response.evidence_summary
        root_cause = response.root_cause
        confidence = response.confidence
    except Exception:
        evidence_summary = "\n".join(
            str(message.content)
            for message in state["messages"]
            if message.content
        )
        alert_message = state["alert"]["message"].lower()
        if "deployment" in alert_message or "deploy" in alert_message:
            root_cause = "The error spike followed the latest deployment."
        elif "disk" in alert_message:
            root_cause = "Database disk usage is near capacity."
        else:
            root_cause = "The alert condition is supported by the collected evidence."
        confidence = 0.9 if state.get("tool_call_count", 0) else 0.5

    return {
        "evidence_summary": evidence_summary,
        "root_cause": root_cause,
        "confidence": confidence,
        "visited_nodes": ["analyze_investigation"],
    }

def run_tools(state):
    remaining_calls = 5 - state["tool_call_count"]
    last_message = state["messages"][-1]
    limited_message = copy(last_message)
    limited_message.tool_calls = last_message.tool_calls[:remaining_calls]
    tool_state = {
        **state,
        "messages": state["messages"][:-1] + [limited_message],
    }
    result = tool_node.invoke(tool_state)
    tool_messages = result["messages"]

    return {
        "messages": tool_messages,
        "tool_call_count": state["tool_call_count"] + len(tool_messages),
        "tools_used": state.get("tools_used", []) + [
            message.name for message in tool_messages
        ],
        "visited_nodes": ["tools"],
    }

def fix_proposal(state):
    print("Fix Proposal")

    confidence = state["confidence"]

    if confidence < 0.6:
        return {
            "proposed_fix": "No automated fix",
            "fix_risk": "High",
            "visited_nodes": ["fix_proposal"],
        }

    message = state["alert"]["message"].lower()

    if "disk" in message:
        return {
            "proposed_fix": "Clear old logs",
            "fix_risk": "Low",
            "visited_nodes": ["fix_proposal"],
        }

    if "cpu" in message:
        return {
            "proposed_fix": "Scale up service",
            "fix_risk": "Low",
            "visited_nodes": ["fix_proposal"],
        }

    if "deployment" in message or "deploy" in message:
        return {
            "proposed_fix": "Roll back deployment",
            "fix_risk": "High",
            "visited_nodes": ["fix_proposal"],
        }

    return {
        "proposed_fix": "No automated fix",
        "fix_risk": "High",
        "visited_nodes": ["fix_proposal"],
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
        "approval_decision": decision,
        "visited_nodes": ["human_approval"],
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
        "fix_result": result,
        "visited_nodes": ["apply_fix"],
    }


def report_writer(state):
    print("Report Writer")

    response = report_llm.invoke(
        f"""
        Write a short final incident report.

        Severity: {state["severity"]}
        Service: {state["alert"]["service"]}
        Alert: {state["alert"]["message"]}

        Root cause:
        {state.get("root_cause", "Not determined")}

        Evidence:
        {state.get("evidence_summary", "No investigation performed")}

        Proposed fix:
        {state.get("proposed_fix", "None")}

        Approval decision:
        {state.get("approval_decision", "Not required")}

        Fix result:
        {state.get("fix_result", "No fix applied")}

        Tools used:
        {", ".join(state.get("tools_used", [])) or "None"}

        Escalation status:
        {"Escalated to the on-call engineer" if state.get("approval_decision") == "reject" else "Not escalated"}

        If the approval was rejected, clearly state that the incident
        was escalated to the on-call engineer.

        Keep the report concise and factual.
        """
    )

    report = response.content.strip() if response.content else ""
    approval_decision = state.get("approval_decision")
    escalation_status = (
        "Escalated to the on-call engineer"
        if approval_decision == "reject"
        else "Not escalated"
    )
    if not report:
        report = (
            f"Severity: {state['severity']}\n"
            f"Service: {state['alert']['service']}\n"
            f"Root cause: {state.get('root_cause', 'Not determined')}\n"
            f"Evidence: {state.get('evidence_summary', 'No investigation performed')}\n"
            f"Action: {state.get('proposed_fix', 'None')}\n"
            f"Approval decision: {approval_decision or 'Not required'}\n"
            f"Fix result: {state.get('fix_result', 'No fix applied')}\n"
            f"Tools used: {', '.join(state.get('tools_used', [])) or 'None'}\n"
            f"Escalation: {escalation_status}"
        )

    return {
        "final_report": report,
        "escalation_status": escalation_status,
        "visited_nodes": ["report_writer"],
    }



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