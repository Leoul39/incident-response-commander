from .schemas import Classification

def test_classification_schema_accepts_required_severities():
    for severity in ("SEV1", "SEV2", "SEV3", "Noise"):
        assert Classification(severity=severity).severity == severity