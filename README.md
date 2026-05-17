
# Robust Temporal Event Reconstruction from Noisy Industrial Logs using Small Language Models under Compute Constraints

## Overview

This repository implements a lightweight pipeline that converts noisy, unstructured IT dispatch worklogs into temporally consistent, structured incident records. The design targets CPU-only environments (e.g., 4‑core machines) and small instruction‑tuned LLMs to enable practical on‑prem and edge deployments.



> Note: This project is based mainly on the following LLM model: **Qwen2.5** ( https://qwen.ai/blog?id=qwen2.5 )

## Research plan

Please refer to the [RESEARCH_PLAN.md](documents/RESEARCH_PLAN.md) for more details


## Problem Statement

IT and network operations teams generate large volumes of unstructured worklogs containing:

- Incident descriptions
- Timestamps scattered across notes
- Device and circuit identifiers
- Technician actions
- Customer and site information
- Escalation and resolution notes

These logs are difficult to:
- search
- aggregate
- analyze
- automate

Manual structuring is slow and error-prone.



## Solution

This system uses a small instruction-tuned language model to extract structured JSON from raw worklogs.

### Output Schema

Each worklog is converted into:

```json
{
  "incident_summary": "",
  "event_timeline": [
    {
      "timestamp": "",
      "event": "",
      "source": ""
    }
  ],
  "entities": {
    "devices": [],
    "circuits": [],
    "technicians": [],
    "ips": []
  },
  "next_actions": [],
  "conflicts_detected": [],
  "final_resolution": ""
}
````






## Key Features

* Extracts structured incident data from noisy logs
* Identifies devices, circuits, and infrastructure references
* Captures resolution steps and escalation paths
* Extracts technician and contact information when available
* Runs efficiently on CPU-only systems
* Produces strict JSON output for downstream systems



## Justification for Using `Qwen2.5-1.5B-Instruct` model

This model was selected based on performance, efficiency, and reliability under constrained hardware conditions.

### 1. Strong Structured Output Performance

Worklog extraction requires strict JSON formatting and consistent field generation.

Qwen2.5-1.5B-Instruct demonstrates:

* High adherence to structured output prompts
* Low rate of malformed JSON
* Stable multi-field extraction behavior

This is critical for production pipelines where downstream systems depend on valid schemas.



### 2. Optimized for Low-Resource Environments

The model is well-suited for CPU inference:

* Runs efficiently on 4-core CPUs
* Compatible with GGUF quantization (Q4_K_M recommended)
* Low memory footprint compared to 7B+ models
* Usable without GPU acceleration

This makes it practical for edge or on-prem deployments.



### 3. Superior Extraction vs Other Small Models

Compared to alternatives:

* Performs better than Phi-3-mini in multi-field extraction consistency
* More reliable than Gemma-2B for strict JSON adherence
* More robust than Llama 3.2 1B in noisy, real-world logs



### 4. Strong Handling of Noisy Operational Text

Worklogs contain:

* inconsistent formatting
* abbreviations
* mixed timestamps
* device identifiers
* escalation notes

Qwen2.5-1.5B-Instruct handles this variability well without requiring heavy prompt engineering.



### 5. Fine-Tuning Friendly

If future improvements are needed, the model supports:

* LoRA / QLoRA fine-tuning
* Hugging Face ecosystem tooling
* Instruction dataset adaptation

This allows incremental improvement without changing architecture.



## System Architecture

```
Raw Worklog
    ↓
Prompt Template (structured extraction instruction)
    ↓
Qwen2.5-1.5B-Instruct
    ↓
JSON Output
    ↓
Validation Layer (schema check)
    ↓
Storage / Analytics / API
```



## Dependencies

### Core Libraries

* transformers
* torch (CPU version)
* accelerate
* sentencepiece
* safetensors

### Optional (Recommended for production)

* llama.cpp (for GGUF inference)
* pydantic (for JSON validation)
* fastapi (for API deployment)



## Inference Options

### Option 1: llama.cpp (recommended)

Fast CPU inference using quantized GGUF models.

### Option 2: Ollama (simplest deployment)

Minimal setup for local inference.


## Future Improvements

* Fine-tuning on domain-specific incident logs
* Adding severity classification
* Adding automatic incident summarization scoring
* Integrating with ticketing systems (ServiceNow, Jira)
* Streaming log ingestion pipeline


## Summary

This project demonstrates how a small instruction-tuned model can effectively convert noisy operational worklogs into structured, machine-readable incident data on CPU-only hardware.

`Qwen2.5-1.5B-Instruct` was selected because it provides the best balance between:

* extraction accuracy
* structured output reliability
* CPU efficiency
* deployment simplicity
