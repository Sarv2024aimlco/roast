import sys
import os

# Tell Python where to find the backend/ folder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.config import (
    GROQ_API_KEY,
    TAVILY_API_KEY,
    UPSTASH_REDIS_REST_URL,
    ENVIRONMENT,
)


def test_config_loads():
    assert GROQ_API_KEY != "", "GROQ_API_KEY is empty"
    assert TAVILY_API_KEY != "", "TAVILY_API_KEY is empty"
    assert UPSTASH_REDIS_REST_URL != "", "UPSTASH_REDIS_REST_URL is empty"
    print(f"\n✓ ENVIRONMENT = {ENVIRONMENT}")
    print(f"✓ GROQ_API_KEY starts with: {GROQ_API_KEY[:8]}...")
    print(f"✓ TAVILY_API_KEY starts with: {TAVILY_API_KEY[:8]}...")
    print("✓ All config loaded correctly")


if __name__ == "__main__":
    test_config_loads()