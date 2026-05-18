from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("evaluator")


# =========================================================
# RESULT
# =========================================================


@dataclass
class EvaluationResult:
    coverage: float
    faithfulness: float
    coherence: float
    hallucination: float
    consistency: float
    overall: float


# =========================================================
# EMBEDDING EVAL
# =========================================================


class EmbeddingEvaluator:
    def __init__(self, model_path: str):
        logger.info(f"Loading embeddings: {model_path}")
        self.model = SentenceTransformer(model_path)

    def similarity(self, a: str, b: str) -> float:
        emb = self.model.encode([a, b], normalize_embeddings=True)
        return float(cosine_similarity([emb[0]], [emb[1]])[0][0])

    def coverage(self, source: str, extracted: str) -> float:
        return self.similarity(source, extracted)


# =========================================================
# CONSISTENCY
# =========================================================


class ConsistencyEvaluator:
    def __init__(self, embed: EmbeddingEvaluator):
        self.embed = embed

    def score(self, runs: List[str]) -> float:
        if len(runs) < 2:
            return 1.0

        scores = []
        for i in range(len(runs)):
            for j in range(i + 1, len(runs)):
                scores.append(self.embed.similarity(runs[i], runs[j]))

        return float(np.mean(scores))


# =========================================================
# LLM JUDGE WRAPPER (INSTRUCTOR PROVIDED)
# =========================================================


class LLMJudge:
    def __init__(self, client):
        self.client = client

    def evaluate(self, prompt: str, schema):
        return self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=schema,
        )


# =========================================================
# MAIN EVALUATOR
# =========================================================


class HybridEvaluator:
    def __init__(self, embed_model: str, judge_client):
        self.embed = EmbeddingEvaluator(embed_model)
        self.consistency = ConsistencyEvaluator(self.embed)
        self.judge_client = judge_client

    def evaluate(
        self,
        source: str,
        extracted: Dict[str, Any],
        judge_prompt: str,
        judge_schema,
        runs: Optional[List[str]] = None,
    ) -> EvaluationResult:

        extracted_text = json.dumps(extracted, indent=2)

        # coverage
        coverage = self.embed.coverage(source, extracted_text)

        # LLM judge
        prompt = judge_prompt.format(
            input_text=source,
            output=extracted_text,
        )

        judge = self.judge_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            response_model=judge_schema,
        )

        # consistency
        consistency = self.consistency.score(runs or [extracted_text])

        # overall
        overall = float(
            np.mean(
                [
                    coverage,
                    judge.faithfulness,
                    judge.coverage,
                    judge.coherence,
                    consistency,
                    1.0 - float(judge.hallucination_detected),
                ]
            )
        )

        return EvaluationResult(
            coverage=coverage,
            faithfulness=judge.faithfulness,
            coherence=judge.coherence,
            hallucination=float(judge.hallucination_detected),
            consistency=consistency,
            overall=overall,
        )
