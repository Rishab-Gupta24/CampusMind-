from app.ingest.chunker import MAX_WORDS, chunk_lecture, chunk_pdf


def _pages() -> list[dict]:
    long_para = " ".join(f"word{i}." for i in range(900))
    return [
        {"page": 1, "text": "Rule 4.3 Makeup tests.\n\nA student who misses a test may apply."},
        {"page": 2, "text": long_para},
        {"page": 3, "text": "Short page."},
    ]


def _segments() -> list[dict]:
    segs = []
    t = 0.0
    for i in range(60):
        segs.append({"text": f"sentence {i}", "start": t, "end": t + 4.0})
        t += 4.0 + (2.0 if i % 20 == 19 else 0.2)
    return segs


def test_pdf_ids_are_deterministic() -> None:
    first = chunk_pdf("src", _pages())
    second = chunk_pdf("src", _pages())
    assert [c["id"] for c in first] == [c["id"] for c in second]
    assert len({c["id"] for c in first}) == len(first)


def test_pdf_chunks_not_empty_and_within_one_page() -> None:
    chunks = chunk_pdf("src", _pages())
    assert all(c["content"].strip() for c in chunks)
    assert all(len(c["content"].split()) <= MAX_WORDS for c in chunks)
    assert {c["page"] for c in chunks} == {1, 2, 3}
    assert all(c["id"].startswith(f"src_{c['page']}_") for c in chunks)


def test_pdf_long_page_has_overlap() -> None:
    page2 = [c for c in chunk_pdf("src", _pages()) if c["page"] == 2]
    assert len(page2) >= 3
    tail = page2[0]["content"].split()[-5:]
    assert " ".join(tail) in page2[1]["content"]


def test_lecture_windows_keep_times_and_ids() -> None:
    chunks = chunk_lecture("lec", _segments())
    again = chunk_lecture("lec", _segments())
    assert [c["id"] for c in chunks] == [c["id"] for c in again]
    assert all(c["content"] for c in chunks)
    for chunk in chunks[:-1]:
        assert 60 <= chunk["end_s"] - chunk["start_s"] <= 94  # one segment may push past 90 s
    starts = [c["start_s"] for c in chunks]
    assert starts == sorted(starts)
    assert chunks[0]["id"] == "lec_0_0"


def test_empty_inputs() -> None:
    assert chunk_pdf("src", []) == []
    assert chunk_lecture("lec", []) == []
