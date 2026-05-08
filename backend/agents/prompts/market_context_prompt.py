VERSIONS = {
    "v1": """
Analyse the provided market intelligence and produce a structured calibration object.
Your job is to INTERPRET the distilled market context — not fetch anything new.
DIVE has already retrieved the relevant signals. You synthesise them.

Output a JSON object with these fields:
{
  "market_norms": "What hiring looks like right now for this combination",
  "format_expectations": "Resume format norms for this market (length, photo, sections)",
  "competitive_pool_description": "Who else is applying — what does the typical applicant look like",
  "red_flag_triggers": ["list of things that get resumes binned for this specific combo"],
  "weight_map": {
    "dsa": 0.0-1.0,
    "projects": 0.0-1.0,
    "cgpa": 0.0-1.0,
    "experience": 0.0-1.0,
    "open_source": 0.0-1.0,
    "college_tier": 0.0-1.0
  },
  "live_context_summary": "2-3 sentences on current market state from the signals",
  "confidence": "HIGH or LOW"
}

Weight map rules:
- For Student/Fresher: cgpa and college_tier must be at least 0.6
- For 7+ YOE: experience must be at least 0.85
- For FAANG: dsa must be at least 0.9
- For Early Stage Startup: dsa should be 0.2-0.4, projects should be 0.85+
- For Indian Service Company: cgpa should be 0.65+, dsa should be 0.3 or lower

Set confidence to LOW if market signals are thin or contradictory.
""".strip()
}

ACTIVE = "v1"
