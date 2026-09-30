from pathlib import Path
import sys

from langgraph.types import Command

from .graph import graph


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ALERTS = {
    "noise": {
        "alert_id": "INC-2033",
        "service": "report-worker",
        "message": "CPU at 91% for 2 minutes on report-worker, now back to normal",
        "timestamp": "2026-09-28T09:14:00Z",
    },
    "low_risk": {
        "alert_id": "INC-2031",
        "service": "db-primary",
        "message": "Database disk usage at 94%",
        "timestamp": "2026-09-28T09:14:00Z",
    },
    "approved": {
        "alert_id": "INC-2032",
        "service": "checkout-service",
        "message": "Error rate spiked to 18% after deployment v2.4.1",
        "timestamp": "2026-09-28T09:14:00Z",
    },
    "rejected": {
        "alert_id": "INC-2034",
        "service": "checkout-service",
        "message": "Error rate spiked to 18% after deployment v2.4.1",
        "timestamp": "2026-09-28T09:14:00Z",
    },
}


def initial_state(alert):
    return {
        "alert": alert,
        "severity": "",
        "messages": [],
        "visited_nodes": [],
        "evidence_summary": "",
        "root_cause": "",
        "confidence": 0.0,
        "tools_used": [],
        "tool_call_count": 0,
        "proposed_fix": "",
        "fix_risk": "",
        "approval_decision": "",
        "fix_result": "",
        "escalation_status": "",
        "final_report": "",
    }


def run_scenario(name, approval=None):
    alert = ALERTS[name]
    config = {"configurable": {"thread_id": alert["alert_id"]}}
    print(f"\n=== Scenario: {name} ===")

    first_result = graph.invoke(initial_state(alert), config=config)
    if first_result.get("__interrupt__"):
        print("First call interrupted for human approval.")
        if approval is None:
            return graph.get_state(config).values
        graph.invoke(Command(resume=approval), config=config)
        print(f"Second call resumed with: {approval}")

    state = graph.get_state(config).values
    print("Path:", " -> ".join(state.get("visited_nodes", [])))
    print("Tools:", ", ".join(state.get("tools_used", [])) or "none")
    print("Final report:\n" + state.get("final_report", ""))
    return state


def save_graph_diagram():
    diagram_path = Path(__file__).resolve().parent.parent / "graph.mmd"
    diagram_path.write_text(graph.get_graph().draw_mermaid(), encoding="utf-8")
    return diagram_path


def main():
    save_graph_diagram()
    run_scenario("noise")
    run_scenario("low_risk")
    run_scenario("approved", approval="approve")
    run_scenario("rejected", approval="reject")


if __name__ == "__main__":
    main()