"""
llm_evaluation.py

Hybrid LLM evaluation framework for:
- semantic coverage
- hallucination detection
- consistency scoring
- fluency evaluation
- schema validation

Architecture:
- Embedding-based semantic evaluation
- LLM-as-a-judge evaluation
- Deterministic validation
- Multi-run consistency analysis

"""


import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, ValidationError
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline


# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "evaluation_results.csv"


# =============================================================================
# Evaluation Result
# =============================================================================

@dataclass
class EvaluationResult:
    """Container for evaluation results."""

    timestamp: str
    sample_id: str

    coverage_score: float
    hallucination_score: float
    consistency_score: float
    fluency_score: float
    faithfulness_score: float

    schema_valid: bool
    schema_error: Optional[str]

    overall_score: float

    metadata: str


# =============================================================================
# Schema Validator
# =============================================================================

class ExtractionSchema(BaseModel):
    """Example extraction schema."""

    summary: str
    entities: List[str]
    key_points: List[str]


class SchemaValidator:
    """Validates extraction schema."""

    def __init__(self, schema_model: BaseModel):
        """
        Initialize schema validator.

        Args:
            schema_model: Pydantic schema model.
        """
        self.schema_model = schema_model

    def validate(
        self,
        extraction: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """
        Validate extraction against schema.

        Args:
            extraction: Extracted JSON object.

        Returns:
            Tuple of validation status and error message.
        """
        try:
            self.schema_model(**extraction)
            return True, None

        except ValidationError as exc:
            return False, str(exc)


# =============================================================================
# Embedding Evaluator
# =============================================================================

class EmbeddingEvaluator:
    """
    Semantic evaluation using embeddings.
    """

    def __init__(
        self,
        embedding_model_name: str = "model/bge-large-en-v1.5",
    ):
        """
        Initialize embedding evaluator.

        Args:
            embedding_model_name: Hugging Face embedding model.
        """
        LOGGER.info("Loading embedding model: %s", embedding_model_name)

        self.model = SentenceTransformer(
            embedding_model_name,
            trust_remote_code=True,
        )

    def compute_similarity(
        self,
        source_text: str,
        extracted_text: str,
    ) -> float:
        """
        Compute semantic similarity.

        Args:
            source_text: Original source text.
            extracted_text: Extracted/generated text.

        Returns:
            Cosine similarity score.
        """
        embeddings = self.model.encode(
            [source_text, extracted_text],
            normalize_embeddings=True,
        )

        similarity = cosine_similarity(
            [embeddings[0]],
            [embeddings[1]],
        )[0][0]

        return float(similarity)

    def compute_coverage(
        self,
        source_chunks: List[str],
        extracted_chunks: List[str],
    ) -> float:
        """
        Compute semantic coverage.

        Measures how much of the source content
        is represented in the extraction.

        Args:
            source_chunks: Source text chunks.
            extracted_chunks: Extracted text chunks.

        Returns:
            Coverage score.
        """
        source_embeddings = self.model.encode(
            source_chunks,
            normalize_embeddings=True,
        )

        extracted_embeddings = self.model.encode(
            extracted_chunks,
            normalize_embeddings=True,
        )

        similarity_matrix = cosine_similarity(
            source_embeddings,
            extracted_embeddings,
        )

        max_similarities = similarity_matrix.max(axis=1)

        return float(np.mean(max_similarities))


# =============================================================================
# LLM Judge Evaluator
# =============================================================================

class LLMJudgeEvaluator:
    """
    LLM-as-a-judge evaluator.
    """

    def __init__(
        self,
        model_name: str = "model/Qwen2.5-72B-Instruct",
        device: str = "auto",
    ):
        """
        Initialize LLM judge evaluator.

        Args:
            model_name: Hugging Face judge model.
            device: Device configuration.
        """
        LOGGER.info("Loading judge model: %s", model_name)

        self.pipe = pipeline(
            "text-generation",
            model=model_name,
            device_map=device,
            trust_remote_code=True,
        )

    def _generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
    ) -> str:
        """
        Generate LLM response.

        Args:
            prompt: Input prompt.
            max_new_tokens: Max generation length.

        Returns:
            Generated text.
        """
        outputs = self.pipe(
            prompt,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.0,
            return_full_text=False,
        )

        return outputs[0]["generated_text"]

    def evaluate_hallucination(
        self,
        source_text: str,
        extracted_text: str,
    ) -> float:
        """
        Evaluate hallucination level.

        Args:
            source_text: Original source text.
            extracted_text: Generated extraction.

        Returns:
            Hallucination score [0-1].
        """
        prompt = f"""
You are an expert evaluator.

TASK:
Determine how much hallucinated information exists
in the extracted text compared to the source text.

RULES:
- Only use the source text.
- Penalize unsupported claims.
- Return ONLY valid JSON.

SOURCE:
{source_text}

EXTRACTION:
{extracted_text}

OUTPUT FORMAT:
{{
    "hallucination_score": float
}}
"""

        response = self._generate(prompt)

        try:
            parsed = json.loads(response)
            return float(parsed["hallucination_score"])

        except Exception as exc:
            LOGGER.warning(
                "Failed hallucination parsing: %s",
                exc,
            )
            return 1.0

    def evaluate_fluency(
        self,
        extracted_text: str,
    ) -> float:
        """
        Evaluate fluency/readability.

        Args:
            extracted_text: Generated extraction.

        Returns:
            Fluency score [0-1].
        """
        prompt = f"""
Evaluate fluency and readability.

Return ONLY JSON.

TEXT:
{extracted_text}

OUTPUT:
{{
    "fluency_score": float
}}
"""

        response = self._generate(prompt)

        try:
            parsed = json.loads(response)
            return float(parsed["fluency_score"])

        except Exception:
            return 0.0

    def evaluate_faithfulness(
        self,
        source_text: str,
        extracted_text: str,
    ) -> float:
        """
        Evaluate faithfulness to source.

        Args:
            source_text: Original source.
            extracted_text: Extraction.

        Returns:
            Faithfulness score [0-1].
        """
        prompt = f"""
Evaluate how faithful the extraction is to the source.

Return ONLY JSON.

SOURCE:
{source_text}

EXTRACTION:
{extracted_text}

OUTPUT:
{{
    "faithfulness_score": float
}}
"""

        response = self._generate(prompt)

        try:
            parsed = json.loads(response)
            return float(parsed["faithfulness_score"])

        except Exception:
            return 0.0


# =============================================================================
# Consistency Evaluator
# =============================================================================

class ConsistencyEvaluator:
    """
    Multi-run consistency evaluator.
    """

    def __init__(
        self,
        embedding_evaluator: EmbeddingEvaluator,
    ):
        """
        Initialize consistency evaluator.

        Args:
            embedding_evaluator: Embedding evaluator instance.
        """
        self.embedding_evaluator = embedding_evaluator

    def evaluate(
        self,
        extraction_runs: List[str],
    ) -> float:
        """
        Evaluate consistency between runs.

        Args:
            extraction_runs: Multiple extraction outputs.

        Returns:
            Consistency score.
        """
        if len(extraction_runs) < 2:
            return 1.0

        scores = []

        for idx in range(len(extraction_runs)):
            for jdx in range(idx + 1, len(extraction_runs)):
                similarity = (
                    self.embedding_evaluator.compute_similarity(
                        extraction_runs[idx],
                        extraction_runs[jdx],
                    )
                )

                scores.append(similarity)

        return float(np.mean(scores))


# =============================================================================
# CSV Writer
# =============================================================================

class EvaluationWriter:
    """
    Handles saving evaluation results.
    """

    def __init__(
        self,
        output_path: Path = OUTPUT_CSV,
    ):
        """
        Initialize writer.

        Args:
            output_path: CSV output file.
        """
        self.output_path = output_path

    def save(
        self,
        result: EvaluationResult,
    ) -> None:
        """
        Append result to CSV.

        Args:
            result: Evaluation result object.
        """
        result_df = pd.DataFrame([asdict(result)])

        if self.output_path.exists():
            existing_df = pd.read_csv(self.output_path)

            combined_df = pd.concat(
                [existing_df, result_df],
                ignore_index=True,
            )

            combined_df.to_csv(
                self.output_path,
                index=False,
            )

        else:
            result_df.to_csv(
                self.output_path,
                index=False,
            )

        LOGGER.info(
            "Saved evaluation result to: %s",
            self.output_path,
        )


# =============================================================================
# Main Evaluator
# =============================================================================

class HybridLLMEvaluator:
    """
    Complete hybrid evaluation framework.
    """

    def __init__(
        self,
        embedding_model_name: str = "model/bge-large-en-v1.5",
        judge_model_name: str = "model/Qwen2.5-1.5B-Instruct",
    ):
        """
        Initialize evaluator stack.

        Args:
            embedding_model_name: Embedding model.
            judge_model_name: Judge LLM.
        """
        self.embedding_evaluator = EmbeddingEvaluator(
            embedding_model_name=embedding_model_name,
        )

        self.judge_evaluator = LLMJudgeEvaluator(
            model_name=judge_model_name,
        )

        self.consistency_evaluator = ConsistencyEvaluator(
            embedding_evaluator=self.embedding_evaluator,
        )

        self.schema_validator = SchemaValidator(
            schema_model=ExtractionSchema,
        )

        self.writer = EvaluationWriter()

    def evaluate(
        self,
        sample_id: str,
        source_text: str,
        extraction: Dict[str, Any],
        extraction_runs: Optional[List[str]] = None,
    ) -> EvaluationResult:
        """
        Run complete evaluation pipeline.

        Args:
            sample_id: Unique sample identifier.
            source_text: Source document text.
            extraction: Extracted structured output.
            extraction_runs: Multiple extraction runs.

        Returns:
            EvaluationResult object.
        """
        extracted_text = json.dumps(
            extraction,
            indent=2,
        )

        # ---------------------------------------------------------------------
        # Schema Validation
        # ---------------------------------------------------------------------

        schema_valid, schema_error = (
            self.schema_validator.validate(extraction)
        )

        # ---------------------------------------------------------------------
        # Semantic Coverage
        # ---------------------------------------------------------------------

        coverage_score = (
            self.embedding_evaluator.compute_coverage(
                source_chunks=[source_text],
                extracted_chunks=[extracted_text],
            )
        )

        # ---------------------------------------------------------------------
        # Hallucination
        # ---------------------------------------------------------------------

        hallucination_score = (
            self.judge_evaluator.evaluate_hallucination(
                source_text=source_text,
                extracted_text=extracted_text,
            )
        )

        # ---------------------------------------------------------------------
        # Fluency
        # ---------------------------------------------------------------------

        fluency_score = (
            self.judge_evaluator.evaluate_fluency(
                extracted_text=extracted_text,
            )
        )

        # ---------------------------------------------------------------------
        # Faithfulness
        # ---------------------------------------------------------------------

        faithfulness_score = (
            self.judge_evaluator.evaluate_faithfulness(
                source_text=source_text,
                extracted_text=extracted_text,
            )
        )

        # ---------------------------------------------------------------------
        # Consistency
        # ---------------------------------------------------------------------

        consistency_score = 1.0

        if extraction_runs:
            consistency_score = (
                self.consistency_evaluator.evaluate(
                    extraction_runs,
                )
            )

        # ---------------------------------------------------------------------
        # Overall Score
        # ---------------------------------------------------------------------

        overall_score = float(
            np.mean(
                [
                    coverage_score,
                    consistency_score,
                    fluency_score,
                    faithfulness_score,
                    1.0 - hallucination_score,
                ]
            )
        )

        result = EvaluationResult(
            timestamp=datetime.utcnow().isoformat(),
            sample_id=sample_id,

            coverage_score=coverage_score,
            hallucination_score=hallucination_score,
            consistency_score=consistency_score,
            fluency_score=fluency_score,
            faithfulness_score=faithfulness_score,

            schema_valid=schema_valid,
            schema_error=schema_error,

            overall_score=overall_score,

            metadata=json.dumps(
                {
                    "embedding_model": (
                        "bge-large-en-v1.5"
                    ),
                    "judge_model": (
                        "Qwen2.5-72B-Instruct"
                    ),
                }
            ),
        )

        self.writer.save(result)

        return result


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    MODEL_NAME = "../model/Qwen2.5-1.5B-Instruct"
    EMB_MODEL_NAME = "../model/bge-large-en-v1.5"
    # define the absolute path of the LLM model
    MODEL_PATH = os.path.abspath(MODEL_NAME)
    EMB_MODEL_PATH = os.path.abspath(EMB_MODEL_NAME)


    SOURCE_TEXT = """
    Apple released a new AI-enabled MacBook Pro
    featuring improved battery life and a faster M4 chip.
    """

    EXTRACTION = {
        "summary": (
            "Apple released a new MacBook Pro "
            "with an M4 chip and better battery life."
        ),
        "entities": [
            "Apple",
            "MacBook Pro",
            "M4 chip",
        ],
        "key_points": [
            "AI-enabled laptop",
            "Improved battery",
            "Faster processor",
        ],
    }

    EXTRACTION_RUNS = [
        json.dumps(EXTRACTION),
        json.dumps(EXTRACTION),
    ]

    evaluator = HybridLLMEvaluator(embedding_model_name = EMB_MODEL_PATH,
        judge_model_name = MODEL_PATH,)

    result = evaluator.evaluate(
        sample_id="sample_001",
        source_text=SOURCE_TEXT,
        extraction=EXTRACTION,
        extraction_runs=EXTRACTION_RUNS,
    )

    print("\nEvaluation Result:")
    print(json.dumps(asdict(result), indent=2))