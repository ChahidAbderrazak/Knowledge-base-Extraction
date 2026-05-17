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
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

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
You are an expert industrial incident reconstruction and summarization system.

Your task:
Generate a concise but complete structured incident summary and technical justification.

STRICT RULES:
- Preserve all telemetry values
- Preserve all IP addresses
- Preserve all device identifiers
- Preserve all technician actions
- Preserve chronology
- Do NOT hallucinate
- Do NOT merge unrelated events
- Keep events atomic and traceable to the source worklog
- Summary must remain factual and operationally accurate

OUTPUT REQUIREMENTS:
- summary:
  Clear operational incident summary
- justifications:
  Explain why the summary is correct using evidence from the worklog

WORKLOG:
{worklog}

{format_instructions}
""")


VERIFICATION_PROMPT = ChatPromptTemplate.from_template("""
You are a strict industrial incident extraction validator.

Validate the generated extraction against the original worklog.

CHECK FOR:
- missing telemetry
- missing IPs
- missing identifiers
- missing technician actions
- hallucinated content
- compressed or merged event chains
- chronology inconsistencies
- unsupported conclusions

OUTPUT REQUIREMENTS:
Return ONLY valid structured JSON.

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

    return chain.invoke(
        {
            "worklog": worklog,
            "format_instructions": parser.get_format_instructions(),
        }
    )


def verify(llm, worklog: str, extracted: OutputStructure):
    parser = PydanticOutputParser(pydantic_object=VerificationResult)

    chain = VERIFICATION_PROMPT | llm | parser

    return chain.invoke(
        {
            "worklog": worklog,
            "extracted": extracted.model_dump_json(indent=2),
            "format_instructions": parser.get_format_instructions(),
        }
    )


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

    return chain.invoke(
        {
            "worklog": worklog,
            "extracted": extracted.model_dump_json(indent=2),
            "verification": verification.model_dump_json(indent=2),
        }
    )


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
    worklog = """
INC-88421

[03:11:42 UTC] Automated monitoring alert triggered for edge aggregation cluster EAGG-MTL-02 in Montreal production region.

Alert source:
Telemetry anomaly detector v4.8.12

Primary condition:
- sustained packet retransmission > 18%
- latency spike from baseline 12ms → 241ms
- intermittent BGP neighbor flaps

Affected ranges:
172.18.44.0/24
172.18.45.0/24

Initial impacted hosts:
172.18.44.12
172.18.44.19
172.18.45.31

---

NOC NOTES

03:14 UTC
Operator JChen unable to establish SSH session to router RT-EAGG-19.
Console access responsive but delayed.

03:16 UTC
Syslog burst detected:

THERMAL_WARN: ASIC temperature threshold exceeded
TEMP=97C
FAN_RPM=0
MODULE=LINECARD-2

03:17 UTC
Additional alarms received from TOR-SW-884 and TOR-SW-887.

03:18 UTC
False-positive alert suspected by Tier1 due to temporary recovery window (~45 sec), but packet loss resumed immediately afterward.

03:21 UTC
Customer ticket volume increased sharply.
VoIP degradation reported by multiple tenants.

---

RAW DEVICE OUTPUT

RT-EAGG-19# show interfaces counters

xe-0/0/1:
CRC_ERR=11842
INPUT_DROP=9921
OUTPUT_DROP=17

xe-0/0/3:
CRC_ERR=0
INPUT_DROP=0

RT-EAGG-19# show environment

TEMP SENSOR 4 = 101C
FAN-TRAY-2 = FAILED
PSU-1 = OK
PSU-2 = OK

---

TECHNICIAN ACTIONS

03:29 UTC
Technician Maria L assigned onsite escalation.

03:41 UTC
Maria L reported abnormal acoustic vibration from chassis cooling subsystem.

03:44 UTC
Fan tray replacement initiated.

03:49 UTC
Unexpected secondary issue observed:
- linecard reseat triggered transient routing instability
- BGP peer 10.9.0.1 reset
- convergence time ~96 sec

03:55 UTC
Packet retransmission dropped to 2.1%.

04:01 UTC
ASIC temperature normalized to 71C.

04:07 UTC
SSH responsiveness restored.

---

INTERNAL CHATTER / NOISE

"maybe firmware?"
"could be optics again lol"
"who touched this rack last week?"
"ignore previous alert maybe duplicate"
"not sure if TOR-SW-887 is actually impacted"
"temporary graph gap due to exporter restart"

Random pasted output:

user=testsvc-prod-991
session=8ff2aa9912
cache_status=MISS
debug=false
build=2026.04.771

---

POST-INCIDENT NOTES

Root cause likely mechanical cooling failure on FAN-TRAY-2 causing ASIC overheating and downstream packet corruption.

Monitoring recommendation:
observe RT-EAGG-19 for 24h.

Pending:
- verify no latent optics damage
- inspect LINECARD-2 thermal interface
- review environmental cooling in rack MTL-R42

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
