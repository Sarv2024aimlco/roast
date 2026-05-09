"""
TechnicalDepthAgent — the most important new agent.

Evaluates the resume from the perspective of a senior engineer
who actually understands what was built. Not a recruiter simulation.
Not keyword matching. Genuine technical evaluation.

Uses DuckDuckGo search to look up unfamiliar technologies in real time
so it can evaluate them accurately even if they're newer than training data.
"""

import json
import re
import structlog
from pydantic import BaseModel
from backend.agents.tech_search import lookup_multiple
from backend.llm.router import call_technical_depth_agent as _call_agent

logger = structlog.get_logger()


# ── Output schema ─────────────────────────────────────────────────────────────

class ProjectEvaluation(BaseModel):
    name: str                    # project name
    what_it_proves: str          # what this demonstrates technically
    difficulty_level: str        # tutorial / intermediate / advanced / exceptional
    strongest_signal: str        # the single most impressive technical decision
    what_is_missing: str         # what would make this genuinely stronger
    resume_vs_reality: str       # is the resume underselling or overselling the work?


class TechnicalDepthOutput(BaseModel):
    project_evaluations: list[ProjectEvaluation]
    overall_technical_level: str      # honest assessment of technical depth
    most_differentiated_signal: str   # the single thing that makes this candidate stand out
    biggest_technical_gap: str        # what's genuinely missing technically
    communication_gap: str            # what's real but poorly communicated in the resume
    honest_summary: str               # 2-3 sentences, no softening


# ── Technology extraction ─────────────────────────────────────────────────────

def _extract_technologies(resume_text: str) -> list[str]:
    """
    Extract specific niche technology names that might need lookup.
    Focused on algorithms, protocols, and specialised tools.
    """
    # Specific known niche terms worth looking up
    specific_terms = [
        'Bayesian NBV', 'NBV', 'd-vector', 'SIP', 'GGUF', 'QLoRA',
        'RRF fusion', 'FTS5', 'sqlite-vec', 'ESTOP', 'LiDAR proximity',
        'SpeechBrain', 'MediaPipe', 'TFLite INT8', 'YOLOv11',
        'LangGraph', 'CrewAI', 'Unsloth', 'PRAW', 'asyncio.to_thread',
    ]

    found = []
    text_lower = resume_text.lower()
    for term in specific_terms:
        if term.lower() in text_lower:
            found.append(term)

    return found[:6]  # max 6 lookups


# ── Agent prompt ──────────────────────────────────────────────────────────────

TECH_DEPTH_SYSTEM = """You are a senior engineer with 10+ years of experience who has hired 50+ engineers.
You are reviewing a resume for a {role} role at {company_type} in {market}.

Your job is NOT to simulate a recruiter. Your job is to actually understand what was built
and evaluate it honestly from a technical perspective.

You have been given:
1. The full resume text
2. Technical context about specific technologies mentioned (from real-time lookup)
3. The target role and market

For each project/experience, evaluate:
- What does this actually demonstrate technically? Be specific.
- Is this genuinely hard or is it tutorial-level work in {year}?
- What's the strongest technical signal?
- What's missing that would make this stronger?
- Is the resume accurately communicating the complexity, or underselling/overselling?

DIFFICULTY LEVELS — calibrate against the candidate's experience level ({experience_level}):
- tutorial: following a guide, using a library as documented, no novel decisions
- intermediate: combining multiple systems, some novel decisions, real constraints
- advanced: non-trivial architecture decisions, production constraints, genuine problem-solving
- exceptional: genuinely rare for this experience level, would impress senior engineers

IMPORTANT: A fresher/student who has built a production system with circuit breakers, hybrid retrieval,
and WebSocket streaming is ADVANCED, not intermediate. Calibrate against peers at the same level.

Be honest. If something is impressive, say why specifically. If something is weak, say why.
Do not soften feedback. The candidate needs accurate information, not encouragement.

Return ONLY valid JSON matching this schema:
{{
  "project_evaluations": [
    {{
      "name": "project name",
      "what_it_proves": "specific technical capabilities demonstrated",
      "difficulty_level": "tutorial|intermediate|advanced|exceptional",
      "strongest_signal": "the single most impressive technical decision or implementation",
      "what_is_missing": "what would make this genuinely stronger",
      "resume_vs_reality": "underselling|accurate|overselling — with explanation"
    }}
  ],
  "overall_technical_level": "honest 2-3 sentence assessment",
  "most_differentiated_signal": "the single thing that makes this candidate stand out from peers",
  "biggest_technical_gap": "what is genuinely missing technically for this role",
  "communication_gap": "what is real and impressive but poorly communicated in the resume",
  "honest_summary": "2-3 sentences, no softening, what a senior engineer actually thinks"
}}"""


async def run_technical_depth_agent(
    resume_text: str,
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    session_id: str = "",
) -> TechnicalDepthOutput:
    """
    Agent that evaluates the resume with genuine technical understanding.
    Looks up unfamiliar technologies in real time before evaluating.
    Runs in parallel with other agents.
    """
    from datetime import datetime
    year = datetime.now().year

    # Step 1 — extract niche technologies that need lookup
    techs_to_lookup = _extract_technologies(resume_text)

    # Step 2 — look them up in parallel
    tech_context = {}
    if techs_to_lookup:
        logger.info(
            "tech_depth_looking_up",
            technologies=techs_to_lookup,
            session_id=session_id,
        )
        tech_context = await lookup_multiple(techs_to_lookup, context=role)

    # Step 3 — build tech context string for prompt
    tech_context_str = ""
    if tech_context:
        tech_context_str = "\n\nTECHNOLOGY CONTEXT (from real-time lookup):\n"
        for tech, description in tech_context.items():
            if description:
                tech_context_str += f"- {tech}: {description[:200]}\n"

    # Step 4 — run evaluation
    system = TECH_DEPTH_SYSTEM.format(
        role=role,
        company_type=company_type,
        market=market,
        year=year,
        experience_level=experience_level,
    )

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"""RESUME:
{resume_text[:5000]}

TARGET: {role} at {company_type} in {market} ({experience_level})
{tech_context_str}

Evaluate the technical depth of this resume.""",
        },
    ]

    try:
        text, meta = await _call_agent(
            messages, max_tokens=1500, temperature=0.2, session_id=session_id
        )

        # Extract JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        data = json.loads(text)

        # Coerce project_evaluations
        evaluations = []
        for p in data.get("project_evaluations", []):
            try:
                evaluations.append(ProjectEvaluation(**p))
            except Exception:
                continue

        output = TechnicalDepthOutput(
            project_evaluations=evaluations,
            overall_technical_level=data.get("overall_technical_level", ""),
            most_differentiated_signal=data.get("most_differentiated_signal", ""),
            biggest_technical_gap=data.get("biggest_technical_gap", ""),
            communication_gap=data.get("communication_gap", ""),
            honest_summary=data.get("honest_summary", ""),
        )

        logger.info(
            "tech_depth_agent_complete",
            session_id=session_id,
            projects_evaluated=len(evaluations),
            model=meta.get("model"),
            techs_looked_up=len([v for v in tech_context.values() if v]),
        )

        return output

    except Exception as e:
        logger.error("tech_depth_agent_failed", error=str(e), session_id=session_id)
        return TechnicalDepthOutput(
            project_evaluations=[],
            overall_technical_level="Technical evaluation unavailable.",
            most_differentiated_signal="",
            biggest_technical_gap="",
            communication_gap="",
            honest_summary="Technical depth evaluation failed.",
        )
