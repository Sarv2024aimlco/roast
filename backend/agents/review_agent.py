import json
import re
import structlog
from backend.agents.schemas import (
    ReviewOutput, MarketContextOutput, RedFlagOutput,
    SixSecondAndTrajectoryOutput, CompetitiveOutput, JDRequirements,
    TechnicalDepthOutput
)
from backend.agents.prompts.template import build_system_prompt
from backend.agents.prompts.review_prompt import VERSIONS as RV_VERSIONS, ACTIVE as RV_ACTIVE
from backend.llm.router import call_review_agent
from backend.agents.json_utils import extract_json

logger = structlog.get_logger()

MIN_WORDS = 250
MAX_WORDS = 2000

PROSE_FIELDS = [
    "whats_working_section",
    "whats_hurting_section",
    "career_story_section",
    "competitive_position_section",
    "action_plan_section",
]


def _count_words(review: ReviewOutput) -> int:
    return sum(
        len(getattr(review, f, "").split())
        for f in PROSE_FIELDS
    )


def _passes_quality_gate(review: ReviewOutput) -> tuple[bool, str]:
    total = _count_words(review)
    if total < MIN_WORDS:
        return False, f"too_short:{total}"
    if total > MAX_WORDS:
        return False, f"too_long:{total}"
    for field in ["six_second_followups", "whats_hurting_followups",
                  "career_story_followups", "competitive_followups"]:
        if not getattr(review, field, []):
            return False, f"missing_followups:{field}"
    return True, "ok"


def _build_upstream_summary(
    market_context: MarketContextOutput,
    red_flags: RedFlagOutput,
    six_second: SixSecondAndTrajectoryOutput,
    competitive: CompetitiveOutput,
    jd_requirements: JDRequirements | None,
    technical_depth: TechnicalDepthOutput | None = None,
) -> str:
    """
    Deterministic Python function — no LLM.
    Concatenates upstream outputs into one structured input for ReviewAgent.
    Technical depth evaluation leads — recruiter inference is supporting context.
    """
    high_flags = [f for f in red_flags.red_flags if f.severity == "HIGH"]
    other_flags = [f for f in red_flags.red_flags if f.severity != "HIGH"]

    flags_text = ""
    if high_flags:
        flags_text += "HIGH SEVERITY FLAGS:\n"
        for f in high_flags:
            flags_text += f"- {f.flag}\n  Quote: \"{f.location}\"\n  Inference: {f.inference_chain}\n  Fix: {f.fix}\n\n"
    if other_flags:
        flags_text += "OTHER FLAGS:\n"
        for f in other_flags[:5]:
            flags_text += f"- [{f.severity}] {f.flag} | Fix: {f.fix}\n"

    jd_text = ""
    if jd_requirements:
        jd_text = f"""
JD REQUIREMENTS:
Required skills: {', '.join(jd_requirements.required_skills)}
Preferred skills: {', '.join(jd_requirements.preferred_skills)}
Experience range: {jd_requirements.experience_range}
"""

    # Technical depth section — leads the summary
    tech_text = ""
    if technical_depth and technical_depth.project_evaluations:
        tech_text = "TECHNICAL DEPTH EVALUATION:\n"
        tech_text += f"Overall: {technical_depth.overall_technical_level}\n"
        tech_text += f"Most differentiated signal: {technical_depth.most_differentiated_signal}\n"
        tech_text += f"Biggest technical gap: {technical_depth.biggest_technical_gap}\n"
        tech_text += f"Communication gap: {technical_depth.communication_gap}\n"
        tech_text += f"Honest summary: {technical_depth.honest_summary}\n"
        if technical_depth.unverified_skills:
            tech_text += f"UNVERIFIED SKILLS (listed but no project evidence): {', '.join(technical_depth.unverified_skills)}\n"
        tech_text += "\n"
        tech_text += "PROJECT EVALUATIONS:\n"
        for p in technical_depth.project_evaluations:
            tech_text += f"\n{p.name} [{p.difficulty_level.upper()}]:\n"
            tech_text += f"  Proves: {p.what_it_proves}\n"
            tech_text += f"  Strongest signal: {p.strongest_signal}\n"
            tech_text += f"  Missing: {p.what_is_missing}\n"
            tech_text += f"  Resume vs reality: {p.resume_vs_reality}\n"

    return f"""{tech_text}
MARKET CONTEXT:
Sentiment: {market_context.live_context_summary}
Weight map: {json.dumps(market_context.weight_map)}
Format expectations: {market_context.format_expectations}
Competitive pool: {market_context.competitive_pool_description}

SIX-SECOND SCAN (how a non-technical recruiter sees this):
Survived cut: {six_second.survived_cut_assessment}
First impression: {six_second.first_impression}
Remembered: {', '.join(six_second.remembered[:3])}
Career story: {six_second.career_story}
Progression: {six_second.progression_signal}

RED FLAGS (recruiter perspective):
{flags_text or 'No significant red flags found.'}
Visual scan: {red_flags.visual_scan_notes}

COMPETITIVE POSITION:
Percentile: {competitive.percentile_estimate.range} ({competitive.percentile_estimate.confidence})
Reasoning: {competitive.percentile_estimate.reasoning}
Expected CTC range: {competitive.expected_ctc_range or 'Not estimated'}
Highest leverage change: {competitive.highest_leverage_change}
{jd_text}"""


async def run_review_agent(
    resume_text: str,
    market_context: MarketContextOutput,
    red_flags: RedFlagOutput,
    six_second: SixSecondAndTrajectoryOutput,
    competitive: CompetitiveOutput,
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    user_context: str = "",
    jd_requirements: JDRequirements | None = None,
    technical_depth: TechnicalDepthOutput | None = None,
    session_id: str = "",
) -> ReviewOutput:
    """
    Agent 5 — runs alone last.
    Writes the complete flowing review from all upstream outputs.
    Uses full fallback chain with quality gate.
    """
    task = RV_VERSIONS[RV_ACTIVE]

    system = build_system_prompt(
        role=role,
        company_type=company_type,
        market=market,
        experience_level=experience_level,
        agent_task=task,
        agent_output_rules="Return only valid JSON matching the schema. No markdown. No explanation.",
    )

    upstream = _build_upstream_summary(
        market_context, red_flags, six_second, competitive, jd_requirements, technical_depth
    )

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": f"""RESUME TEXT:
{resume_text[:4000]}

UPSTREAM ANALYSIS:
{upstream}

USER CONTEXT: {user_context or 'None provided'}

Write the complete review JSON.""",
        },
    ]

    last_error = None

    # Try up to 2 times per provider (quality gate retry)
    for attempt in range(2):
        try:
            text, meta = await call_review_agent(
                messages=messages,
                max_tokens=3000,
                session_id=session_id,
            )

            # Extract + repair JSON
            import re
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
            data = extract_json(text)

            # Ensure all required fields exist with defaults
            for field in ["jd_alignment_section"]:
                if field not in data:
                    data[field] = ""
            for field in ["six_second_followups", "whats_hurting_followups",
                          "career_story_followups", "competitive_followups"]:
                if field not in data or not data[field]:
                    data[field] = ["Tell me more about this."]

            # Coerce list fields to strings if model returns arrays
            for field in ["whats_working_section", "whats_hurting_section",
                          "career_story_section", "competitive_position_section",
                          "action_plan_section", "jd_alignment_section",
                          "tldr_shortlist_chance", "tldr_biggest_blocker", "tldr_fix_first"]:
                if isinstance(data.get(field), list):
                    data[field] = " ".join(str(x) for x in data[field])
                elif data.get(field) is None:
                    data[field] = ""

            review = ReviewOutput(**data)

            # Quality gate
            passed, reason = _passes_quality_gate(review)
            if not passed:
                logger.warning(
                    "review_quality_gate_failed",
                    reason=reason,
                    attempt=attempt,
                    session_id=session_id,
                )
                if attempt == 0:
                    # Add explicit length instruction and retry
                    messages.append({
                        "role": "assistant",
                        "content": text,
                    })
                    messages.append({
                        "role": "user",
                        "content": f"The review failed quality check: {reason}. Rewrite with 500-1200 words across the prose sections.",
                    })
                    continue
                # Second attempt also failed — use what we have
                logger.warning("review_quality_gate_failed_both_attempts", session_id=session_id)

            logger.info(
                "review_agent_complete",
                session_id=session_id,
                word_count=_count_words(review),
                provider=meta.get("provider"),
                model=meta.get("model"),
                prompt_version=RV_ACTIVE,
            )

            return review

        except Exception as e:
            last_error = e
            logger.error("review_agent_attempt_failed", error=str(e), attempt=attempt, session_id=session_id)

    # All attempts failed — assemble partial review from upstream
    logger.error("review_agent_all_failed", error=str(last_error), session_id=session_id)
    return _assemble_partial_review(six_second, red_flags, competitive, market_context)


def _assemble_partial_review(
    six_second: SixSecondAndTrajectoryOutput,
    red_flags: RedFlagOutput,
    competitive: CompetitiveOutput,
    market_context: MarketContextOutput,
) -> ReviewOutput:
    """
    Last resort — assemble a basic review from upstream outputs
    when ReviewAgent completely fails.
    """
    high_flags = [f for f in red_flags.red_flags if f.severity == "HIGH"]
    flag_text = " ".join([f.flag for f in high_flags[:3]]) if high_flags else "No critical issues found."

    return ReviewOutput(
        tldr_shortlist_chance=competitive.percentile_estimate.range,
        tldr_biggest_blocker=flag_text,
        tldr_fix_first=competitive.highest_leverage_change,
        whats_working_section=" ".join(competitive.strengths_vs_pool[:2]),
        whats_hurting_section=" ".join([f.inference_chain for f in high_flags[:2]]),
        career_story_section=six_second.career_story,
        competitive_position_section=competitive.percentile_estimate.reasoning,
        action_plan_section=competitive.highest_leverage_change,
        jd_alignment_section="",
        six_second_followups=["What can I improve about my first impression?"],
        whats_hurting_followups=["How do I fix the biggest red flag?"],
        career_story_followups=["How do I improve my career narrative?"],
        competitive_followups=["What would move me to the next percentile?"],
    )
