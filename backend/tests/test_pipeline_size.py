"""A PDF still too big for Storage after compression fails early with a message the user can act on."""

from types import SimpleNamespace

from app.ingest import pipeline


def test_oversized_pdf_fails_with_clear_message(monkeypatch, tmp_path):
    big = tmp_path / "big.pdf"
    big.write_bytes(b"%PDF-" + b"0" * (2 * 1024 * 1024))
    updates: list[dict] = []
    monkeypatch.setattr(pipeline.prepare, "prepare_pdf", lambda src, dst: big)
    monkeypatch.setattr(pipeline.db, "update_source", lambda sid, fields: updates.append(fields))
    monkeypatch.setattr(pipeline.db, "upload_file", lambda *a: (_ for _ in ()).throw(AssertionError("uploaded")))
    settings = SimpleNamespace(max_stored_mb=1, tmp_dir=tmp_path)
    monkeypatch.setattr(pipeline, "get_settings", lambda: settings)

    pipeline.process_document("src-1", tmp_path / "upload.pdf")

    final = updates[-1]
    assert final["status"] == "failed"
    assert "over 1 MB after compression" in final["error"]
