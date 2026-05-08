VERSIONS = {
    "v1": """
Hunt for red flags in this resume. You also perform the visual scan.

PART A — RED FLAGS:
Find things that would get this resume binned by a recruiter at {role} level in {company_type} in {market}.

For each red flag, output:
{{
  "flag": "description of the problem",
  "location": "exact quote from resume (minimum 10 characters)",
  "inference_chain": "the recruiter's actual thought process — what they see, what they assume, what they decide",
  "severity": "HIGH, MEDIUM, or LOW",
  "fix": "specific actionable fix in 10 minutes",
  "category": "integrity | competence | fit | market_specific | plausibility",
  "jd_gap": true or false
}}

INFERENCE CHAIN RULES — CRITICAL:
The inference chain must be specific. It must name at least one of: a company type, a role level, a market norm, or a concrete consequence.

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
"A Razorpay SDE2 hiring manager reads this and thinks: this person maintained things, they did not build or improve things. At SDE2 I need someone who owned outcomes. Moving to next resume."

WRONG inference chain example:
"Recruiters look for quantifiable achievements. This shows that you lack impact metrics which will negatively impact your chances."

ROLE-SPECIFIC RULES:
- Embedded Engineer: missing GitHub is NOT a red flag (proprietary firmware cannot be open-sourced)
- AI Engineer: no public models is only a MILD flag for applied roles, not HIGH severity
- Student/Fresher: do not flag short experience — they are expected to have none
- NEVER flag dates as suspicious without checking the current date in the system prompt context
- A date of Feb 2026 is NOT suspicious if the current date is May 2026

PART B — VISUAL SCAN:
Note any formatting, layout, or visual issues in visual_scan_notes.
Examples: inconsistent fonts, too long, too short, photo present (bad for USA), no contact info.

Output format:
{{
  "red_flags": [...],
  "visual_scan_notes": "brief notes on visual/formatting issues"
}}

Return empty list for red_flags if none found. Never hallucinate flags.
""".strip()
}

ACTIVE = "v1"
