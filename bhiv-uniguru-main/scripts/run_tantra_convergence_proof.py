from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PROOF_DIR = ROOT / "review_packets" / "proof_logs"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from kosha.deterministic_pipeline import run_deterministic_pipeline


CASES = [
    {
        "name": "replay_trace",
        "query": "What is a qubit?",
        "trace_id": "tantra_replay_qubit",
        "user_id": "tantra-demo-user",
    },
    {
        "name": "contradiction_trace",
        "query": "Explain dharma and rajadharma for governance",
        "trace_id": "tantra_contradiction_governance",
        "user_id": "tantra-demo-user",
    },
    {
        "name": "memory_continuity_trace",
        "query": "How does Gita connect dharma, karma yoga, rajadharma, and governance?",
        "trace_id": "tantra_memory_gita_governance",
        "user_id": "tantra-demo-user",
    },
    {
        "name": "downstream_contract_trace",
        "query": "What is Vishnu in Padma Purana?",
        "trace_id": "tantra_downstream_vishnu",
        "user_id": "tantra-demo-user",
    },
]


def _write(name: str, payload: dict) -> None:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    (PROOF_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")


def main() -> None:
    os.environ.setdefault("UNIGURU_API_AUTH_REQUIRED", "false")
    outputs = []
    for case in CASES:
        first = run_deterministic_pipeline(
            query=case["query"],
            trace_id=case["trace_id"],
            user_id=case["user_id"],
        )
        replay = run_deterministic_pipeline(
            query=case["query"],
            trace_id=case["trace_id"],
            user_id=case["user_id"],
        )
        replay_check = {
            "trace_id": case["trace_id"],
            "name": case["name"],
            "retrieval_truth_hash_stable": first.get("retrieval_truth_payload", {}).get("artifact_hash")
            == replay.get("retrieval_truth_payload", {}).get("artifact_hash"),
            "interpretation_hash_stable": first.get("interpretation_payload", {}).get("artifact_hash")
            == replay.get("interpretation_payload", {}).get("artifact_hash"),
            "contract_schema": first.get("output_contract", {}).get("schema"),
            "downstream_status": first.get("downstream_execution", {}).get("status"),
            "verification_status": first.get("verification_status"),
            "trace_continuity": first.get("bucket_proof", {}).get("trace_continuity"),
        }
        outputs.append(replay_check)
        _write(f"{case['name']}.json", first)

    summary = {
        "schema": "TANTRA_CONVERGENCE_PROOF_SUMMARY_V1",
        "proof_logs": [f"{case['name']}.json" for case in CASES],
        "replay_checks": outputs,
        "all_replay_hashes_stable": all(
            item["retrieval_truth_hash_stable"] and item["interpretation_hash_stable"]
            for item in outputs
        ),
    }
    _write("tantra_convergence_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
