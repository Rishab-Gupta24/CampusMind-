"""upsert_chunks: small batches, retries transient Supabase failures, never retries real errors."""

import httpx
import pytest
from postgrest.exceptions import APIError

from app import db


class FakeTable:
    def __init__(self, failures: list[Exception]):
        self.failures = failures
        self.batches: list[int] = []

    def upsert(self, rows):
        self._rows = rows
        return self

    def execute(self):
        if self.failures:
            raise self.failures.pop(0)
        self.batches.append(len(self._rows))


class FakeClient:
    def __init__(self, table: FakeTable):
        self._table = table

    def table(self, name):
        return self._table


def _run(monkeypatch, failures, n_rows=60):
    table = FakeTable(failures)
    monkeypatch.setattr(db, "get_client", lambda: FakeClient(table))
    monkeypatch.setattr(db.time, "sleep", lambda s: None)
    db.upsert_chunks([{"id": str(i)} for i in range(n_rows)])
    return table


def test_batches_are_small(monkeypatch):
    table = _run(monkeypatch, [])
    assert table.batches == [25, 25, 10]


def test_retries_dropped_connection_and_timeout(monkeypatch):
    failures = [
        httpx.RemoteProtocolError("Server disconnected"),
        APIError({"message": "canceling statement due to statement timeout", "code": "57014"}),
    ]
    table = _run(monkeypatch, failures)
    assert sum(table.batches) == 60


def test_does_not_retry_real_errors(monkeypatch):
    bad = APIError({"message": "unsupported Unicode escape sequence", "code": "22P05"})
    with pytest.raises(APIError):
        _run(monkeypatch, [bad])


def test_gives_up_after_max_attempts(monkeypatch):
    failures = [httpx.RemoteProtocolError("Server disconnected")] * db.UPSERT_ATTEMPTS
    with pytest.raises(httpx.RemoteProtocolError):
        _run(monkeypatch, failures)
