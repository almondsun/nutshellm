from nutshellm.storage import Store


def test_job_content_is_removed_from_input_after_completion(tmp_path):
    store = Store(str(tmp_path / "test.sqlite3"))
    store.initialize()
    store.enqueue(
        "abc",
        "owner",
        {"scenario_id": None, "task": "private", "segments": []},
        3600,
    )
    claimed = store.claim_next()
    assert claimed and claimed[0] == "abc"
    result = {
        "scenario_id": None,
        "mode": "compare",
        "validation": {"status": "passed"},
        "fallback": None,
        "metrics": {
            "original_input_tokens": 100,
            "optimized_input_tokens": 50,
            "total_tokens_saved": 50,
            "total_latency_ms": 100,
            "estimated_input_cost_saved_usd": 0.001,
            "estimated_total_run_cost_usd": 0.003,
        },
    }
    store.complete("abc", result)
    with store.connect() as conn:
        row = conn.execute(
            "SELECT input_json, result_json FROM jobs WHERE id='abc'"
        ).fetchone()
    assert row["input_json"] is None
    assert "private" not in row["result_json"]
    assert store.aggregate()["saved_tokens"] == 50


def test_quota_is_atomic_and_enforced(tmp_path):
    store = Store(str(tmp_path / "test.sqlite3"))
    store.initialize()
    assert store.consume_quota(("ip", "session"), 1, 10, 10, 0.1)[0]
    allowed, reason = store.consume_quota(
        ("ip", "new-session"), 1, 10, 10, 0.1
    )
    assert not allowed
    assert "client" in reason


def test_budget_reservation_blocks_burst_before_jobs_complete(tmp_path):
    store = Store(str(tmp_path / "test.sqlite3"))
    store.initialize()
    allowed, reason = store.consume_quota(
        ("ip", "session"), 10, 100, 1.0, 1.01
    )
    assert not allowed
    assert "budget" in reason


def test_expired_job_is_not_claimed(tmp_path):
    store = Store(str(tmp_path / "test.sqlite3"))
    store.initialize()
    store.enqueue("expired", "owner", {"scenario_id": "x"}, -1)
    assert store.claim_next() is None
