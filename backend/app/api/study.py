import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.llm.base import LLMError
from app.rag.embedder import EmbedError
from app.rag.study import StudyError, generate_flashcards, generate_quiz

router = APIRouter()


class QuizRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    count: int = Field(default=5, ge=5, le=10)
    sources: Literal["all", "past_papers", "notes"] = "all"
    course_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    lecture_id: uuid.UUID | None = None
    exclude: list[str] = Field(default_factory=list, max_length=40)


class FlashcardRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    count: int = Field(default=10, ge=4, le=20)
    course_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    lecture_id: uuid.UUID | None = None


def _s(value: uuid.UUID | None) -> str | None:
    return str(value) if value else None


@router.post("/api/quiz")
async def quiz(req: QuizRequest) -> dict[str, object]:
    try:
        return await generate_quiz(
            req.topic.strip(),
            course_id=_s(req.course_id),
            section_id=_s(req.section_id),
            count=req.count,
            source_filter=req.sources,
            lecture_id=_s(req.lecture_id),
            exclude=req.exclude,
        )
    except StudyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (LLMError, EmbedError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/api/flashcards")
async def flashcards(req: FlashcardRequest) -> dict[str, object]:
    try:
        return await generate_flashcards(
            req.topic.strip(),
            course_id=_s(req.course_id),
            section_id=_s(req.section_id),
            count=req.count,
            lecture_id=_s(req.lecture_id),
        )
    except StudyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (LLMError, EmbedError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
