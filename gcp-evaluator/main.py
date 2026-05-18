from __future__ import annotations

import logging
from typing import List

import instructor
import mlflow
from evaluator import HybridEvaluator
from pydantic import BaseModel, ConfigDict
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from prompts import ENRICH_PROMPT, EXTRACT_PROMPT, JUDGE_PROMPT, VERIFY_PROMPT

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


# =========================================================
# SCHEMAS
# =========================================================


class Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    reasonings: List[str]


class Verification(BaseModel):
    fix_required: bool
    issues: List[str]


class JudgeSchema(BaseModel):
    faithfulness: float
    coverage: float
    coherence: float
    hallucination_detected: bool
    overall_score: float
    reasoning: str


# =========================================================
# MODEL LOADER
# =========================================================


def load_client(model_path: str):
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",
        torch_dtype="auto",
        local_files_only=True,
    )

    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        temperature=0.1,
        return_full_text=False,
    )

    return instructor.from_transformers(pipe)


# =========================================================
# PIPELINE STEPS
# =========================================================


def extract(client, text: str) -> Extraction:
    prompt = EXTRACT_PROMPT.format(input_text=text)

    return client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        response_model=Extraction,
    )


def verify(client, text: str, extraction: Extraction) -> Verification:
    prompt = VERIFY_PROMPT.format(
        input_text=text,
        extracted=extraction.model_dump_json(indent=2),
    )

    return client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        response_model=Verification,
    )


def enrich(client, text: str, extraction: Extraction, verification: Verification) -> Extraction:
    if not verification.fix_required:
        return extraction

    prompt = ENRICH_PROMPT.format(
        input_text=text,
        extracted=extraction.model_dump_json(indent=2),
        verification=verification.model_dump_json(indent=2),
    )

    return client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        response_model=Extraction,
    )


# =========================================================
# MAIN
# =========================================================

WORKLOG = """
Packet loss spike in Montreal cluster.
FAN failure detected.
Technician replaced fan tray.
System recovered.
"""

MODEL_PATH = "../model/Qwen2.5-1.5B-Instruct"
EMBED_PATH = "../model/all-MiniLM-L6-v2"


def main():

    mlflow.set_experiment("qwen_full_pipeline")

    client = load_client(MODEL_PATH)

    evaluator = HybridEvaluator(
        embed_model=EMBED_PATH,
        judge_client=client,
    )

    with mlflow.start_run():
        logger.info("STEP: extract")
        extraction = extract(client, WORKLOG)

        logger.info("STEP: verify")
        verification = verify(client, WORKLOG, extraction)

        logger.info("STEP: enrich")
        final = enrich(client, WORKLOG, extraction, verification)

        logger.info("STEP: evaluate")

        result = evaluator.evaluate(
            source=WORKLOG,
            extracted=final.model_dump(),
            judge_prompt=JUDGE_PROMPT,
            judge_schema=JudgeSchema,
        )

        mlflow.log_metric("overall", result.overall)

        print(final.model_dump_json(indent=2))
        print(result)


if __name__ == "__main__":
    main()
