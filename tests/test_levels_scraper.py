import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ingestion.levels_scraper import fetch_levels_salary


async def main():
    print("\n── Levels.fyi scraper test ──")

    result = await fetch_levels_salary("Google", "SDE2")

    if not result:
        print("✗ No data returned")
        return

    print(f"✓ Company: {result['company']}")
    print(f"✓ Role: {result['role']}")
    print(f"✓ URL: {result['source_url']}")
    print(f"✓ Levels found: {len(result['levels'])}")

    for level in result["levels"][:5]:
        print(f"  → {level['level']}: {level['total']} total, {level['base']} base")

    print(f"\n── Raw text sample (first 500 chars) ──")
    print(result["raw_text"][:500])


if __name__ == "__main__":
    asyncio.run(main())

