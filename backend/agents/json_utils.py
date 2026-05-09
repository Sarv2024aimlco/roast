"""
Shared JSON extraction utility for all agents.
Handles: markdown code blocks, preamble text, thinking tags, malformed JSON.
"""

import re
import json


def extract_json(text: str) -> dict:
    """
    Extract and parse a JSON object from model output that may contain:
    - Markdown code blocks (```json ... ```)
    - Preamble text ("Here is the JSON...")
    - Thinking tags (<think>...</think>)
    - Trailing commas, unescaped quotes (via json-repair)

    Raises json.JSONDecodeError if all attempts fail.
    """
    # Strip thinking tags (qwen3)
    if "</think>" in text:
        text = text[text.index("</think>") + len("</think>"):].strip()

    # Strip markdown code blocks
    code_block = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if code_block:
        text = code_block.group(1).strip()

    # Find outermost { ... }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]

    # Try standard parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: json-repair handles trailing commas, unescaped chars, etc.
    try:
        from json_repair import repair_json
        repaired = repair_json(text, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
    except Exception:
        pass

    # Last resort: raise original error
    return json.loads(text)
