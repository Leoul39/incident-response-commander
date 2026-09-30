from graph import graph
from langgraph.types import Command

# initial_state = {
#     "alert": {
#         "alert_id": "INC-2031",
#         "service": "db-primary",
#         "message": "Database disk usage at 95%",
#         "timestamp": "2026-09-28T09:14:00Z",
#     },
#     "messages": [],
#     "tool_call_count": 0
# }

initial_state = {
    "alert": {
        "alert_id": "INC-2040",
        "service": "checkout-service",
        "message": "Error rate spiked to 18% after deployment v2.4.1",
        "timestamp": "2026-09-28T09:14:00Z",
    },
    "messages": [],
    "tool_call_count": 0,
}

config = {
    "configurable": {
        "thread_id": "INC-2040"
    }
}

result = graph.invoke(
    initial_state,
    config=config
)
result = graph.invoke(
    Command(resume="approve"),
    config=config
)

print("\nFinal state:")
print(result)