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


def test_timeout_splits_the_batch(monkeypatch):
    timeout = APIError({"message": "canceling statement due to statement timeout", "code": "57014"})
    table = _run(monkeypatch, [timeout, timeout], n_rows=25)
    # 25 times out, its first half (12) times out, then 6 + 6 + 13 succeed: every row lands once.
    assert table.batches == [6, 6, 13]


def test_single_row_timeout_eventually_gives_up(monkeypatch):
    timeout = APIError({"message": "canceling statement due to statement timeout", "code": "57014"})
    with pytest.raises(APIError):
        _run(monkeypatch, [timeout] * 100, n_rows=1)


def test_does_not_retry_real_errors(monkeypatch):
    bad = APIError({"message": "unsupported Unicode escape sequence", "code": "22P05"})
    with pytest.raises(APIError):
        _run(monkeypatch, [bad])


def test_gives_up_after_max_attempts(monkeypatch):
    failures = [httpx.RemoteProtocolError("Server disconnected")] * db.UPSERT_ATTEMPTS
    with pytest.raises(httpx.RemoteProtocolError):
        _run(monkeypatch, failures)


class FakeChunks:
    """Just enough of the query builder for delete_chunks: select/eq/limit and delete/in_."""

    def __init__(self, ids, timeouts=0):
        self.ids, self.timeouts, self.deletes = list(ids), timeouts, []

    def select(self, _):
        self._op = "select"
        return self

    def eq(self, *_):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def delete(self):
        self._op = "delete"
        return self

    def in_(self, _, ids):
        self._ids = ids
        return self

    def execute(self):
        if self._op == "select":
            return type("R", (), {"data": [{"id": i} for i in self.ids[: self._limit]]})()
        if self.timeouts:
            self.timeouts -= 1
            raise APIError({"message": "canceling statement due to statement timeout", "code": "57014"})
        self.deletes.append(len(self._ids))
        self.ids = [i for i in self.ids if i not in self._ids]


def test_delete_chunks_in_batches_with_retry(monkeypatch):
    table = FakeChunks(range(250), timeouts=1)
    monkeypatch.setattr(db, "get_client", lambda: FakeClient(table))
    monkeypatch.setattr(db.time, "sleep", lambda s: None)
    db.delete_chunks("src")
    assert table.deletes == [100, 100, 50]
    assert table.ids == []
