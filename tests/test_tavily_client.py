import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingestion.tavily_client import deep, general


async def test_deep_search():
    print("\n── Deep client ──")
    print(f"Budget used: {deep.get_budget()}")
    print(f"Budget remaining: {deep.budget_remaining()}")

    results = await deep.search("SDE2 software engineer jobs site:reddit.com India 2026", max_results=3)

    print(f"Results returned: {len(results)}")
    for r in results:
        print(f"  → {r.get('title', 'no title')}")
        print(f"    {r.get('url', 'no url')}")
    print(f"Budget after search: {deep.get_budget()}")


async def test_general_search():
    print("\n── General client ──")
    results = await general.search("software engineer hiring India 2026", max_results=3)
    print(f"Results returned: {len(results)}")
    for r in results:
        print(f"  → {r.get('title', 'no title')}")


async def main():
    await test_deep_search()
    await test_general_search()
    print("\n✓ Tavily client tests done")


if __name__ == "__main__":
    asyncio.run(main())
