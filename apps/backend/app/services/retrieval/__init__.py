"""AstraTrace Retrieval Package.

SIH 2026 | Problem ID: SIH26227
Contains baseline search, vocabulary parsing, feature classification, and ranking modules.
"""
from apps.backend.app.services.retrieval.vocabulary import ControlledVocabulary
from apps.backend.app.services.retrieval.baseline_classifier import TileFeatureClassifier
from apps.backend.app.services.retrieval.baseline_scorer import BaselineScorer
from apps.backend.app.services.retrieval.service import BaselineRetrievalService
from apps.backend.app.services.retrieval.embedding_model import (
    EmbeddingModel,
    RemoteCLIPEmbeddingModel,
    DeterministicOfflineEmbeddingModel,
    get_embedding_model,
)
from apps.backend.app.services.retrieval.vector_index import VectorIndex, NumpyVectorIndex
from apps.backend.app.services.retrieval.semantic_service import SemanticRetrievalService
from apps.backend.app.services.retrieval.evaluator import RetrievalEvaluator

__all__ = [
    "ControlledVocabulary",
    "TileFeatureClassifier",
    "BaselineScorer",
    "BaselineRetrievalService",
    "EmbeddingModel",
    "RemoteCLIPEmbeddingModel",
    "DeterministicOfflineEmbeddingModel",
    "get_embedding_model",
    "VectorIndex",
    "NumpyVectorIndex",
    "SemanticRetrievalService",
    "RetrievalEvaluator",
]
