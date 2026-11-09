"""The only place that talks to Supabase. Uses the service-role key (server side only)."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from supabase import Client, create_client

from app.config import get_settings

UPSERT_BATCH = 100
SIGNED_URL_SECONDS = 3600

Row = dict[str, Any]


class NotConfiguredError(RuntimeError):
    """Raised when backend/.env is missing Supabase settings. Its message is safe to show users."""


@lru_cache
def get_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise NotConfiguredError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env."
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


# ---------- chunks ----------


def count_chunks() -> int:
    result = get_client().table("chunks").select("id", count="exact").limit(1).execute()
    return result.count or 0


def upsert_chunks(rows: list[Row]) -> None:
    table = get_client().table("chunks")
    for start in range(0, len(rows), UPSERT_BATCH):
        table.upsert(rows[start : start + UPSERT_BATCH]).execute()


def delete_chunks(source_id: str) -> None:
    get_client().table("chunks").delete().eq("source_id", source_id).execute()


# ---------- sources ----------


def insert_source(row: Row) -> Row:
    return get_client().table("sources").insert(row).execute().data[0]


def update_source(source_id: str, fields: Row) -> None:
    get_client().table("sources").update(fields).eq("id", source_id).execute()


def get_source(source_id: str) -> Row | None:
    rows = (
        get_client()
        .table("sources")
        .select("*, instructors(name, role), sections(name)")
        .eq("id", source_id)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def find_document(title: str, kind: str, course_id: str | None) -> Row | None:
    """An existing PDF with the same title, kind and course — re-uploading replaces it."""
    query = get_client().table("sources").select("*").eq("type", "pdf").eq("title", title).eq("kind", kind)
    query = query.eq("course_id", course_id) if course_id else query.is_("course_id", "null")
    rows = query.limit(1).execute().data
    return rows[0] if rows else None


def list_sources(source_type: str, course_id: str | None = None) -> list[Row]:
    query = (
        get_client()
        .table("sources")
        .select("*, instructors(name, role), sections(name)")
        .eq("type", source_type)
        .order("created_at", desc=True)
    )
    if course_id:
        query = query.eq("course_id", course_id)
    return query.execute().data


def delete_source(source_id: str) -> None:
    get_client().table("sources").delete().eq("id", source_id).execute()


# ---------- answers, feedback, unanswered ----------


def insert_answer(question: str, answer: str, source_chunk_ids: list[str], scope: str) -> str:
    row = {"question": question, "answer": answer, "source_chunk_ids": source_chunk_ids, "scope": scope}
    return get_client().table("answers").insert(row).execute().data[0]["id"]


def answer_exists(answer_id: str) -> bool:
    return bool(get_client().table("answers").select("id").eq("id", answer_id).limit(1).execute().data)


def insert_feedback(answer_id: str, rating: int) -> None:
    get_client().table("feedback").insert({"answer_id": answer_id, "rating": rating}).execute()


def insert_unanswered(question: str, scope: str, best_score: float | None) -> None:
    row = {"question": question, "scope": scope, "best_score": best_score}
    get_client().table("unanswered").insert(row).execute()


# ---------- lecture notes ----------


def get_lecture_notes(source_id: str) -> Row | None:
    rows = get_client().table("lecture_notes").select("*").eq("source_id", source_id).limit(1).execute().data
    return rows[0] if rows else None


def upsert_lecture_notes(row: Row) -> None:
    get_client().table("lecture_notes").upsert(row).execute()


# ---------- storage ----------


def _bucket():
    return get_client().storage.from_(get_settings().supabase_bucket)


def upload_file(storage_path: str, local_path: Path, content_type: str) -> None:
    with local_path.open("rb") as handle:
        _bucket().upload(storage_path, handle.read(), {"content-type": content_type, "upsert": "true"})


def upload_json(storage_path: str, data: object) -> None:
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    _bucket().upload(storage_path, payload, {"content-type": "application/json", "upsert": "true"})


def download_file(storage_path: str, local_path: Path) -> None:
    local_path.write_bytes(_bucket().download(storage_path))


def download_json(storage_path: str) -> Any:
    return json.loads(_bucket().download(storage_path))


def remove_files(paths: list[str]) -> None:
    if paths:
        _bucket().remove(paths)


def signed_url(storage_path: str) -> str | None:
    result = _bucket().create_signed_url(storage_path, SIGNED_URL_SECONDS)
    return result.get("signedURL") or result.get("signedUrl")


# ---------- flagged moments, insights ----------


def lecture_notes_for(source_ids: list[str]) -> dict[str, list[Row]]:
    if not source_ids:
        return {}
    rows = (
        get_client().table("lecture_notes").select("source_id, flagged_moments").in_("source_id", source_ids).execute()
    ).data
    return {r["source_id"]: r["flagged_moments"] or [] for r in rows}


def list_unanswered(limit: int = 500) -> list[Row]:
    return (
        get_client()
        .table("unanswered")
        .select("question, scope, best_score, created_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def list_thumbs_down(limit: int = 200) -> list[Row]:
    rows = (
        get_client()
        .table("feedback")
        .select("created_at, answers(id, question, answer)")
        .eq("rating", -1)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )
    return [
        {
            "answer_id": r["answers"]["id"],
            "question": r["answers"]["question"],
            "answer": r["answers"]["answer"],
            "created_at": r["created_at"],
        }
        for r in rows
        if r.get("answers")
    ]


# ---------- catalog helpers ----------


@lru_cache
def course_codes() -> dict[str, str]:
    """{course_id: "MATH F113"} — cached; the catalog changes only through seed/migrations."""
    rows = get_client().table("courses").select("id, code").execute().data
    return {r["id"]: r["code"] for r in rows}
