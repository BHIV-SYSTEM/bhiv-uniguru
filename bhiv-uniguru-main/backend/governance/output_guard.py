from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class OutputGovernanceResult:
    allowed: bool
    reason: str
    flags: Dict[str, bool]


class OutputGovernanceGuard:
    """Deterministic output gate to prevent authority/action leakage."""

    BLOCK_PATTERNS = [
        "i have executed",
        "i executed",
        "i will execute",
        "i already ran",
        "run this command",
        "delete files",
        "override governance",
        "bypass safety",
        "i can take action in your system",
        "i have changed your system",
        "i will perform this action",
    ]

    def evaluate(self, response_content: str) -> OutputGovernanceResult:
        text = (response_content or "").lower()
        for pattern in self.BLOCK_PATTERNS:
            if pattern in text:
                return OutputGovernanceResult(
                    allowed=False,
                    reason=f"Output governance block: forbidden action/authority pattern '{pattern}'.",
                    flags={"output_authority_violation": True},
                )
        return OutputGovernanceResult(
            allowed=True,
            reason="Output governance passed.",
            flags={"output_authority_violation": False},
        )
