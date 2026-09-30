from .tools import (
    query_logs,
    get_metrics,
    get_recent_deployments,
)


def test_mock_tools_are_deterministic_and_service_keyed():
    assert "94%" in query_logs.invoke({"service": "db-primary"})
    assert "Disk: 94%" in get_metrics.invoke({"service": "db-primary"})
    assert get_recent_deployments.invoke({"service": "db-primary"}) == (
        "No recent deployments."
    )


def test_runbook_returns_fixed_results():
    from .tools import execute_runbook

    assert execute_runbook("Clear old logs", "db-primary") == "success"
    assert execute_runbook("Roll back deployment", "checkout-service") == "success"
    assert execute_runbook("Roll back deployment", "db-primary") == "failed"