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
import torch
from pydantic import BaseModel, ConfigDict, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_huggingface import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline


# =========================================================
# PYDANTIC SCHEMAS
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

EXTRACTION_PROMPT = ChatPromptTemplate.from_template("""
You are a high-fidelity industrial incident reconstruction system.

Extract structured incident representation.

RULES:
- Preserve telemetry
- Preserve identifiers
- No hallucination
- Atomic events only

WORKLOG:
{worklog}

{format_instructions}
""")

VERIFICATION_PROMPT = ChatPromptTemplate.from_template("""
You are a strict validation engine.

Check:
- missing telemetry
- missing events
- hallucinations

Return structured JSON.

WORKLOG:
{worklog}

EXTRACTED:
{extracted}
{format_instructions}
""")


# =========================================================
# MODEL LOADING (HF → LangChain wrapper)
# =========================================================

def load_llm(model_name: str):
    MODEL_PATH = os.path.abspath(model_name)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
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
    )

    return HuggingFacePipeline(pipeline=pipe)


# =========================================================
# PIPELINE STEPS
# =========================================================

def extract(llm, worklog: str):
    parser = PydanticOutputParser(pydantic_object=OutputStructure)

    chain = EXTRACTION_PROMPT | llm | parser

    return chain.invoke({
        "worklog": worklog,
        "format_instructions": parser.get_format_instructions(),
    })


def verify(llm, worklog: str, extracted: OutputStructure):
    parser = PydanticOutputParser(pydantic_object=VerificationResult)

    chain = VERIFICATION_PROMPT | llm | parser

    return chain.invoke({
        "worklog": worklog,
        "extracted": extracted.model_dump_json(indent=2),
        "format_instructions": parser.get_format_instructions(),
    })


def enrich(llm, worklog, extracted, verification):
    if not verification.fix_required:
        return extracted

    prompt = ChatPromptTemplate.from_template("""
Fix only if required.

WORKLOG:
{worklog}

EXTRACTED:
{extracted}

VERIFICATION:
{verification}
""")

    chain = prompt | llm | PydanticOutputParser(pydantic_object=OutputStructure)

    return chain.invoke({
        "worklog": worklog,
        "extracted": extracted.model_dump_json(indent=2),
        "verification": verification.model_dump_json(indent=2),
    })


# =========================================================
# MAIN
# =========================================================

def main():

    model_name = "../model/Qwen2.5-1.5B-Instruct"

    worklog = """
INC-99102
Packet loss in Toronto TD-14 cluster.
ICMP failure > 40% for 10.22.14.0/24.
Device SW-CORE-19 unstable.
Technician Alex P dispatched.
NIC replaced and rebooted.
"""

    mlflow.set_experiment("langchain_qwen_pipeline")

    with mlflow.start_run():

        start = time.time()

        llm = load_llm(model_name)

        extraction = extract(llm, worklog)
        verification = verify(llm, worklog, extraction)
        final = enrich(llm, worklog, extraction, verification)

        latency = time.time() - start

        # =====================================================
        # MLflow logging
        # =====================================================

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