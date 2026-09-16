from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Provenance:
    source_text: str
    chapter: str = ""
    verse: str = ""
    commentary: str = ""
    author: str = ""
    edition: str = ""
    translator: str = ""
    validation_status: str = "UNVERIFIED"
    trace_id: Optional[str] = None
    artifact_hash: Optional[str] = None
