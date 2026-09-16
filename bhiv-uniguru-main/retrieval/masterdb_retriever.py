from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retrieval.retrieval_engine import generate_retrieval_artifact as _generate_retrieval_artifact
from retrieval.retrieval_engine import retrieve_from_masterdb as _retrieve_from_masterdb


def retrieve_from_masterdb(
    query: str,
    grade: Optional[int] = None,
    medium: Optional[str] = None,
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    return _retrieve_from_masterdb(query=query, grade=grade, medium=medium, subject=subject)


def generate_retrieval_artifact(
    query: str,
    grade: Optional[int] = None,
    medium: Optional[str] = None,
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    artifact = _generate_retrieval_artifact(query=query, grade=grade, medium=medium, subject=subject)
    artifact_path = ROOT / "retrieval" / "retrieval_artifact.json"
    artifact_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    return artifact
