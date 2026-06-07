import json
import os
import time
from typing import List, Optional

import outlines
import torch
from pydantic import BaseModel, ConfigDict, Field
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Enable low CPU threads
torch.set_num_threads(2)


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


# =========================================================
# MODEL PATH
# =========================================================

MODEL_NAME = "../model/Qwen2.5-1.5B-Instruct"
# MODEL_NAME = "../model/Phi-3-mini-4k-instruct"


# =========================================================
# 4-bit QUANTIZATION CONFIG
# =========================================================

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

# =========================================================
# TOKENIZER
# =========================================================

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    local_files_only=True,
)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token


# =========================================================
# MODEL (QUANTIZED)
# =========================================================

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    # quantization_config=bnb_config,
    local_files_only=True,
)


# =========================================================
# OUTLINES WRAPPER
# =========================================================

model = outlines.from_transformers(model, tokenizer)


# =========================================================
# INPUT PROMPT
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

WORKLOG = """
CATALINA workfloow
AUTO test started 03:12, poll thread 8
RTE-51 silent on SNMP/161, no get, no trap
ping 10.0.2.1 -> 100% loss, 30ms>NA, ttl 0
reachability probe icmp echo req out, reply none
route via 10.0.0.254 pulse: 2/2 acks then hang
poll event sysUpTime missing, config pull timeout
BGP reset 10.9.0.1
Convergence 96 sec

ping 10.0.2.1: 100% loss, 3 probes, no response
ping 10.0.0.254: 2/3 success, 1 timeout
reachability check icmp echo req/out, reply missing from router

error with conect #hf78.00g.0oh. full apt updagreate needed,
arp table stale, mac 00:16:3e.. never learned
switchover probe 192.168.100.1 ok, vty no answer
auto test RMON OID 1.3.6.1.2.1 fail, pcap keepalive seen
ticket AUTO-307 manual af/ba layer reset needed

rechekc with L1 and customer
"""

PROMPT = f"""
You are an industrial incident reconstruction system.

TASK:
Generate structured incident analysis.

RULES:
- preserve chronology
- preserve telemetry
- preserve identifiers
- preserve causal relationships
- do NOT hallucinate

WORKLOG:
{WORKLOG}
"""


# =========================================================
# GENERATION (FAST + STABLE SETTINGS)
# =========================================================

start_time = time.time()

result = model(
    PROMPT,
    IncidentSummary,
    max_new_tokens=384,
    # temperature=0.1
)

elapsed_time = time.time() - start_time
print(f"\nGeneration completed in {elapsed_time:.2f} seconds.")

# =========================================================
# OUTPUT
# =========================================================

print("\n" + "=" * 80)
print("STRUCTURED OUTPUT")
print("=" * 80)
print(f" LLM Response [{type(result).__name__}]: {result}")

# =========================================================
# SAVE RESULTS
# =========================================================

output_path = "outputs/summary_2.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
result_dict = json.loads(result)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result_dict, f, indent=2, ensure_ascii=False)

print(f"Saved structured output to {output_path}")
