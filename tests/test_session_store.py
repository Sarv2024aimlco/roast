import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.storage.session_store import create_session, get_session, update_session


def test_session_lifecycle():
    # 1. Create
    session = create_session("SDE2", "India", "product")
    sid = session["session_id"]

    print(f"\n✓ Created session: {sid[:8]}...")
    assert session["status"] == "pending"
    assert session["role"] == "SDE2"

    # 2. Fetch from Redis
    fetched = get_session(sid)
    assert fetched is not None, "Session not found in Redis"
    assert fetched["session_id"] == sid
    print("✓ Fetched from Redis correctly")

    # 3. Update
    updated = update_session(sid, {"status": "processing"})
    assert updated["status"] == "processing"
    assert updated["role"] == "SDE2"  # other fields preserved
    print("✓ Updated status to processing")

    # 4. Confirm update persisted
    refetched = get_session(sid)
    assert refetched["status"] == "processing"
    print("✓ Update persisted in Redis")

    # 5. Non-existent session returns None
    missing = get_session("does-not-exist")
    assert missing is None
    print("✓ Missing session returns None correctly")

    print("\n✓ All session store tests passed")


if __name__ == "__main__":
    test_session_lifecycle()
