import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.storage.rate_limit import (
    check_and_increment_rate_limit,
    get_rate_limit_status,
)
import time

TEST_IP = f"test-ip-{int(time.time())}"  # unique IP each run so tests don't collide


def test_rate_limit():
    # First request — should be allowed
    r1 = check_and_increment_rate_limit(TEST_IP)
    assert r1["allowed"] is True, f"First request should be allowed: {r1}"
    assert r1["count"] == 1
    assert r1["remaining"] == 1
    print(f"✓ Request 1: allowed, count={r1['count']}, remaining={r1['remaining']}")

    # Second request — should be allowed
    r2 = check_and_increment_rate_limit(TEST_IP)
    assert r2["allowed"] is True, f"Second request should be allowed: {r2}"
    assert r2["count"] == 2
    assert r2["remaining"] == 0
    print(f"✓ Request 2: allowed, count={r2['count']}, remaining={r2['remaining']}")

    # Third request — should be blocked
    r3 = check_and_increment_rate_limit(TEST_IP)
    assert r3["allowed"] is False, f"Third request should be blocked: {r3}"
    print(f"✓ Request 3: blocked correctly")

    # Status check — count should still be 2 (blocked request was not counted)
    status = get_rate_limit_status(TEST_IP)
    assert status["count"] == 2, f"Count should be 2, got: {status['count']}"
    print(f"✓ Status check: count={status['count']} (blocked request not counted)")

    print("\n✓ All rate limit tests passed")


if __name__ == "__main__":
    test_rate_limit()