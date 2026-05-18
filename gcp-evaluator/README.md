# GCP LLM Evaluation System

## Architecture
- CPU Cloud Run: Scheduler + batching
- GPU Cloud Run: LLM evaluation engine
- BigQuery: storage (requests + results)

## Flow
1. Insert evaluation requests into BigQuery
2. CPU scheduler batches requests
3. GPU service evaluates batch
4. Results stored in eval_results


## Setup & Configuration

### Download HF LLM models
1. **Small model for CPU**
```
$ hf download BAAI/bge-large-en-v1.5 --local-dir model/bge-large-en-v1.5

$ hf download Qwen/Qwen2.5-1.5B-Instruct --local-dir model/Qwen2.5-1.5B-Instruct

$ hf download microsoft/Phi-3-mini-4k-instruct --local-dir ../model/Phi-3-mini-4k-instruct
```

2. **Large model for GPU H100**
```
$ hf download BAAI/bge-large-en-v1.5 --local-dir model/bge-large-en-v1.5

$ hf download Qwen/Qwen2.5-72B-Instruct --local-dir model/Qwen2.5-72B-Instruct
```