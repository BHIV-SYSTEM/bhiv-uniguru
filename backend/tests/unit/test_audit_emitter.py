"""
Unit tests — Immutable Cryptographic Audit Emitter
T-GOV-002
"""
from __future__ import annotations

import json

import pytest


@pytest.fixture()
def emitter(tmp_path):
    from security.audit_emitter import AuditEmitter
    return AuditEmitter(log_path=tmp_path / "audit.jsonl")


# ---------------------------------------------------------------------------
# Emit & structure
# ---------------------------------------------------------------------------

def test_emit_returns_entry_with_all_fields(emitter):
    entry = emitter.emit(
        event="jwt_verified",
        actor="user-123",
        resource="/runtime/ecosystem/execute",
        outcome="ALLOW",
    )
    assert entry.seq == 0
    assert entry.event == "jwt_verified"
    assert entry.actor == "user-123"
    assert entry.resource == "/runtime/ecosystem/execute"
    assert entry.outcome == "ALLOW"
    assert len(entry.entry_hash) == 64
    assert len(entry.prev_hash) == 64


def test_first_entry_prev_hash_is_genesis(emitter):
    from security.audit_emitter import _GENESIS_HASH
    entry = emitter.emit(event="e", actor="a", resource="r", outcome="ALLOW")
    assert entry.prev_hash == _GENESIS_HASH


def test_second_entry_prev_hash_equals_first_entry_hash(emitter):
    e1 = emitter.emit(event="e1", actor="a", resource="r", outcome="ALLOW")
    e2 = emitter.emit(event="e2", actor="a", resource="r", outcome="DENY")
    assert e2.prev_hash == e1.entry_hash


def test_seq_increments_monotonically(emitter):
    entries = [emitter.emit(event=f"e{i}", actor="a", resource="r", outcome="ALLOW") for i in range(5)]
    assert [e.seq for e in entries] == list(range(5))


def test_metadata_is_stored(emitter):
    entry = emitter.emit(
        event="replay_blocked",
        actor="attacker",
        resource="/ask",
        outcome="DENY",
        metadata={"jti": "abc123", "reason": "replay"},
    )
    assert entry.metadata["jti"] == "abc123"


# ---------------------------------------------------------------------------
# Chain verification
# ---------------------------------------------------------------------------

def test_verify_chain_empty_log_is_valid(emitter):
    result = emitter.verify_chain()
    assert result["valid"] is True
    assert result["entry_count"] == 0


def test_verify_chain_valid_after_multiple_emits(emitter):
    for i in range(10):
        emitter.emit(event=f"e{i}", actor="a", resource="r", outcome="ALLOW")
    result = emitter.verify_chain()
    assert result["valid"] is True
    assert result["entry_count"] == 10


def test_verify_chain_detects_tampered_entry(tmp_path):
    from security.audit_emitter import AuditEmitter
    log_path = tmp_path / "tamper.jsonl"
    em = AuditEmitter(log_path=log_path)
    em.emit(event="e1", actor="a", resource="r", outcome="ALLOW")
    em.emit(event="e2", actor="a", resource="r", outcome="ALLOW")

    # Tamper: overwrite the first line with modified outcome
    lines = log_path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["outcome"] = "DENY"  # tamper
    lines[0] = json.dumps(first, sort_keys=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        AuditEmitter(log_path=log_path)


def test_verify_chain_detects_tampered_single_entry(tmp_path):
    from security.audit_emitter import AuditEmitter

    log_path = tmp_path / "single-tamper.jsonl"
    emitter = AuditEmitter(log_path=log_path)
    emitter.emit(event="e1", actor="a", resource="r", outcome="ALLOW")

    row = json.loads(log_path.read_text(encoding="utf-8"))
    row["outcome"] = "DENY"
    log_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch"):
        AuditEmitter(log_path=log_path)


def test_verify_chain_detects_broken_prev_hash(tmp_path):
    from security.audit_emitter import AuditEmitter, AuditEntry
    log_path = tmp_path / "broken.jsonl"
    em = AuditEmitter(log_path=log_path)
    em.emit(event="e1", actor="a", resource="r", outcome="ALLOW")
    em.emit(event="e2", actor="a", resource="r", outcome="ALLOW")

    lines = log_path.read_text(encoding="utf-8").splitlines()
    second = json.loads(lines[1])
    second["prev_hash"] = "0" * 64  # break the chain link
    lines[1] = json.dumps(
        AuditEntry(
            seq=second["seq"],
            event=second["event"],
            actor=second["actor"],
            resource=second["resource"],
            outcome=second["outcome"],
            metadata=second["metadata"],
            timestamp=second["timestamp"],
            prev_hash=second["prev_hash"],
        ).to_dict(),
        sort_keys=True,
    )
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    em2 = AuditEmitter(log_path=log_path)
    result = em2.verify_chain()
    assert result["valid"] is False
    assert result["broken_at_seq"] == 1


def test_malformed_persisted_audit_log_fails_closed(tmp_path):
    from security.audit_emitter import AuditEmitter

    log_path = tmp_path / "malformed-audit.jsonl"
    log_path.write_text("{not-json}\n", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        AuditEmitter(log_path=log_path)


# ---------------------------------------------------------------------------
# Persistence & reload
# ---------------------------------------------------------------------------

def test_emitter_resumes_seq_and_chain_after_reload(tmp_path):
    from security.audit_emitter import AuditEmitter
    log_path = tmp_path / "resume.jsonl"
    em1 = AuditEmitter(log_path=log_path)
    e1 = em1.emit(event="e1", actor="a", resource="r", outcome="ALLOW")

    em2 = AuditEmitter(log_path=log_path)
    e2 = em2.emit(event="e2", actor="a", resource="r", outcome="ALLOW")

    assert e2.seq == 1
    assert e2.prev_hash == e1.entry_hash
    result = em2.verify_chain()
    assert result["valid"] is True
    assert result["entry_count"] == 2


def test_tail_returns_last_n_entries(emitter):
    for i in range(15):
        emitter.emit(event=f"e{i}", actor="a", resource="r", outcome="ALLOW")
    tail = emitter.tail(5)
    assert len(tail) == 5
    assert tail[-1]["seq"] == 14


# ---------------------------------------------------------------------------
# Determinism — same inputs produce same entry_hash
# ---------------------------------------------------------------------------

def test_entry_hash_is_deterministic():
    from security.audit_emitter import AuditEntry
    e1 = AuditEntry(seq=0, event="e", actor="a", resource="r", outcome="ALLOW",
                    metadata={}, timestamp="2026-01-01T00:00:00Z", prev_hash="0" * 64)
    e2 = AuditEntry(seq=0, event="e", actor="a", resource="r", outcome="ALLOW",
                    metadata={}, timestamp="2026-01-01T00:00:00Z", prev_hash="0" * 64)
    assert e1.entry_hash == e2.entry_hash
