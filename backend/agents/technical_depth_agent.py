"""
TechnicalDepthAgent — agentic version with tool calling.
LLM reads the resume and decides what to search for itself.
35s timeout — falls back to non-agentic if exceeded.
"""

import json
import asyncio
import structlog
from typing import Any
from pydantic import BaseModel
from backend.agents.tech_search import lookup_technology
from backend.llm.router import call_technical_depth_agent as _call_agent
from groq import AsyncGroq
from backend.config import GROQ_API_KEYS
from backend.agents.json_utils import extract_json

logger = structlog.get_logger()

_keys = [k.strip() for k in GROQ_API_KEYS.split(",") if k.strip()]

# ── Output schema ─────────────────────────────────────────────────────────────

class ProjectEvaluation(BaseModel):
    name: str
    what_it_proves: str
    difficulty_level: str
    strongest_signal: str
    what_is_missing: str
    resume_vs_reality: str


class TechnicalDepthOutput(BaseModel):
    project_evaluations: list[ProjectEvaluation]
    overall_technical_level: str
    most_differentiated_signal: str
    biggest_technical_gap: str
    communication_gap: str
    honest_summary: str
    unverified_skills: list[str] = []


# ── Tool ──────────────────────────────────────────────────────────────────────

SEARCH_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": (
            "Search the web for technical information about a niche technology, algorithm, "
            "or concept mentioned in the resume that you need to understand to evaluate accurately."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Specific search query"}
            },
            "required": ["query"]
        }
    }
}

# ── System prompt ─────────────────────────────────────────────────────────────

TECH_DEPTH_SYSTEM = """You are a senior engineer with 10+ years of experience who has hired 50+ engineers.
Reviewing a resume for {role} at {company_type} in {market}.

Use the search tool for niche/unfamiliar technologies where knowing more would change your evaluation.

WHEN TO SEARCH: niche algorithms, specific chip families, non-mainstream libraries, domain-specific techniques.

WHEN NOT TO SEARCH:
- Mainstream tools: Python, React, Docker, SQL, FastAPI, Redis, WebSocket, LangChain, PyTorch, HuggingFace
- LLM providers: Groq, OpenAI, Gemini, Cerebras, NVIDIA NIM, Deepgram
- Search/scraping tools: DuckDuckGo, Tavily, Jina, Selenium — these are search APIs
- Generic concepts: RAG, LLM, REST API, microservices, CI/CD, MCP server, WebSocket streaming
- The project's own architecture components (e.g. if resume describes ROAST, don't search for ROAST's tools)
- Anything you already know well enough to evaluate

DIFFICULTY LEVELS (calibrate against {experience_level}):
- tutorial: following a guide, no novel decisions
- intermediate: combining systems, some novel decisions
- advanced: non-trivial architecture, production constraints
- exceptional: genuinely rare for this experience level

ROLE CONTEXT:
{role_calibration}

After searching, produce final JSON:
{{
  "project_evaluations": [{{
    "name": "project name",
    "what_it_proves": "specific capabilities demonstrated",
    "difficulty_level": "tutorial|intermediate|advanced|exceptional",
    "strongest_signal": "most impressive decision and WHY it shows engineering judgment",
    "what_is_missing": "what would make this genuinely stronger",
    "resume_vs_reality": "underselling|accurate|overselling — with rewritten bullet if underselling"
  }}],
  "overall_technical_level": "honest 2-3 sentence assessment with percentile context",
  "most_differentiated_signal": "what makes this candidate stand out and why it's rare",
  "biggest_technical_gap": "what is genuinely missing for this role",
  "communication_gap": "what is real but poorly communicated — include rewritten version",
  "honest_summary": "2-3 sentences, no softening",
  "unverified_skills": ["skills listed but no project evidence"]
}}"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_output(data: dict) -> TechnicalDepthOutput:
    evaluations = []
    for p in data.get("project_evaluations", []):
        try:
            evaluations.append(ProjectEvaluation(**p))
        except Exception:
            continue
    return TechnicalDepthOutput(
        project_evaluations=evaluations,
        overall_technical_level=data.get("overall_technical_level", ""),
        most_differentiated_signal=data.get("most_differentiated_signal", ""),
        biggest_technical_gap=data.get("biggest_technical_gap", ""),
        communication_gap=data.get("communication_gap", ""),
        honest_summary=data.get("honest_summary", ""),
        unverified_skills=data.get("unverified_skills", []),
    )


# ── Agentic loop ──────────────────────────────────────────────────────────────

async def _run_agentic_loop(
    client: AsyncGroq,
    messages: list[dict],
    session_id: str,
) -> TechnicalDepthOutput:
    MAX_TOOL_CALLS = 3
    tool_call_count = 0
    searches_made = []

    while tool_call_count <= MAX_TOOL_CALLS:
        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,  # type: ignore
            tools=[SEARCH_TOOL],  # type: ignore
            tool_choice="auto",
            max_tokens=2000,
            temperature=0.2,
        )

        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in (msg.tool_calls or [])
            ] or None,
        })

        # No tool calls — LLM is done
        if finish_reason == "stop" or not msg.tool_calls:
            data = extract_json(msg.content or "")
            output = _parse_output(data)
            logger.info("tech_depth_agent_complete", session_id=session_id,
                        projects_evaluated=len(output.project_evaluations),
                        tool_calls_made=tool_call_count, searches=searches_made)
            return output

        # Execute tool calls
        for tool_call in msg.tool_calls:
            if tool_call.function.name != "search_web":
                continue
            tool_call_count += 1
            args = json.loads(tool_call.function.arguments)
            query = args.get("query", "")
            searches_made.append(query)
            logger.info("tech_depth_search", query=query, call_num=tool_call_count, session_id=session_id)

            result = await lookup_technology(query, context="")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result[:600] if result else "No results found.",
            })

    # Hit MAX_TOOL_CALLS — force final
    messages.append({"role": "user", "content": (
        "Research complete. Write the full JSON evaluation now. "
        "Include ALL fields with real content. Do not return null for any field."
    )})
    response = await client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,  # type: ignore
        max_tokens=3000,
        temperature=0.2,
    )
    data = extract_json(response.choices[0].message.content or "")
    output = _parse_output(data)
    logger.info("tech_depth_agent_complete", session_id=session_id,
                projects_evaluated=len(output.project_evaluations),
                tool_calls_made=tool_call_count, searches=searches_made)
    return output


# ── Public entry point ────────────────────────────────────────────────────────

async def run_technical_depth_agent(
    resume_text: str,
    role: str,
    company_type: str,
    market: str,
    experience_level: str,
    session_id: str = "",
) -> TechnicalDepthOutput:
    from backend.agents.prompts.template import get_role_calibration

    role_calibration = get_role_calibration(role, company_type)
    system = TECH_DEPTH_SYSTEM.format(
        role=role, company_type=company_type, market=market,
        experience_level=experience_level, role_calibration=role_calibration,
    )

    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": (
            f"RESUME:\n{resume_text[:5000]}\n\n"
            f"TARGET: {role} at {company_type} in {market} ({experience_level})\n\n"
            "Evaluate the technical depth. Search only for genuinely niche/unfamiliar tech. "
            "When ready, produce the final JSON."
        )},
    ]

    client = AsyncGroq(api_key=_keys[0])

    try:
        return await asyncio.wait_for(
            _run_agentic_loop(client, messages, session_id),
            timeout=35.0,
        )
    except asyncio.TimeoutError:
        logger.warning("tech_depth_timeout_falling_back", session_id=session_id)
        return await _fallback_evaluation(resume_text, role, company_type, market, experience_level, session_id)
    except Exception as e:
        logger.error("tech_depth_agent_failed", error=str(e), session_id=session_id)
        return await _fallback_evaluation(resume_text, role, company_type, market, experience_level, session_id)


async def _fallback_evaluation(
    resume_text: str, role: str, company_type: str,
    market: str, experience_level: str, session_id: str,
) -> TechnicalDepthOutput:
    from backend.agents.prompts.template import get_role_calibration
    role_calibration = get_role_calibration(role, company_type)
    messages = [
        {"role": "system", "content": TECH_DEPTH_SYSTEM.format(
            role=role, company_type=company_type, market=market,
            experience_level=experience_level, role_calibration=role_calibration,
        )},
        {"role": "user", "content": f"RESUME:\n{resume_text[:5000]}\n\nEvaluate technical depth. Return JSON only."},
    ]
    try:
        text, _ = await _call_agent(messages, max_tokens=2000, temperature=0.2, session_id=session_id)
        return _parse_output(extract_json(text))
    except Exception as e:
        logger.error("tech_depth_fallback_failed", error=str(e), session_id=session_id)
        return TechnicalDepthOutput(
            project_evaluations=[], overall_technical_level="Evaluation unavailable.",
            most_differentiated_signal="", biggest_technical_gap="",
            communication_gap="", honest_summary="Technical depth evaluation failed.",
            unverified_skills=[],
        )
