import json
import structlog
from backend.agents.schemas import CompetitiveOutput, PercentileEstimate
from backend.agents.prompts.template import build_system_prompt
from backend.agents.prompts.competitive_prompt import VERSIONS as CP_VERSIONS, ACTIVE as CP_ACTIVE
from backend.agents.schemas import MarketContextOutput, JDRequirements
from backend.llm.router import call_groq_8b

logger = structlog.get_logger()


async def run_competitive_agent(
    resume_text: str,
    market_context: MarketContextOutput,
    breaking_signal: str,
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    user_context: str = "",
    jd_requirements: JDRequirements | None = None,
    corpus_signals: list[dict] | None = None,
    combo_count: int = 0,
    session_id: str = "",
) -> CompetitiveOutput:
    """
    Agent 4 — runs in parallel.
    Estimates where this resume sits in the applicant pool.
    Uses corpus signals when available for calibrated estimates.
    """
    task = CP_VERSIONS[CP_ACTIVE]  # no .format() — prompt contains JSON braces

    system = build_system_prompt(
        role=role,
        company_type=company_type,
        market=market,
        experience_level=experience_level,
        agent_task=task,
        agent_output_rules="Return only valid JSON matching the schema.",
    )

    corpus_section = ""
    if corpus_signals and len(corpus_signals) >= 5:
        corpus_section = f"""
ANONYMISED CORPUS SIGNALS ({len(corpus_signals)} opted-in analyses for this combination):
{json.dumps(corpus_signals[:20], indent=2)}
Corpus size: {len(corpus_signals)} — use "calibrated" confidence if >= 30, else "estimated"
"""

    jd_section = ""
    if jd_requirements:
        jd_section = f"\n\nJD REQUIREMENTS:\n{jd_requirements.model_dump_json(indent=2)}"

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"""RESUME TEXT:
{resume_text[:3000]}

MARKET CONTEXT:
{market_context.competitive_pool_description}
{market_context.live_context_summary}

BREAKING SIGNAL (last 7 days):
{breaking_signal or 'No breaking signal available'}

USER CONTEXT: {user_context or 'None provided'}
{corpus_section}
{jd_section}

Produce the CompetitivePositioning JSON output.""",
        },
    ]

    try:
        text, meta = await call_groq_8b(
            messages, max_tokens=1000, temperature=0.2, session_id=session_id
        )

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        data = json.loads(text)
        output = CompetitiveOutput(**data)

        logger.info(
            "competitive_agent_complete",
            session_id=session_id,
            percentile=output.percentile_estimate.range,
            confidence=output.percentile_estimate.confidence,
            model=meta.get("model"),
            prompt_version=CP_ACTIVE,
        )

        return output

    except Exception as e:
        logger.error("competitive_agent_failed", error=str(e), session_id=session_id)
        return CompetitiveOutput(
            strengths_vs_pool=[],
            weaknesses_vs_pool=[],
            percentile_estimate=PercentileEstimate(
                range="Unable to estimate",
                reasoning="Analysis failed",
                confidence="estimated",
            ),
            highest_leverage_change="Analysis unavailable",
            estimated_impact="",
            jd_fit_score=None,
        )
