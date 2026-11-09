import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db

router = APIRouter()


class FeedbackRequest(BaseModel):
    answer_id: uuid.UUID
    rating: Literal[1, -1]


@router.post("/api/feedback")
def feedback(req: FeedbackRequest) -> dict[str, bool]:
    answer_id = str(req.answer_id)
    if not db.answer_exists(answer_id):
        raise HTTPException(status_code=404, detail="That answer no longer exists.")
    db.insert_feedback(answer_id, req.rating)
    return {"ok": True}
