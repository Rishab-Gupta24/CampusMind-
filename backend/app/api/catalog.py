from fastapi import APIRouter

from app import db

router = APIRouter()


@router.get("/api/courses")
def list_courses() -> list[dict[str, object]]:
    rows = (
        db.get_client()
        .table("courses")
        .select("id, code, title, sections(id, name, instructors(name, role))")
        .order("code")
        .execute()
        .data
    )
    return [
        {
            "id": course["id"],
            "code": course["code"],
            "title": course["title"],
            "sections": [
                {"id": s["id"], "name": s["name"], "instructor": s.get("instructors")}
                for s in sorted(course.get("sections") or [], key=lambda s: s["name"])
            ],
        }
        for course in rows
    ]
