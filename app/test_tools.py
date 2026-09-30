from tools import (
    query_logs,
    get_metrics,
    get_recent_deployments,
)


print(query_logs.invoke({"service": "db-primary"}))
print(get_metrics.invoke({"service": "db-primary"}))
print(get_recent_deployments.invoke({"service": "db-primary"}))