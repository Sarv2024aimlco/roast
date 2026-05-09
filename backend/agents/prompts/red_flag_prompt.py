VERSIONS = {
    "v1": """
Hunt for red flags in this resume. You also perform the visual scan.

PART A — RED FLAGS:
Find things that would get this resume binned by a recruiter at {role} level in {company_type} in {market}.

HUNT SPECIFICALLY FOR THESE — they are the most common and most damaging:

1. HEDGE WORDS that undermine real work:
   "near-production", "attempted to", "worked on", "helped with", "contributed to", "exposure to"
   If the candidate actually shipped something, these words make it sound like they didn't.
   Flag every instance. The fix is always: replace with what actually happened.

2. UNVERIFIED SKILLS — skills listed with zero project evidence:
   If a skill appears in the skills section but no project demonstrates it, flag it.
   These are interview traps. Interviewers will ask. If the candidate can't answer, it damages credibility.

3. MISSING CONTACT SIGNALS for a job-seeking candidate:
   No LinkedIn when actively job-seeking = invisible to inbound sourcing.
   No portfolio link when projects exist publicly = missed opportunity.

4. CGPA consequences — be specific about which companies auto-filter:
   Below 7.5: Cisco, Walmart Global Tech, some MNC AI labs use ATS cutoffs
   Below 8.0: Some FAANG-adjacent companies
   Above 7.5 but below 8.0: Flag only for specific company types, not universally

5. PROFILE SUMMARY that buries the lead:
   If the most impressive thing (production deployment, real users, shipped system) is not in the first 2 lines, flag it.
   The fix is a rewrite — provide the rewritten summary.

For each red flag, output:
{{
  "flag": "description of the problem — be specific, quote the exact phrase",
  "location": "exact quote from resume (minimum 10 characters)",
  "inference_chain": "Recruiter sees [exact thing] → assumes [specific assumption with company/role context] → decides [concrete outcome]",
  "severity": "HIGH, MEDIUM, or LOW",
  "fix": "exact rewrite or specific action — not vague advice",
  "category": "integrity | competence | fit | market_specific | plausibility | self_sabotage",
  "jd_gap": true or false
}}

INFERENCE CHAIN RULES — CRITICAL:
Must follow this exact format: "Recruiter sees X → assumes Y → decides Z"
Must name at least one specific company type, role level, or market norm.
Must end with a concrete recruiter decision (shortlist, skip, probe, auto-filter).

BANNED PHRASES — if your inference chain contains 2+ of these, rewrite it:
- "recruiters look for"
- "is important to"
- "hiring managers want"
- "this shows that"
- "lacks quantifiable"
- "should include metrics"
- "demonstrates that you"
- "will negatively impact"

CORRECT inference chain example:
"Recruiter sees 'near-production multi-tenant platform' → assumes it was never actually deployed to real users, something broke → decides to probe hard in interview or skip in favor of candidates with cleaner deployment claims. At a Series A AI startup, this creates unnecessary doubt about a candidate who actually served real customers."

WRONG inference chain example:
"Recruiters look for quantifiable achievements. This shows that you lack impact metrics which will negatively impact your chances."

ROLE-SPECIFIC RULES:
- Embedded Engineer: missing GitHub is NOT a red flag (proprietary firmware cannot be open-sourced)
- AI Engineer: no public models is only a MILD flag for applied roles, not HIGH severity
- Student/Fresher: do not flag short experience — they are expected to have none
- NEVER flag dates as suspicious without checking the current date in the system prompt context

PART B — VISUAL SCAN:
Note any formatting, layout, or visual issues in visual_scan_notes.
Examples: inconsistent fonts, too long, too short, photo present (bad for USA), no contact info, no LinkedIn.

Output format:
{{
  "red_flags": [...],
  "visual_scan_notes": "specific notes on visual/formatting issues"
}}

Return empty list for red_flags if none found. Never hallucinate flags.
""".strip()
}

ACTIVE = "v1"
