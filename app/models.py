from dotenv import load_dotenv
from langchain_groq import ChatGroq

from .schemas import Classification, Investigation

from .tools import (
    query_logs,
    get_metrics,
    get_recent_deployments,
)


load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
)

classifier_llm = llm.with_structured_output(
    Classification, method = "json_schema"
)

investigator_llm = llm.bind_tools(
    [
        query_logs,
        get_metrics,
        get_recent_deployments,
    ]
)
investigation_llm = llm.with_structured_output(
    Investigation, method="json_schema"
)

report_llm=llm