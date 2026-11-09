import httpx
from fastapi import APIRouter

from app import db
from app.config import get_settings

router = APIRouter()


def _ollama_ok(base_url: str) -> bool:
    try:
        return httpx.get(f"{base_url}/api/tags", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


@router.get("/api/health")
def health() -> dict[str, object]:
    settings = get_settings()
    supabase_ok = True
    chunks = 0
    try:
        chunks = db.count_chunks()
    except Exception:  # noqa: BLE001 — health must never crash; report Supabase as down instead
        supabase_ok = False
    return {
        "ollama": _ollama_ok(settings.ollama_url),
        "supabase": supabase_ok,
        "llm_model": settings.llm_model,
        "chunks": chunks,
    }
