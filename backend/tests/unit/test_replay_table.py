"""
Unit tests — Replay Mitigation Table
T-GOV-002
"""
from __future__ import annotations

import time
import uuid

import pytest


@pytest.fixture()
def table():
    from security.replay_table import ReplayMitigationTable
    return ReplayMitigationTable()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_consume_new_jti_succeeds(table):
    jti = str(uuid.uuid4())
    table.consume(jti)  # must not raise


def test_is_replayed_false_for_unknown_jti(table):
    assert table.is_replayed("never-seen-jti") is False


def test_is_replayed_true_after_consume(table):
    jti = str(uuid.uuid4())
    table.consume(jti)
    assert table.is_replayed(jti) is True


def test_try_consume_returns_true_on_first_use(table):
    jti = str(uuid.uuid4())
    assert table.try_consume(jti) is True


def test_try_consume_returns_false_on_replay(table):
    jti = str(uuid.uuid4())
    table.consume(jti)
    assert table.try_consume(jti) is False


# ---------------------------------------------------------------------------
# Replay detection
# ---------------------------------------------------------------------------

def test_consume_same_jti_twice_raises(table):
    jti = str(uuid.uuid4())
    table.consume(jti)
    with pytest.raises(ValueError, match="Replay detected"):
        table.consume(jti)


def test_multiple_distinct_jtis_all_accepted(table):
    jtis = [str(uuid.uuid4()) for _ in range(20)]
    for jti in jtis:
        table.consume(jti)
    assert table.size() == 20


# ---------------------------------------------------------------------------
# Expiry / eviction
# ---------------------------------------------------------------------------

def test_expired_entry_is_evicted_and_reusable():
    from security.replay_table import ReplayMitigationTable
    t = ReplayMitigationTable(leeway_seconds=0)
    jti = str(uuid.uuid4())
    # exp in the past → entry expires immediately after leeway=0
    past_exp = int(time.time()) - 1
    t.consume(jti, exp=past_exp)
    # After eviction the jti should be reusable
    time.sleep(0.05)
    assert t.is_replayed(jti) is False
    t.consume(jti, exp=int(time.time()) + 3600)  # must not raise


def test_size_reflects_active_entries(table):
    for _ in range(5):
        table.consume(str(uuid.uuid4()))
    assert table.size() == 5


def test_clear_empties_table(table):
    table.consume(str(uuid.uuid4()))
    table.clear()
    assert table.size() == 0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_persist_and_reload(tmp_path):
    from security.replay_table import ReplayMitigationTable
    path = str(tmp_path / "replay.json")
    t1 = ReplayMitigationTable(persist_path=path)
    jti = str(uuid.uuid4())
    t1.consume(jti, exp=int(time.time()) + 3600)

    # New instance loads from file
    t2 = ReplayMitigationTable(persist_path=path)
    assert t2.is_replayed(jti) is True


def test_persist_expired_entries_not_reloaded(tmp_path):
    from security.replay_table import ReplayMitigationTable
    path = str(tmp_path / "replay_exp.json")
    t1 = ReplayMitigationTable(persist_path=path, leeway_seconds=0)
    jti = str(uuid.uuid4())
    past_exp = int(time.time()) - 5
    t1.consume(jti, exp=past_exp)

    time.sleep(0.05)
    t2 = ReplayMitigationTable(persist_path=path, leeway_seconds=0)
    assert t2.is_replayed(jti) is False


def test_corrupt_persisted_replay_store_fails_closed(tmp_path):
    from security.replay_table import ReplayMitigationTable

    path = tmp_path / "corrupt-replay.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(RuntimeError, match="refusing requests"):
        ReplayMitigationTable(persist_path=str(path))
