from models import classifier_llm


result = classifier_llm.invoke(
    """
    Classify this monitoring alert.

    Service: db-primary
    Alert: Database disk usage at 94%
    """
)

print(result)