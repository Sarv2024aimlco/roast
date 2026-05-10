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
    # ── Already populated ─────────────────────────────────────────────────────
    ('Software Engineer / Associate', 'Indian Product Company', 'India'),
    ('Software Engineer / Associate', 'Indian Service Company', 'India'),
    ('SDE1', 'Indian Product Company', 'India'),
    ('SDE1', 'Indian Service Company', 'India'),
    ('SDE1', 'Startup', 'India'),
    ('SDE2 / Senior SDE', 'Indian Product Company', 'India'),
    ('SDE2 / Senior SDE', 'FAANG / Big Tech', 'India'),
    ('SDE2 / Senior SDE', 'Startup', 'India'),
    ('AI Engineer', 'Startup', 'India'),
    ('AI Engineer', 'Indian Product Company', 'India'),
    ('AI/ML Engineer', 'Indian Product Company', 'India'),
    ('AI/ML Engineer', 'Startup', 'India'),
    ('Full Stack Engineer', 'Indian Product Company', 'India'),
    ('Backend Engineer', 'Indian Product Company', 'India'),
    ('Data Engineer', 'Indian Product Company', 'India'),
    ('Data Scientist', 'Indian Product Company', 'India'),
    ('Data Analyst', 'Indian Product Company', 'India'),
    ('VLSI Design Engineer', 'Semiconductor / Hardware', 'India'),
    ('Embedded Systems Engineer', 'Semiconductor / Hardware', 'India'),
    ('Product Manager', 'Indian Product Company', 'India'),
    ('DevOps / SRE', 'Indian Product Company', 'India'),
    ('Business Analyst', 'Indian Product Company', 'India'),
    ('Business Analyst', 'Consulting / IB', 'India'),

    # ── MNC India gaps ────────────────────────────────────────────────────────
    ('Software Engineer / Associate', 'MNC India (Non-FAANG)', 'India'),
    ('SDE1', 'MNC India (Non-FAANG)', 'India'),
    ('AI Engineer', 'MNC India (Non-FAANG)', 'India'),
    ('AI/ML Engineer', 'MNC India (Non-FAANG)', 'India'),
    ('Data Analyst', 'MNC India (Non-FAANG)', 'India'),
    ('Data Scientist', 'MNC India (Non-FAANG)', 'India'),
    ('Business Analyst', 'MNC India (Non-FAANG)', 'India'),

    # ── FAANG gaps ────────────────────────────────────────────────────────────
    ('SDE1', 'FAANG / Big Tech', 'India'),
    ('Software Engineer / Associate', 'FAANG / Big Tech', 'India'),
    ('AI Engineer', 'FAANG / Big Tech', 'India'),
    ('Data Scientist', 'FAANG / Big Tech', 'India'),
    ('Data Engineer', 'FAANG / Big Tech', 'India'),
    ('Product Manager', 'FAANG / Big Tech', 'India'),

    # ── Startup gaps ──────────────────────────────────────────────────────────
    ('Full Stack Engineer', 'Startup', 'India'),
    ('Backend Engineer', 'Startup', 'India'),
    ('Data Analyst', 'Startup', 'India'),
    ('Data Scientist', 'Startup', 'India'),
    ('Data Engineer', 'Startup', 'India'),
    ('Product Manager', 'Startup', 'India'),
    ('DevOps / SRE', 'Startup', 'India'),

    # ── Service company gaps ──────────────────────────────────────────────────
    ('Business Analyst', 'Indian Service Company', 'India'),
    ('SDE2 / Senior SDE', 'Indian Service Company', 'India'),

    # ── VLSI — all company types ──────────────────────────────────────────────
    ('VLSI Design Engineer', 'Indian Product Company', 'India'),
    ('VLSI Design Engineer', 'MNC India (Non-FAANG)', 'India'),
    ('VLSI Design Engineer', 'FAANG / Big Tech', 'India'),
    ('VLSI Design Engineer', 'Startup', 'India'),

    # ── Embedded — all company types ─────────────────────────────────────────
    ('Embedded Systems Engineer', 'Indian Product Company', 'India'),
    ('Embedded Systems Engineer', 'MNC India (Non-FAANG)', 'India'),
    ('Embedded Systems Engineer', 'FAANG / Big Tech', 'India'),
    ('Embedded Systems Engineer', 'Startup', 'India'),

    # ── Software Engineer / Associate — remaining company types ───────────────
    ('Software Engineer / Associate', 'Startup', 'India'),
    ('Software Engineer / Associate', 'Consulting / IB', 'India'),

    # ── Data Analyst — all company types ─────────────────────────────────────
    ('Data Analyst', 'Indian Service Company', 'India'),
    ('Data Analyst', 'MNC India (Non-FAANG)', 'India'),
    ('Data Analyst', 'FAANG / Big Tech', 'India'),
    ('Data Analyst', 'Startup', 'India'),
    ('Data Analyst', 'Consulting / IB', 'India'),
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
                force_refresh=False,  # skip if already populated
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
