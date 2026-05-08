"""
Pre-populate script — run once before launch.
Ingests market intelligence for all Tier 1/2 combinations.
Takes ~45-60 minutes total. Run in a separate terminal.

Usage:
    cd /home/sarvesh/projects/roast
    uv run python3 scripts/prepopulate.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
from ingestion.pipeline import run_ingestion_for_combo

COMBINATIONS = [
    ('SDE1', 'Indian Product Company (Tier 1)', 'India'),
    ('SDE1', 'Indian Service Company', 'India'),
    ('SDE1', 'Early Stage Startup', 'India'),
    ('SDE2', 'Early Stage Startup', 'India'),
    ('SDE2', 'FAANG / Big Tech', 'India'),
    ('Senior SDE', 'Indian Product Company (Tier 1)', 'India'),
    ('AI Engineer', 'Growth Stage Startup', 'India'),
    ('ML Engineer', 'Indian Product Company (Tier 1)', 'India'),
    ('Full Stack Engineer', 'Indian Product Company (Tier 1)', 'India'),
    ('Backend Engineer', 'Indian Product Company (Tier 1)', 'India'),
    ('Data Engineer', 'Indian Product Company (Tier 1)', 'India'),
    ('Data Scientist', 'Indian Product Company (Tier 1)', 'India'),
    ('Data Analyst', 'Indian Product Company (Tier 1)', 'India'),
    ('VLSI Design Engineer', 'Semiconductor / Hardware', 'India'),
    ('Embedded Systems Engineer', 'Semiconductor / Hardware', 'India'),
    ('Product Manager', 'Indian Product Company (Tier 1)', 'India'),
    ('DevOps / SRE', 'Indian Product Company (Tier 1)', 'India'),
]


async def main():
    total = len(COMBINATIONS)
    success = 0
    failed = 0

    print(f"Pre-populating {total} combinations...")
    print("=" * 60)

    for i, (role, company_type, market) in enumerate(COMBINATIONS, 1):
        print(f"\n[{i}/{total}] {role} / {company_type} / {market}")
        start = time.time()

        try:
            summary = await run_ingestion_for_combo(
                role=role,
                company_type=company_type,
                market=market,
                force_refresh=True,
            )
            elapsed = round(time.time() - start, 1)
            print(f"  Stored: {summary.signals_stored} | Discarded: {summary.signals_discarded} | {elapsed}s")
            if summary.signals_stored > 0:
                success += 1
            else:
                print(f"  WARNING: 0 signals stored")
                failed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

        if i < total:
            await asyncio.sleep(3)

    print("\n" + "=" * 60)
    print(f"Done. {success} succeeded, {failed} failed.")


if __name__ == "__main__":
    asyncio.run(main())
