import asyncio

import pytest

from app.ingest import flagger


def _segs(texts: list[tuple[float, str]]) -> list[dict]:
    return [{"text": text, "start": start, "end": start + 3.0} for start, text in texts]


def test_cues_match_on_word_boundaries() -> None:
    segs = _segs(
        [
            (0, "Let us do an example."),
            (5, "This will definitely come in the exam."),
            (10, "Note this down."),
            (15, "It is important that f is continuous."),
            (20, "The examiner liked it."),
            (25, "This was asked last year."),
        ]
    )
    assert flagger.find_candidates(segs) == [1, 2, 3, 5]


def test_parse_verdict_requires_reason() -> None:
    assert flagger.parse_verdict('{"is_flag": true, "reason": "Exam hint: Bayes"}') == (True, "Exam hint: Bayes")
    assert flagger.parse_verdict('{"is_flag": true, "reason": ""}')[0] is False
    assert flagger.parse_verdict('{"is_flag": false, "reason": "x"}')[0] is False
    assert flagger.parse_verdict('noise {"is_flag": true, "reason": "Formula"} noise') == (True, "Formula")
    assert flagger.parse_verdict("not json")[0] is False


class FakeProvider:
    def __init__(self, verdicts: list[str]) -> None:
        self.verdicts = verdicts
        self.calls = 0

    async def generate(self, *_: object, **__: object) -> str:
        self.calls += 1
        return self.verdicts.pop(0)


def test_adjacent_cues_merge_into_one_moment(monkeypatch: pytest.MonkeyPatch) -> None:
    segs = _segs(
        [
            (40, "Bayes theorem is P of B given A times P of A over P of B."),
            (43, "Please note this formula down."),
            (46, "This will definitely come in the exam."),
            (70, "It is important that the events are disjoint."),
            (99, "The law of total probability was asked last year."),
        ]
    )
    fake = FakeProvider(
        [
            '{"is_flag": true, "reason": "Exam hint: Bayes formula"}',
            '{"is_flag": false, "reason": ""}',
            '{"is_flag": true, "reason": "Asked last year: total probability"}',
        ]
    )
    monkeypatch.setattr(flagger, "get_provider", lambda: fake)
    moments = asyncio.run(flagger.detect("Lecture", segs))
    assert fake.calls == 3  # the 46 s cue merged without an LLM call
    assert [m["reason"] for m in moments] == ["Exam hint: Bayes formula", "Asked last year: total probability"]
    assert moments[0]["start_s"] == 40 and moments[0]["end_s"] == 49
    assert "come in the exam" in moments[0]["quote"]

    chunks = [
        {"id": "lec_0_0", "content": "", "page": None, "start_s": 0.0, "end_s": 95.0},
        {"id": "lec_95_1", "content": "", "page": None, "start_s": 95.0, "end_s": 120.0},
    ]
    reasons = flagger.apply_to_chunks(chunks, moments)
    assert reasons == {"lec_0_0": "Exam hint: Bayes formula", "lec_95_1": "Asked last year: total probability"}
