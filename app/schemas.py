from typing import Literal

from pydantic import BaseModel


class Classification(BaseModel):
    severity: Literal["SEV1", "SEV2", "SEV3", "Noise"]

class Investigation(BaseModel):
    evidence_summary: str
    root_cause: str
    confidence: float