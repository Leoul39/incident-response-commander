from langchain_core.tools import tool


@tool
def query_logs(service: str) -> str:
    """Get recent error logs for a service."""

    data = {
        "db-primary": (
            "09:10 ERROR database disk usage reached 94%; "
            "09:11 WARNING filesystem nearly full"
        ),
        "checkout-service": (
            "09:12 ERROR HTTP 500 rate increased to 18%; "
            "09:13 ERROR payment requests failing"
        ),
        "report-worker": (
            "09:10 WARNING CPU reached 91%; "
            "09:12 INFO CPU returned to normal"
        ),
    }

    return data.get(service, "No recent logs found.")


@tool
def get_metrics(service: str) -> str:
    """Get current CPU, memory, disk and error-rate metrics."""

    data = {
        "db-primary": (
            "CPU: 42%, Memory: 71%, Disk: 94%, Error rate: 2%"
        ),
        "checkout-service": (
            "CPU: 78%, Memory: 82%, Disk: 61%, Error rate: 18%"
        ),
        "report-worker": (
            "CPU: 48%, Memory: 55%, Disk: 42%, Error rate: 0%"
        ),
    }

    return data.get(service, "No metrics found.")


@tool
def get_recent_deployments(service: str) -> str:
    """Get recent deployments for a service."""

    data = {
        "db-primary": "No recent deployments.",
        "checkout-service": (
            "v2.4.1 deployed at 09:05; "
            "v2.4.0 deployed yesterday at 15:30"
        ),
        "report-worker": "v1.8.2 deployed yesterday at 18:00.",
    }

    return data.get(service, "No deployment data found.")

def execute_runbook(action: str, service: str) -> str:
    results = {
        ("Clear old logs", "db-primary"): "success",
        ("Restart service", "db-primary"): "success",
        ("Scale up service", "report-worker"): "success",
        ("Roll back deployment", "checkout-service"): "success",
        ("No automated fix", "db-primary"): "failed",
    }

    return results.get((action, service), "failed")