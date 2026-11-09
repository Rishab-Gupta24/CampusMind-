"""Visible source priority (PRD F5, Architecture §3.3).

Boosts only re-order passages that already passed the relevance gate. Every boost applied
becomes a badge on the source chip — no hidden ranking.
"""

from app.config import Settings, get_settings
from app.rag.retriever import Passage

# Display order on the chip: Flagged, IC/HOD, Official, Your section.
BADGE_ORDER = ["Flagged", "IC", "HOD", "Official", "Your section"]


def best_raw_score(passages: list[Passage]) -> float:
    """The relevance gate's input: the best reranker score, before any boost."""
    return max((p["rerank_score"] for p in passages), default=0.0)


def apply_boosts(
    passages: list[Passage], section_id: str | None = None, settings: Settings | None = None
) -> list[Passage]:
    """Set `final_score` and `badges` on each passage and sort by final score."""
    s = settings or get_settings()
    for p in passages:
        score = p["rerank_score"]
        badges: list[str] = []
        if p.get("flagged"):
            score += s.boost_flagged
            badges.append("Flagged")
        role = (p.get("instructor") or {}).get("role")
        if role in ("ic", "hod"):
            score += s.boost_senior
            badges.append(role.upper())
        if p.get("kind") in ("campus", "handout"):
            score += s.boost_official
            badges.append("Official")
        if section_id and p.get("section_id") == section_id:
            score += s.boost_section
            badges.append("Your section")
        p["final_score"] = score
        p["badges"] = sorted(badges, key=BADGE_ORDER.index)
    return sorted(passages, key=lambda p: p["final_score"], reverse=True)
