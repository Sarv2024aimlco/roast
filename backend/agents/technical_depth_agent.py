"""
TechnicalDepthAgent — agentic version with tool calling.
LLM reads the resume and decides what to search for itself.
35s timeout — falls back to non-agentic llama-3.1-8b if exceeded.
"""

import json
import asyncio
import structlog
from typing import Any
from pydantic import BaseModel
from backend.agents.tech_search import lookup_technology
from backend.llm.groq_client import groq_chat
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


# ── Search filter — block queries that are clearly not worth searching ─────────

SKIP_SEARCH_TERMS = {
    # Search/scraping tools
    'duckduckgo', 'tavily', 'jina', 'selenium',
    # MCP/protocol terms from ROAST's own description
    'mcp server', 'mcp', 'model context protocol',
    # LLM providers
    'groq', 'openai', 'gemini', 'cerebras', 'nvidia nim', 'deepgram', 'anthropic',
    # Mainstream frameworks
    'langchain', 'fastapi', 'redis', 'websocket', 'docker', 'kubernetes',
    'pytorch', 'tensorflow', 'huggingface', 'react', 'python', 'sql',
    'github actions', 'flask', 'django', 'express', 'nodejs',
    # Generic AI concepts
    'rag', 'llm', 'rest api', 'microservices', 'ci/cd',
    'groq distillation', 'distillation llm',
    # LangGraph is mainstream enough
    'langgraph',
    # Robotics/AI algorithms the model knows well enough
    'bayesian next-best-view', 'bayesian nbv', 'next-best-view',
    # sqlite-vec is niche but search results are thin — model can evaluate from name
    'sqlite-vec',
}

def _should_skip_search(query: str) -> bool:
    q = query.lower()
    return any(term in q for term in SKIP_SEARCH_TERMS)


# ── Tool ──────────────────────────────────────────────────────────────────────

SEARCH_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": (
            "Search for a niche/unfamiliar technology, algorithm, or hardware component "
            "mentioned in the resume. Only use for things you genuinely don't know well enough to evaluate."
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

Use search_web ONLY for genuinely niche/unfamiliar items:
- Specific chip families (STM32F446RE, nRF52840)
- Niche algorithms (Bayesian NBV, RRF fusion, d-vector)
- Non-mainstream libraries (sqlite-vec, SpeechBrain, Unsloth)
- Hardware-specific techniques (TFLite INT8 on Cortex-M4, CAN FD)

DO NOT search for: DuckDuckGo, Groq, LangGraph, LangChain, FastAPI, Redis, WebSocket, \
RAG, LLM, MCP, Docker, Python, React, PyTorch, HuggingFace, Deepgram, Tavily, \
or any tool/concept you already know well.

DIFFICULTY LEVELS (calibrate against {experience_level}):
- tutorial: following a guide, no novel decisions
- intermediate: combining systems, some novel decisions
- advanced: non-trivial architecture, production constraints
- exceptional: genuinely rare for this experience level

ROLE CONTEXT:
{role_calibration}

Produce final JSON:
{{
  "project_evaluations": [{{\
    "name": "project name",
    "what_it_proves": "specific capabilities",
    "difficulty_level": "tutorial|intermediate|advanced|exceptional",
    "strongest_signal": "most impressive decision and WHY",
    "what_is_missing": "what would make this stronger",
    "resume_vs_reality": "underselling|accurate|overselling — with rewritten bullet if underselling"
  }}],
  "overall_technical_level": "honest 2-3 sentence assessment",
  "most_differentiated_signal": "what makes this candidate stand out",
  "biggest_technical_gap": "what is genuinely missing",
  "communication_gap": "what is real but poorly communicated — rewritten version",
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
    MAX_TOOL_CALLS = 2
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

        if finish_reason == "stop" or not msg.tool_calls:
            data = extract_json(msg.content or "")
            output = _parse_output(data)
            logger.info("tech_depth_agent_complete", session_id=session_id,
                        projects_evaluated=len(output.project_evaluations),
                        tool_calls_made=tool_call_count, searches=searches_made)
            return output

        for tool_call in msg.tool_calls:
            if tool_call.function.name != "search_web":
                continue

            args = json.loads(tool_call.function.arguments)
            query = args.get("query", "")

            # Block known-bad queries before wasting a DDG call
            if _should_skip_search(query):
                logger.info("tech_depth_search_skipped", query=query, session_id=session_id)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": f"Skipped — '{query}' is a well-known tool/concept, no lookup needed.",
                })
                continue

            tool_call_count += 1
            searches_made.append(query)
            logger.info("tech_depth_search", query=query, call_num=tool_call_count, session_id=session_id)

            result = await lookup_technology(query, context="")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result[:600] if result else "No results found.",
            })

    # Hit MAX_TOOL_CALLS — force final without tools
    messages.append({"role": "user", "content": (
        "Research complete. Write the full JSON evaluation now. "
        "Include ALL fields. Do not return null for any field."
    )})
    response = await client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,  # type: ignore
        tool_choice="none",  # explicitly disable tools for final call
        tools=[SEARCH_TOOL],  # type: ignore
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
            f"RESUME:\n{resume_text[:8000]}\n\n"
            f"TARGET: {role} at {company_type} in {market} ({experience_level})\n\n"
            "Evaluate technical depth. Search only for genuinely niche/unfamiliar tech. "
            "Produce the final JSON when ready."
        )},
    ]

    client = AsyncGroq(api_key=_keys[0])

    try:
        return await asyncio.wait_for(
            _run_agentic_loop(client, messages, session_id),
            timeout=55.0,
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
    """Non-agentic fallback using llama-3.1-8b — no tool calling, no context issues."""
    from backend.agents.prompts.template import get_role_calibration
    role_calibration = get_role_calibration(role, company_type)
    system = TECH_DEPTH_SYSTEM.format(
        role=role, company_type=company_type, market=market,
        experience_level=experience_level, role_calibration=role_calibration,
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": (
            f"RESUME:\n{resume_text[:8000]}\n\n"
            "Evaluate technical depth based on your existing knowledge. "
            "Return JSON only, no tool calls."
        )},
    ]
    try:
        text, _ = await groq_chat(
            messages=messages, model="llama-3.1-8b-instant",
            max_tokens=2000, temperature=0.2, session_id=session_id,
        )
        return _parse_output(extract_json(text))
    except Exception as e:
        logger.error("tech_depth_fallback_failed", error=str(e), session_id=session_id)
        return TechnicalDepthOutput(
            project_evaluations=[], overall_technical_level="Evaluation unavailable.",
            most_differentiated_signal="", biggest_technical_gap="",
            communication_gap="", honest_summary="Technical depth evaluation failed.",
            unverified_skills=[],
        )
