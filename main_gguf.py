"""
main_gguf.py

Production incident reconstruction pipeline using:

- Qwen2.5-1.5B-Instruct-GGUF
- llama-cpp-python
- Pydantic schemas
- Structured JSON generation
- Verification
- Enrichment
- Evaluation integration

Author: Production Template
"""

import logging
import os
import time
from typing import List, Optional

import numpy as np
from llama_cpp import Llama
from pydantic import BaseModel, ConfigDict, Field

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s | %(message)s",
)

LOGGER = logging.getLogger(__name__)


# =========================================================
# CONFIG
# =========================================================

CONFIG = {
    "model_path": "model/Qwen2.5-1.5B-Instruct-GGUF/qwen2.5-1.5b-instruct-q4_k_m.gguf",  # for max quality: "model/Qwen2.5-1.5B-Instruct-GGUF/qwen2.5-1.5b-instruct-q8_0.gguf"
    "llama": {
        "n_ctx": 8192,
        "n_threads": np.max([1, os.cpu_count() - 1]),
        "n_batch": 512,
        "verbose": False,
        "temperature": 0.0,
        "max_tokens": 1024,
    },
}


# =========================================================
# WORKLOG
# =========================================================

WORKLOG = """
INC-88421

Packet loss spike in Montreal cluster EAGG-MTL-02.
Latency 12ms → 241ms.
BGP flaps detected.

RT-EAGG-19:
TEMP=97C
FAN_RPM=0
CRC_ERR=11842

FAN-TRAY-2 failure confirmed.

Technician Maria L replaced fan tray.

BGP reset 10.9.0.1
Convergence 96 sec

Recovery after hardware replacement.
"""


# =========================================================
# PROMPTS
# =========================================================

EXTRACTION_PROMPT = """
You are an industrial incident reconstruction system.

TASK:
Generate a structured incident reconstruction report.

RULES:
- Preserve chronology
- Preserve telemetry
- Preserve identifiers
- Preserve technician actions
- Preserve evidence
- Preserve causal relationships
- Do NOT hallucinate

WORKLOG:

{worklog}
"""


VERIFICATION_PROMPT = """
You are a strict validation engine.

Verify:

- Missing telemetry
- Missing identifiers
- Missing events
- Hallucinations
- Invalid chronology

WORKLOG:
{worklog}

EXTRACTION:
{extraction}
"""


ENRICHMENT_PROMPT = """
You are a correction engine.

Fix issues identified during verification.

WORKLOG:
{worklog}

EXTRACTION:
{extraction}

VERIFICATION:
{verification}
"""


# =========================================================
# SCHEMAS
# =========================================================


class ReasoningStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: int
    step_type: str
    title: str
    explanation: str

    evidence: List[str] = Field(default_factory=list)

    extracted_entities: List[str] = Field(default_factory=list)

    causal_dependency: Optional[str] = None
    temporal_reference: Optional[str] = None

    confidence: float

    validation_status: str


class IncidentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str

    root_cause: Optional[str] = None

    impacted_systems: List[str] = Field(default_factory=list)

    severity: Optional[str] = None

    reasonings: List[ReasoningStep] = Field(default_factory=list)


class VerificationIssue(BaseModel):
    issue_type: str
    details: str


class VerificationResult(BaseModel):
    fix_required: bool

    issues: List[VerificationIssue] = Field(default_factory=list)


# =========================================================
# MODEL
# =========================================================


def load_llm(config: dict) -> Llama:

    if not os.path.exists(config["model_path"]):
        raise RuntimeError(f"GGUF model file missing: {config['model_path']}")
    LOGGER.info("Loading GGUF model using n_threads=%d", config["llama"]["n_threads"])

    return Llama(
        model_path=config["model_path"],
        n_ctx=config["llama"]["n_ctx"],
        n_threads=config["llama"]["n_threads"],
        n_batch=config["llama"]["n_batch"],
        verbose=config["llama"]["verbose"],
    )


# =========================================================
# STRUCTURED GENERATION
# =========================================================


def generate_structured(
    llm: Llama,
    prompt: str,
    schema_model: type[BaseModel],
    config: dict,
):

    schema = schema_model.model_json_schema()

    response = llm.create_chat_completion(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        response_format={
            "type": "json_object",
            "schema": schema,
        },
        max_tokens=config["llama"]["max_tokens"],
        temperature=config["llama"]["temperature"],
    )

    content = response["choices"][0]["message"]["content"]

    return schema_model.model_validate_json(content)


# =========================================================
# EXTRACTION
# =========================================================


def extract(
    llm: Llama,
    worklog: str,
    config: dict,
) -> IncidentSummary:

    prompt = EXTRACTION_PROMPT.format(worklog=worklog)

    return generate_structured(
        llm=llm,
        prompt=prompt,
        schema_model=IncidentSummary,
        config=config,
    )


# =========================================================
# VERIFY
# =========================================================


def verify(
    llm: Llama,
    worklog: str,
    extraction: IncidentSummary,
    config: dict,
) -> VerificationResult:

    prompt = VERIFICATION_PROMPT.format(
        worklog=worklog,
        extraction=extraction.model_dump_json(indent=2),
    )

    return generate_structured(
        llm=llm,
        prompt=prompt,
        schema_model=VerificationResult,
        config=config,
    )


# =========================================================
# ENRICH
# =========================================================


def enrich(
    llm: Llama,
    worklog: str,
    extraction: IncidentSummary,
    verification: VerificationResult,
    config: dict,
) -> IncidentSummary:

    if not verification.fix_required:
        return extraction

    prompt = ENRICHMENT_PROMPT.format(
        worklog=worklog,
        extraction=extraction.model_dump_json(indent=2),
        verification=verification.model_dump_json(indent=2),
    )

    return generate_structured(
        llm=llm,
        prompt=prompt,
        schema_model=IncidentSummary,
        config=config,
    )


# =========================================================
# MAIN
# =========================================================


def main():

    start = time.time()

    llm = load_llm(CONFIG)

    LOGGER.info("STEP: extraction")

    extraction = extract(
        llm,
        WORKLOG,
        CONFIG,
    )
    print(extraction.model_dump_json(indent=2))

    LOGGER.info("STEP: verification")

    verification = verify(
        llm,
        WORKLOG,
        extraction,
        CONFIG,
    )
    print(verification.model_dump_json(indent=2))

    LOGGER.info("STEP: enrichment")

    final = enrich(
        llm,
        WORKLOG,
        extraction,
        verification,
        CONFIG,
    )

    elapsed = time.time() - start
    hours, rem = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(rem, 60)
    elapsed_ts = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    LOGGER.info(
        "Pipeline completed in %s",
        elapsed_ts,
    )

    print(final.model_dump_json(indent=2))

    print(f"worklog: {len(WORKLOG)} chars, {len(WORKLOG.splitlines())} lines: \n{WORKLOG}")


if __name__ == "__main__":
    main()
