"""
Knowledge extraction pipeline using:
- Hugging Face Transformers
- Outlines structured decoding
- Pydantic schema validation
- MLflow tracking
"""

import time
from typing import Dict, List, Optional

import mlflow
import outlines
import torch
from pydantic import BaseModel, ConfigDict, Field
from transformers import AutoModelForCausalLM, AutoTokenizer

# =========================================================
# PYDANTIC SCHEMAS
# =========================================================


class Event(BaseModel):
    """Atomic event extracted from incident logs."""

    timestamp: Optional[str] = None
    description: str
    actor: Optional[str] = None
    system: Optional[str] = None


class Entity(BaseModel):
    """Entity extracted from incident logs."""

    name: str
    type: str
    metadata: Optional[Dict[str, str]] = None


class IncidentExtraction(BaseModel):
    """Structured incident extraction schema."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str
    incident_summary: str
    event_timeline: List[Event] = Field(default_factory=list)
    entities: Dict[str, Entity] = Field(default_factory=dict)
    final_resolution: str


class VerificationIssue(BaseModel):
    """Single verification issue."""

    issue_type: str
    details: str


class VerificationResult(BaseModel):
    """Verification output schema."""

    fix_required: bool
    issues: List[VerificationIssue] = Field(default_factory=list)


# =========================================================
# PROMPTS
# =========================================================


def build_extraction_prompt(worklog: str) -> str:
    """Build extraction prompt.

    Args:
        worklog: Raw incident worklog.

    Returns:
        Formatted extraction prompt.
    """

    return f"""
You are a high-fidelity industrial incident reconstruction system.

Extract a complete structured incident representation.

CRITICAL RULES:
- Preserve all telemetry
- Preserve all IPs
- Preserve all device identifiers
- Preserve all technician actions
- Never hallucinate
- Never merge unrelated events
- Each event must be atomic

WORKLOG:
{worklog}

Return structured extraction only.
"""


def build_verification_prompt(
    worklog: str,
    extracted_json: str,
) -> str:
    """Build verification prompt.

    Args:
        worklog: Original worklog.
        extracted_json: Structured extraction JSON.

    Returns:
        Formatted verification prompt.
    """

    return f"""
You are a strict incident extraction validator.

Check:
- missing telemetry
- missing events
- hallucinations
- missing entities
- compressed event chains


Return ONLY valid JSON:

{{
  "fix_required": boolean,
  "issues": []
}}

WORKLOG:
{worklog}

EXTRACTED:
{extracted_json}
"""


# =========================================================
# MODEL LOADING
# =========================================================


def load_model_and_tokenizer(model_name: str):
    """Load Hugging Face model and tokenizer.

    Args:
        model_name: Local or remote HF model path.

    Returns:
        Tuple of (tokenizer, model, elapsed_time).
    """

    print("[STEP] Loading tokenizer...")
    start = time.time()

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        local_files_only=True,
    )

    print("[STEP] Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        device_map="auto",
        local_files_only=True,
    )

    model.eval()

    elapsed = time.time() - start
    print(f"[DONE] Model loaded successfully. ({elapsed:.2f}s)")

    return tokenizer, model


def build_structured_generator(model, tokenizer):
    """Build structured constrained decoder.

    Args:
        model: Hugging Face causal LM.
        tokenizer: Hugging Face tokenizer.

    Returns:
        Tuple of (structured_model, elapsed_time).
    """

    print("[STEP] Building Outlines structured generator...")
    start = time.time()

    structured_model = outlines.from_transformers(
        model,
        tokenizer,
    )

    elapsed = time.time() - start
    print(f"[DONE] Structured generator ready. ({elapsed:.2f}s)")

    return structured_model


def extract_incident(structured_model, worklog: str):
    """Extract structured incident information.

    Args:
        structured_model: Outlines structured model.
        worklog: Raw incident worklog.

    Returns:
        extraction.
    """

    print("[STEP] Running extraction...")
    start = time.time()

    prompt = build_extraction_prompt(worklog)

    result = structured_model(
        prompt,
        IncidentExtraction,
        max_new_tokens=384,
        temperature=0.1,
    )

    validated = IncidentExtraction.model_validate_json(result)

    elapsed = time.time() - start
    print(f"[DONE] Extraction complete. ({elapsed:.2f}s)")

    return validated


def extract_json_payload(text: str) -> str:
    """Extract the first complete JSON object from model output."""
    text = text.strip()

    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence) :].strip()

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model output.")

    depth = 0
    in_string = False
    escape = False

    for idx, ch in enumerate(text[start:], start):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]

    raise ValueError("Incomplete JSON object in model output.")


def verify_extraction(model, tokenizer, worklog: str, extracted: IncidentExtraction):
    """Verify extraction quality.

    Args:
        model: Hugging Face model.
        tokenizer: Hugging Face tokenizer.
        worklog: Original worklog.
        extracted: Structured extraction.

    Returns:
        verification_result
    """

    print("[STEP] Running verification...")
    start = time.time()

    prompt = build_verification_prompt(
        worklog=worklog,
        extracted_json=extracted.model_dump_json(indent=2),
    )

    messages = [
        {
            "role": "system",
            "content": "You are a strict validation engine.",
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(
        [text],
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=300,
            temperature=0.1,
        )

    generated_tokens = output[0][inputs.input_ids.shape[-1] :]

    decoded = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True,
    ).strip()

    # print("[DEBUG] Verification raw output:")
    # print(decoded)
    json_payload = extract_json_payload(decoded)
    verified = VerificationResult.model_validate_json(json_payload)

    elapsed = time.time() - start
    print(f"[DONE] Verification complete. ({elapsed:.2f}s)")

    return verified


# =========================================================
# OUTLINES CONSTRAINED DECODER (ZERO-FAILURE CORE)
# =========================================================


def incident_generator(generator, prompt: str):
    return generator(
        prompt,
        IncidentExtraction,
        max_new_tokens=384,
        temperature=0.1,
    )


# =========================================================
# ENRICHMENT (OPTIONAL, NOT REQUIRED FOR CORRECTNESS)
# =========================================================


def enrich(
    generator,
    worklog: str,
    extracted: IncidentExtraction,
    verification: VerificationResult,
):

    if not verification.fix_required:
        return extracted

    prompt = f"""
Improve extracted incident ONLY if missing critical information exists.

WORKLOG:
{worklog}

CURRENT EXTRACTION:
{extracted.model_dump_json(indent=2)}

VERIFICATION:
{verification.model_dump_json(indent=2)}

If verification reports issues, update the extraction to fix them.
If verification reports no issues, return the current extraction unchanged.
"""

    output = incident_generator(generator, prompt)

    # print("[DEBUG] Verification raw output:")
    # print(decoded)
    # json_payload = extract_json_payload(decoded)

    print("[DEBUG] enrichment raw output:")
    print(output)

    try:
        return IncidentExtraction.model_validate(output).model_dump_json(indent=2)
    except Exception as e:
        print(f"[ERROR] Enrichment failed to produce valid output: {e}")
        print("Returning the raw enrichment output.")
        return output
        # print("Returning original extraction without enrichment.")
        # return extracted


def evaluate_extraction(extraction: IncidentExtraction):
    """Evaluate extraction quality metrics.

    Args:
        extraction: Structured extraction.

    Returns:
        metrics_dict
    """

    print("[STEP] Evaluating extraction...")
    start = time.time()

    metrics = {
        "valid_schema": 1,
        "event_count": len(extraction.event_timeline),
        "entity_count": len(extraction.entities),
        "has_resolution": int(bool(extraction.final_resolution)),
    }

    elapsed = time.time() - start
    print(f"[DONE] Evaluation complete. ({elapsed:.2f}s)")

    return metrics


# =========================================================
# MAIN
# =========================================================


def main():
    """Run incident extraction pipeline."""

    print("=" * 80)
    print("KNOWLEDGE EXTRACTION PIPELINE")
    print("=" * 80)

    model_name = "model/Qwen2.5-1.5B-Instruct"

    worklog = """
INC-99102

System monitoring detected intermittent packet loss on core switch cluster in Toronto data node TD-14.

Initial alert triggered at 03:41 AM when ICMP ping failures exceeded threshold (packet loss > 40%) for IP range 10.22.14.0/24.

NOC engineer report:
Device SW-CORE-19 unstable. SSH access failed.

At 03:58 AM, ICMP timeout for 10.22.14.23 and 10.22.14.31.

Technician Alex P dispatched.

NIC failure suspected after overheating logs.

NIC replaced and device rebooted.

Next action: monitor stability for 24 hours.
"""

    mlflow.set_experiment("knowledge_extraction_pipeline")

    with mlflow.start_run():

        start_time = time.time()

        print("[STEP] Initializing pipeline...")

        tokenizer, model = load_model_and_tokenizer(
            model_name=model_name,
        )
        generator = outlines.from_transformers(model, tokenizer)

        structured_model = build_structured_generator(
            model=model,
            tokenizer=tokenizer,
        )

        extraction = extract_incident(
            structured_model=structured_model,
            worklog=worklog,
        )

        verification = verify_extraction(
            model=model,
            tokenizer=tokenizer,
            worklog=worklog,
            extracted=extraction,
        )

        # 3. optional enrichment (only if needed)
        final_output = enrich(generator, worklog, extraction, verification)

        metrics = evaluate_extraction(
            extraction=final_output,
        )

        metrics["latency_sec"] = time.time() - start_time

        print("[STEP] Logging MLflow metrics...")

        mlflow.log_param(
            "model_name",
            model_name,
        )

        for key, value in metrics.items():
            mlflow.log_metric(key, value)

        mlflow.log_text(
            worklog,
            "input_worklog.txt",
        )

        mlflow.log_text(
            extraction.model_dump_json(indent=2),
            "extraction.json",
        )

        mlflow.log_text(
            verification.model_dump_json(indent=2),
            "verification.json",
        )

        print("[DONE] MLflow logging complete.")

        print("\n" + "=" * 80)
        print("FINAL EXTRACTION")
        print("=" * 80)

        print(
            extraction.model_dump_json(
                indent=2,
            )
        )

        print("\n" + "=" * 80)
        print("VERIFICATION")
        print("=" * 80)

        print(
            verification.model_dump_json(
                indent=2,
            )
        )

        print("\n[DONE] Pipeline completed successfully.")


if __name__ == "__main__":
    main()
