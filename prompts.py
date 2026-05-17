# =========================
# OUTPUT SCHEMA
# =========================

# {{
#   "incident_summary": "",
#   "event_timeline": [
#     {{
#       "timestamp": "",
#       "event": "",
#       "source": ""
#     }}
#   ],
#   "entities": {{
#     "devices": [],
#     "circuits": [],
#     "technicians": [],
#     "ips": []
#   }},
#   "conflicts_detected": [],
#   "final_resolution": ""
# }}


# =========================================================
# PROMPTS (SIMPLIFIED - CONSTRAINED DECODING HANDLES VALIDITY)
# =========================================================

PROMPT_V1 = """
You are an industrial incident reconstruction system.

Your task is STRICT structured extraction from operational logs.

You are NOT summarizing.

You are NOT allowed to omit technical details.

You must extract:
- timestamps (if present)
- all telemetry signals (packet loss, ICMP, SSH failures)
- all IPs and device identifiers
- all technician actions
- full event sequence without compression

--------------------------------------------------------
RULES
--------------------------------------------------------

1. Do NOT merge events
2. Do NOT drop telemetry
3. Do NOT infer missing facts
4. Each event must be atomic
5. Preserve ALL technical signals exactly as written
6. final_resolution must include root cause + fix

--------------------------------------------------------
INPUT WORKLOG
--------------------------------------------------------

{input_text}

--------------------------------------------------------
OUTPUT
--------------------------------------------------------

Return structured incident extraction.
"""


PROMPT_V2 = """
You are a high-fidelity incident reconstruction system.

Extract a complete structured representation of the incident.

CRITICAL REQUIREMENTS:
- Lossless extraction of all diagnostic signals
- No summarization or compression
- No hallucination
- Preserve all IPs, devices, telemetry, and actions

--------------------------------------------------------
GUIDELINES
--------------------------------------------------------

- Each event must correspond to a real log entry
- Maintain full chronological fidelity
- Keep all system, technician, and monitoring signals
- Ensure final resolution reflects root cause and remediation

--------------------------------------------------------
INPUT WORKLOG
--------------------------------------------------------

{input_text}

--------------------------------------------------------
OUTPUT
--------------------------------------------------------

Return structured incident extraction.
"""


VERIFIER_PROMPT = """
You are a strict validation engine.

Your job is to verify completeness of extracted incident data.

Check for:
- missing telemetry (ICMP, packet loss, SSH failures)
- missing devices or IPs
- hallucinated information
- missing or compressed events
- schema violations

Return ONLY JSON:

{{
  "fix_required": boolean,
  "issues": []
}}

WORKLOG:
{input_text}

EXTRACTED:
{extracted_json}
"""
