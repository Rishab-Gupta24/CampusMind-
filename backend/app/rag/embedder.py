"""Text → 1024-dim vectors with bge-m3 through Ollama /api/embed, 32 texts per call."""

import httpx

from app.config import get_settings

BATCH_SIZE = 32


class EmbedError(Exception):
    """Embedding failed. The message is safe to show users."""


def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    vectors: list[list[float]] = []
    with httpx.Client(base_url=settings.ollama_url, timeout=300) as client:
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            try:
                res = client.post(
                    "/api/embed",
                    json={"model": settings.embed_model, "input": batch, "keep_alive": settings.ollama_keep_alive},
                )
                res.raise_for_status()
            except httpx.HTTPError as exc:
                raise EmbedError("The embedding model is not reachable. Check that Ollama is running.") from exc
            batch_vectors = res.json()["embeddings"]
            if len(batch_vectors) != len(batch) or any(len(v) != settings.embed_dim for v in batch_vectors):
                raise EmbedError("The embedding model returned unexpected vectors. Check EMBED_MODEL and EMBED_DIM.")
            vectors.extend(batch_vectors)
    return vectors


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
