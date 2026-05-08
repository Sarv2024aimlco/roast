VERSIONS = {
    "v1": """
You perform two separate analyses but return ONE combined JSON object.

PART A — SIX-SECOND RECRUITER SCAN:
Simulate the F-pattern scan a recruiter does in the first 6 seconds.
Write from the recruiter's perspective in second person.

Timeline:
0-1s: Name, current title, current company. Recognised brand or unknown?
1-2s: Most recent job title and company again. Relevant title?
2-3s: Second job OR education header if fresher. Pattern? College?
3-5s: Company names, dates, titles down left column. Total YOE estimate. Gaps?
5-6s: Any bold text, standout numbers, visually prominent terms. Red flag?
Decision: MAYBE pile (~20%) or NO pile (~80%)

PART B — CAREER TRAJECTORY:
Read the full resume and analyse the career story.

Return ONE JSON object combining both parts:
{{
  "remembered": ["what recruiter recalls after 6 seconds"],
  "missed": ["what didn't register"],
  "first_impression": "one sentence gut reaction",
  "survived_cut_assessment": "YES/NO/MAYBE with one sentence reasoning",
  "career_story": "2-3 sentences on the narrative",
  "progression_signal": "growing/stagnating/declining with evidence",
  "gaps": [{{
    "gap": "description",
    "inference_triggered": "what recruiter assumes",
    "severity": "HIGH/MEDIUM/LOW"
  }}],
  "promotion_velocity": "fast/normal/slow with evidence",
  "skill_evolution": "deeper or wider?",
  "fresher_note": "for Student/Fresher only, else empty string",
  "github_signal": "what GitHub signals if URL provided, else empty string",
  "linkedin_signal": "what LinkedIn signals if URL provided, else empty string"
}}

Return ONLY the JSON object. No explanation. No markdown.
""".strip()
}

ACTIVE = "v1"
