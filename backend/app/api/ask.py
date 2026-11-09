import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.rag.answerer import answer

router = APIRouter()
log = logging.getLogger(__name__)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    scope: Literal["all", "docs", "lectures"] = "all"
    course_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    lecture_id: uuid.UUID | None = None


def _str(value: uuid.UUID | None) -> str | None:
    return str(value) if value else None


@router.post("/api/ask")
async def ask(req: AskRequest) -> EventSourceResponse:
    async def events() -> AsyncIterator[dict[str, str]]:
        try:
            async for event in answer(
                req.question,
                scope=req.scope,
                course_id=_str(req.course_id),
                section_id=_str(req.section_id),
                lecture_id=_str(req.lecture_id),
            ):
                yield {"event": event["event"], "data": json.dumps(event["data"], ensure_ascii=False)}
        except Exception:
            log.exception("Ask failed")
            yield {"event": "error", "data": json.dumps({"error": "Something went wrong. Please try again."})}

    return EventSourceResponse(events())
