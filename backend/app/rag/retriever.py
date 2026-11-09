"""Hybrid search (pgvector + full-text, RRF) in one RPC, then chunk rows with source details."""

from typing import Literal, TypedDict

from app import db

Scope = Literal["all", "docs", "lectures"]
SCOPE_TO_TYPE: dict[str, str | None] = {"all": None, "docs": "pdf", "lectures": "lecture"}


class Instructor(TypedDict):
    name: str
    role: str


class Passage(TypedDict, total=False):
    chunk_id: str
    content: str
    page: int | None
    start_s: float | None
    end_s: float | None
    flagged: bool
    flag_reason: str | None
    source_id: str
    title: str
    type: str
    kind: str
    course_id: str | None
    section_id: str | None
    instructor: Instructor | None
    course_code: str | None
    rrf_score: float
    rerank_score: float
    final_score: float
    badges: list[str]


def retrieve(
    question: str,
    query_embedding: list[float],
    scope: Scope = "all",
    course_id: str | None = None,
    lecture_id: str | None = None,
    k: int = 20,
) -> list[Passage]:
    client = db.get_client()
    hits = (
        client.rpc(
            "hybrid_search",
            {
                "query_text": question,
                "query_embedding": query_embedding,
                "match_count": k,
                "filter_type": "lecture" if lecture_id else SCOPE_TO_TYPE[scope],
                "filter_course": course_id,
                "filter_source": lecture_id,
            },
        )
        .execute()
        .data
    )
    if not hits:
        return []

    rrf = {hit["chunk_id"]: hit["rrf_score"] for hit in hits}
    rows = (
        client.table("chunks")
        .select(
            "id, content, page, start_s, end_s, flagged, flag_reason, source_id, "
            "sources(title, type, kind, course_id, section_id, instructors(name, role), courses(code))"
        )
        .in_("id", list(rrf))
        .execute()
        .data
    )

    passages: list[Passage] = []
    for row in rows:
        source = row["sources"] or {}
        passages.append(
            {
                "chunk_id": row["id"],
                "content": row["content"],
                "page": row["page"],
                "start_s": row["start_s"],
                "end_s": row["end_s"],
                "flagged": row["flagged"],
                "flag_reason": row["flag_reason"],
                "source_id": row["source_id"],
                "title": source.get("title", ""),
                "type": source.get("type", ""),
                "kind": source.get("kind", ""),
                "course_id": source.get("course_id"),
                "section_id": source.get("section_id"),
                "instructor": source.get("instructors"),
                "course_code": (source.get("courses") or {}).get("code"),
                "rrf_score": rrf[row["id"]],
            }
        )
    passages.sort(key=lambda p: p["rrf_score"], reverse=True)
    return passages
