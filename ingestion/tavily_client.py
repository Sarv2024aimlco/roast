import httpx
from backend.config import TAVILY_API_KEY_DEEP, TAVILY_API_KEY_GENERAL
from backend.storage.redis_client import redis

TAVILY_URL = "https://api.tavily.com/search"
MONTHLY_LIMIT = 1000


class TavilyClient:
    def __init__(self, api_key: str, budget_key: str):
        self.api_key = api_key
        self.budget_key = budget_key

    def get_budget(self) -> int:
        count = redis.get(self.budget_key)
        return int(count) if count else 0

    def _increment_budget(self) -> None:
        redis.incr(self.budget_key)

    def budget_remaining(self) -> int:
        return max(0, MONTHLY_LIMIT - self.get_budget())

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        if self.get_budget() >= MONTHLY_LIMIT:
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    TAVILY_URL,
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                    },
                    timeout=10,
                )
                response.raise_for_status()
                results = response.json().get("results", [])
                self._increment_budget()
                return results
        except Exception:
            return []


# Two instances — import these directly, never instantiate TavilyClient yourself
deep = TavilyClient(
    api_key=TAVILY_API_KEY_DEEP,
    budget_key="counter:tavily_deep_calls",
)

general = TavilyClient(
    api_key=TAVILY_API_KEY_GENERAL,
    budget_key="counter:tavily_general_calls",
)
