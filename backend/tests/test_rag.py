from app.config import Settings
from app.rag.answerer import CitationFilter, clean_citations
from app.rag.priority import apply_boosts, best_raw_score
from app.rag.prompts import format_passages, format_time

SETTINGS = Settings(boost_official=0.04, boost_senior=0.04, boost_flagged=0.05, boost_section=0.03)


def _passage(chunk_id: str, score: float, **extra: object) -> dict:
    base = {
        "chunk_id": chunk_id,
        "content": f"text of {chunk_id}",
        "title": chunk_id,
        "kind": "lecture",
        "flagged": False,
        "instructor": None,
        "section_id": None,
        "rerank_score": score,
    }
    base.update(extra)
    return base


# ---------- priority ----------


def test_boosts_reorder_ties_and_match_badges() -> None:
    plain = _passage("plain", 0.60)
    ic = _passage("ic", 0.60, instructor={"name": "Dr. A", "role": "ic"})
    flagged_mine = _passage("flagged", 0.60, flagged=True, section_id="sec-1")
    official = _passage("official", 0.60, kind="campus")
    ranked = apply_boosts([plain, ic, flagged_mine, official], section_id="sec-1", settings=SETTINGS)

    assert ranked[0]["chunk_id"] == "flagged"
    assert ranked[-1]["chunk_id"] == "plain"
    by_id = {p["chunk_id"]: p for p in ranked}
    assert by_id["flagged"]["badges"] == ["Flagged", "Your section"]
    assert by_id["ic"]["badges"] == ["IC"]
    assert by_id["official"]["badges"] == ["Official"]
    assert by_id["plain"]["badges"] == []
    assert abs(by_id["flagged"]["final_score"] - (0.60 + 0.05 + 0.03)) < 1e-9


def test_boost_does_not_beat_a_clearly_better_passage() -> None:
    strong = _passage("strong", 0.90)
    weak_but_everything = _passage(
        "weak", 0.70, flagged=True, kind="campus", instructor={"name": "Dr. B", "role": "hod"}, section_id="s"
    )
    ranked = apply_boosts([weak_but_everything, strong], section_id="s", settings=SETTINGS)
    assert ranked[0]["chunk_id"] == "strong"


def test_gate_uses_raw_score() -> None:
    p = _passage("p", 0.25, flagged=True, kind="campus")
    apply_boosts([p], settings=SETTINGS)
    assert p["final_score"] > 0.3
    assert best_raw_score([p]) == 0.25  # still below a 0.3 gate


# ---------- citations ----------


def test_invented_citation_is_removed() -> None:
    text, cited = clean_citations("Apply within three days [1]. See also [9].", valid=5)
    assert text == "Apply within three days [1]. See also ."
    assert cited == {1}


def test_grouped_citations_are_split_and_filtered() -> None:
    text, cited = clean_citations("Both rules apply [2, 7, 3].", valid=5)
    assert text == "Both rules apply [2][3]."
    assert cited == {2, 3}


def test_non_citation_brackets_pass_through() -> None:
    text, cited = clean_citations("Use P[A|B] here [1].", valid=2)
    assert text == "Use P[A|B] here [1]."
    assert cited == {1}


def test_streaming_filter_handles_split_markers() -> None:
    f = CitationFilter(valid=3)
    out = "".join(f.feed(piece) for piece in ["Rule [", "1", "] and [", "8]", " done [2"]) + f.flush()
    assert out == "Rule [1] and  done [2"
    assert f.cited == {1}


# ---------- prompts ----------


def test_prompt_renders_pdf_and_lecture_passages() -> None:
    pdf = _passage("x", 0.9, title="Academic Regulations", kind="campus", page=12, badges=["Official"])
    lecture = _passage(
        "y",
        0.8,
        title="MATH F113 · Lecture 4",
        start_s=760.0,
        flagged=True,
        flag_reason="Exam hint: Bayes' theorem",
        instructor={"name": "Dr. Asha Demo", "role": "ic"},
        badges=["Flagged", "IC"],
    )
    rendered = format_passages([pdf, lecture])
    assert rendered.startswith("[1] (Academic Regulations · campus-wide · p. 12 · Official)\ntext of x")
    assert "[2] (MATH F113 · Lecture 4 · 12:40 · Dr. Asha Demo (IC) · Flagged, IC · flag reason: Exam hint" in rendered
    assert format_time(3725) == "1:02:05"


# ---------- passage selection ----------


def test_select_caps_per_source_and_keeps_best_official() -> None:
    from app.rag.answerer import select_passages

    material = [_passage(f"pyq{i}", 0.99 - i * 0.01, kind="material", source_id=f"s{i // 3}") for i in range(9)]
    official = _passage("handout", 0.40, kind="handout", source_id="h")
    chosen = select_passages([*material, official], k=5)
    ids = [p["chunk_id"] for p in chosen]
    assert len(chosen) == 5
    assert "handout" in ids
    sources = [p["source_id"] for p in chosen]
    assert all(sources.count(s) <= 2 for s in set(sources))


def test_select_without_official_is_plain_top_k() -> None:
    from app.rag.answerer import select_passages

    passages = [_passage(f"c{i}", 0.9 - i * 0.1, source_id=f"s{i}") for i in range(7)]
    assert [p["chunk_id"] for p in select_passages(passages, k=5)] == ["c0", "c1", "c2", "c3", "c4"]


def test_math_brackets_are_not_citations() -> None:
    text, cited = clean_citations(r"For $x \in [0, 1]$ the density is flat [2]. $$F = [1]$$ Done [9].", valid=3)
    assert text == r"For $x \in [0, 1]$ the density is flat [2]. $$F = [1]$$ Done ."
    assert cited == {2}


def test_streaming_math_split_across_pieces() -> None:
    f = CitationFilter(valid=2)
    out = "".join(f.feed(p) for p in ["Use $", r"$P(A) \in [0,", " 1]$", "$ here [1] and [5]."]) + f.flush()
    assert out == r"Use $$P(A) \in [0, 1]$$ here [1] and ."
