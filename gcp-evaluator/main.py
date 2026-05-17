"""
LangChain + HF Qwen prompting pipeline with:
- Structured output (PydanticOutputParser)
- ChatPromptTemplate
- HF Transformers via LangChain
- MLflow tracking
"""

import os
import time
from typing import List

import mlflow
import mlflow.transformers

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFacePipeline

from pydantic import BaseModel, ConfigDict, Field

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline,
)


# =========================================================
# SCHEMAS
# =========================================================


class OutputStructure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    justifications: str


class VerificationIssue(BaseModel):
    issue_type: str
    details: str


class VerificationResult(BaseModel):
    fix_required: bool
    issues: List[VerificationIssue] = Field(default_factory=list)


# =========================================================
# PROMPTS
# =========================================================

EXTRACTION_PROMPT = ChatPromptTemplate.from_template(
    """
You are an expert industrial incident reconstruction system.

TASK:
Generate a concise structured incident summary and justification.

RULES:
- Preserve telemetry
- Preserve IPs
- Preserve device identifiers
- Preserve technician actions
- Preserve chronology
- Do NOT hallucinate
- Ignore noise and irrelevant chatter

WORKLOG:
{worklog}

{format_instructions}
"""
)

VERIFICATION_PROMPT = ChatPromptTemplate.from_template(
    """
You are a strict validation engine.

Check:
- missing telemetry
- missing identifiers
- hallucinations
- compressed event chains

Return ONLY structured JSON.

WORKLOG:
{worklog}

EXTRACTED:
{extracted}

{format_instructions}
"""
)

ENRICH_PROMPT = ChatPromptTemplate.from_template(
    """
You are a correction engine.

Fix only if verification requires it.

WORKLOG:
{worklog}

EXTRACTED:
{extracted}

VERIFICATION:
{verification}

{format_instructions}
"""
)


# =========================================================
# MODEL LOADING
# =========================================================


def load_llm(model_name: str):

    model_path = os.path.abspath(model_name)

    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        local_files_only=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",
        torch_dtype="auto",
        local_files_only=True,
    )

    # IMPORTANT FIX:
    # ❌ NO GenerationConfig (caused conflicts)
    # ❌ NO generation_config argument
    # ✔ pass params directly here

    pipe = pipeline(
        task="text-generation",
        model=model,
        tokenizer=tokenizer,
        return_full_text=False,
        max_new_tokens=512,
        temperature=0.1,
        top_p=0.9,
        do_sample=True,
        repetition_penalty=1.05,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id,
    )

    return HuggingFacePipeline(pipeline=pipe)


# =========================================================
# SAFE PARSING
# =========================================================


def safe_parse_output(text: str, schema):

    try:
        return schema.model_validate_json(text)
    except Exception:
        pass

    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON found")

    depth = 0
    in_str = False
    escape = False

    for i, ch in enumerate(text[start:], start):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    json_str = text[start : i + 1]
                    return schema.model_validate_json(json_str)

    raise ValueError("Invalid JSON output")


# =========================================================
# PIPELINE STEPS
# =========================================================


def extract(llm, worklog):

    parser = PydanticOutputParser(OutputStructure)

    chain = EXTRACTION_PROMPT | llm

    raw = chain.invoke(
        {
            "worklog": worklog,
            "format_instructions": parser.get_format_instructions(),
        }
    )

    return safe_parse_output(raw, OutputStructure)


def verify(llm, worklog, extracted):

    parser = PydanticOutputParser(VerificationResult)

    chain = VERIFICATION_PROMPT | llm

    raw = chain.invoke(
        {
            "worklog": worklog,
            "extracted": extracted.model_dump_json(indent=2),
            "format_instructions": parser.get_format_instructions(),
        }
    )

    return safe_parse_output(raw, VerificationResult)


def enrich(llm, worklog, extracted, verification):

    if not verification.fix_required:
        return extracted

    parser = PydanticOutputParser(OutputStructure)

    chain = ENRICH_PROMPT | llm

    raw = chain.invoke(
        {
            "worklog": worklog,
            "extracted": extracted.model_dump_json(indent=2),
            "verification": verification.model_dump_json(indent=2),
            "format_instructions": parser.get_format_instructions(),
        }
    )

    return safe_parse_output(raw, OutputStructure)


# =========================================================
# MAIN
# =========================================================


def main():

    model_name = "../model/Qwen2.5-1.5B-Instruct"

    worklog = """
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

    mlflow.set_experiment("langchain_qwen_pipeline")
    mlflow.transformers.autolog()

    with mlflow.start_run():
        start = time.time()

        llm = load_llm(model_name)

        extraction = extract(llm, worklog)
        verification = verify(llm, worklog, extraction)
        final = enrich(llm, worklog, extraction, verification)

        latency = time.time() - start

        mlflow.log_param("model_name", model_name)
        mlflow.log_metric("latency_sec", latency)
        mlflow.log_metric("fix_required", int(verification.fix_required))

        mlflow.log_text(worklog, "input.txt")
        mlflow.log_text(extraction.model_dump_json(indent=2), "extraction.json")
        mlflow.log_text(verification.model_dump_json(indent=2), "verification.json")
        mlflow.log_text(final.model_dump_json(indent=2), "final.json")

        print(final.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
