"""
prompts.py

Centralized prompt library.
No logic, no models, only text definitions.
"""

EXTRACT_PROMPT = """
You are an industrial incident extraction system.

TASK:
Extract a structured incident summary.

RULES:
- Only use facts from the input
- Do NOT hallucinate
- Preserve technical identifiers
- Preserve chronology

INPUT:
{input_text}
"""


VERIFY_PROMPT = """
You are a strict verification engine.

TASK:
Validate extracted information against the source.

Check:
- factual correctness
- missing information
- hallucinations
- consistency

SOURCE:
{input_text}

EXTRACTION:
{extracted}
"""


ENRICH_PROMPT = """
You are a correction engine.

TASK:
Fix extraction ONLY if verification requires it.

RULES:
- Do NOT add new facts
- Only correct inconsistencies

SOURCE:
{input_text}

EXTRACTION:
{extracted}

VERIFICATION:
{verification}
"""


JUDGE_PROMPT = """
You are a strict LLM evaluator.

Evaluate the extraction.

Return ONLY JSON.

SOURCE:
{input_text}

OUTPUT:
{output}

Return schema:
{
  "faithfulness": float,
  "coverage": float,
  "coherence": float,
  "hallucination_detected": bool,
  "overall_score": float,
  "reasoning": string
}
"""
