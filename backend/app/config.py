"""All settings come from backend/.env. Nothing is hard-coded elsewhere."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket: str = "sources"

    # Models
    llm_provider: str = "ollama"
    llm_model: str = "gemma4:e4b"
    ollama_url: str = "http://127.0.0.1:11434"  # not localhost: on Windows it tries IPv6 first (+2 s per call)
    embed_model: str = "bge-m3"
    # How long Ollama keeps a model loaded after its last use. 30m unloaded both models between demo
    # questions and the next answer took ~25 s; the demo laptop has the VRAM to keep them loaded.
    ollama_keep_alive: str = "24h"
    embed_dim: int = 1024
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    whisper_model: str = "small"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"

    # Retrieval
    top_k_retrieve: int = 40  # tuned in 2.9: GPU rerank of 40 ≈ 0.6 s
    top_k_final: int = 5
    min_relevance: float = 0.02  # tuned on eval: off-topic ≤ 0.004, hard-but-relevant ≥ 0.04 (memory.md)
    boost_official: float = 0.04
    boost_senior: float = 0.04
    boost_flagged: float = 0.05
    boost_section: float = 0.03

    # OCR for scanned pages and handwritten notes (vision model via Ollama; empty = LLM_MODEL)
    ocr_enabled: bool = True
    ocr_model: str = ""
    ocr_dpi: int = 150
    ocr_max_pages: int = 80

    # Uploads
    max_upload_mb: int = 200
    pdf_compress_over_mb: int = 20
    max_stored_mb: int = 50  # Supabase free-tier Storage rejects larger objects (HTTP 413)
    audio_bitrate: str = "24k"
    tmp_dir: Path = BACKEND_DIR / "tmp"

    # CORS
    frontend_origin: str = "http://localhost:3000"

    @property
    def allowed_origins(self) -> list[str]:
        """The app's origin under both local names, so opening 127.0.0.1:3000 works too."""
        origins = {self.frontend_origin}
        for a, b in (("//localhost", "//127.0.0.1"), ("//127.0.0.1", "//localhost")):
            if a in self.frontend_origin:
                origins.add(self.frontend_origin.replace(a, b))
        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()
