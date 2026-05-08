VERSIONS = {
    "v1": """
Assess where this resume sits in the actual applicant pool for {role} at {company_type} in {market}.

You have access to:
- Market context (what the pool looks like)
- Breaking signal (what changed this week)
- Anonymised corpus signals (if available — real opted-in data from previous analyses)

CRITICAL — PERCENTILE CALIBRATION:
Calibrate the percentile against applicants at the SAME experience level, not all applicants.
- If the candidate is a Student/Fresher or Junior (0-2 years): compare against OTHER freshers/students applying for this role
- A fresher with production experience, shipped projects, and GitHub presence should be 60th-80th percentile among freshers
- Do NOT compare a fresher against senior engineers with 5+ years experience
- The percentile must reflect realistic competition at this experience level

Output:
{
  "strengths_vs_pool": ["specific strengths compared to typical applicants AT THE SAME LEVEL"],
  "weaknesses_vs_pool": ["specific weaknesses compared to typical applicants AT THE SAME LEVEL"],
  "percentile_estimate": {
    "range": "e.g. 65th-75th percentile among fresher/junior applicants",
    "reasoning": "must cite actual pool signals and specify the comparison group",
    "confidence": "estimated or calibrated"
  },
  "highest_leverage_change": "ONE specific actionable change that would move the percentile most",
  "estimated_impact": "what that change would do",
  "jd_fit_score": "e.g. 7/10 — missing Kafka and system design depth (only if JD provided, else null)"
}

highest_leverage_change must be ONE specific thing. Not generic advice.
""".strip()
}

ACTIVE = "v1"
