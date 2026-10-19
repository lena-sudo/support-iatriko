"""Thin sqlite3-compatible adapter over libsql_client (HTTP/WebSocket).

Why: the existing db.py uses sqlite3 patterns (cursor-like execute, fetchone,
row["name"]). libsql_client's ResultSet is similar but not identical.
This adapter exposes a drop-in Connection + Cursor API so db.py keeps working
unchanged when wired to Turso remote.

Dependency: libsql-client (pure Python, works on 3.11+ including 3.14).
"""
from __future__ import annotations

import os as _os
import ssl as _ssl

# macOS Python 3.14 from python.org ships without a trusted CA bundle, so
# aiohttp's ssl.create_default_context() returns a context with no CAs loaded
# and handshakes fail. We fix this two ways:
#   (a) env vars for subprocesses / OpenSSL direct consumers,
#   (b) monkey-patch ssl.create_default_context so aiohttp picks up certifi
#       even though it doesn't read SSL_CERT_FILE itself on this Python build.
# Linux (Streamlit Cloud) has /etc/ssl/certs populated — the patch is a no-op
# there because the context already loads system CAs.
try:
    import certifi as _certifi
    _CA = _certifi.where()
    _os.environ.setdefault("SSL_CERT_FILE", _CA)
    _os.environ.setdefault("REQUESTS_CA_BUNDLE", _CA)

    _orig_default_ctx = _ssl.create_default_context

    def _patched_default_ctx(*args, **kwargs):
        ctx = _orig_default_ctx(*args, **kwargs)
        try:
            ctx.load_verify_locations(cafile=_CA)
        except Exception:
            pass
        return ctx

    if not getattr(_ssl.create_default_context, "_turso_patched", False):
        _patched_default_ctx._turso_patched = True  # type: ignore[attr-defined]
        _ssl.create_default_context = _patched_default_ctx  # type: ignore[assignment]
except ImportError:
    pass

import libsql_client as _lsq


class _CursorLike:
    """Mimics sqlite3.Cursor: iteration, fetchone, fetchall, lastrowid, rowcount."""

    __slots__ = ("_rows", "_i", "lastrowid", "rowcount")

    def __init__(self, result_set: _lsq.ResultSet):
        self._rows = list(result_set.rows)
        self._i = 0
        self.lastrowid = result_set.last_insert_rowid
        self.rowcount = result_set.rows_affected

    def fetchone(self):
        if self._i >= len(self._rows):
            return None
        row = self._rows[self._i]
        self._i += 1
        return row

    def fetchall(self):
        remaining = self._rows[self._i:]
        self._i = len(self._rows)
        return remaining

    def __iter__(self):
        while self._i < len(self._rows):
            yield self._rows[self._i]
            self._i += 1


class TursoConnection:
    """sqlite3.Connection-compatible wrapper.

    Autocommit semantics: libsql_client is request/response. We don't buffer
    into a transaction unless the caller explicitly uses .transaction(). The
    conn()/commit() pattern in db.py becomes a no-op on commit (changes are
    already persisted after each execute).

    Supported subset of sqlite3 API used by db.py:
      - execute(sql, params=()) -> cursor-like
      - executescript(script)
      - commit()
      - close()
    """

    def __init__(self, url: str, auth_token: str):
        # Prefer HTTPS transport — the pure-Python WS path (hrana ws) handshakes
        # as 400 against current Turso edge; HTTP hrana is universally supported.
        if url.startswith("libsql://"):
            url = "https://" + url[len("libsql://"):]
        self._client = _lsq.create_client_sync(url=url, auth_token=auth_token)

    def execute(self, sql: str, params=()):
        args = list(params) if params else None
        rs = self._client.execute(sql, args)
        return _CursorLike(rs)

    def executescript(self, script: str):
        for stmt in _split_sql(script):
            if stmt:
                self._client.execute(stmt)

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass


def _split_sql(script: str) -> list[str]:
    """Split a multi-statement script on ';' at the top level.

    Simple splitter: respects nothing but trims whitespace. Fine for our schema
    (no triggers, no embedded semicolons in strings).
    """
    return [s.strip() for s in script.split(";") if s.strip()]
