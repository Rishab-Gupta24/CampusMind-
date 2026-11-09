"""Cross-encoder reranking. Scores are 0–1 (sigmoid); the relevance gate uses these raw scores."""

import logging
import threading

import torch
from sentence_transformers import CrossEncoder

from app.config import get_settings
from app.rag.retriever import Passage

log = logging.getLogger(__name__)

_model: CrossEncoder | None = None
_lock = threading.Lock()


def device() -> str:
    """GPU when a CUDA build of torch sees one (≈20x faster); CPU otherwise."""
    return "cuda" if torch.cuda.is_available() else "cpu"


def load() -> CrossEncoder:
    global _model
    with _lock:
        if _model is None:
            dev = device()
            kwargs = {"torch_dtype": torch.float16} if dev == "cuda" else {}
            _model = CrossEncoder(get_settings().reranker_model, max_length=512, device=dev, model_kwargs=kwargs)
            log.info("Reranker loaded on %s", dev)
        return _model


def is_loaded() -> bool:
    return _model is not None


def rerank_text(p: Passage) -> str:
    """What the reranker reads: title and speaker first, so "what did the IC say" or a course code can match."""
    header = p.get("title") or ""
    instructor = p.get("instructor")
    if instructor:
        role = {"ic": "IC, Instructor-in-Charge", "hod": "HOD, Head of Department"}.get(
            instructor["role"], "Instructor"
        )
        header += f" · {instructor['name']} ({role})"
    return f"{header}\n{p['content']}" if header else p["content"]


def rerank(question: str, passages: list[Passage]) -> list[Passage]:
    """Add `rerank_score` to each passage and sort best first."""
    if not passages:
        return []
    pairs = [(question, rerank_text(p)) for p in passages]
    scores = load().predict(pairs, batch_size=8, show_progress_bar=False)
    for passage, score in zip(passages, scores, strict=True):
        passage["rerank_score"] = float(score)
    return sorted(passages, key=lambda p: p["rerank_score"], reverse=True)
