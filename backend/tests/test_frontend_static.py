"""SPA static serving under OFFICEHOURS_ROOT_PATH + path-traversal guards."""

from __future__ import annotations

import os
from pathlib import Path

import anyio
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.frontend_static import _safe_dist_file, mount_frontend
from app.path_prefix import PathPrefixASGI

PREFIX = "/officehours-ai"


def _build_dist(tmp_path: Path) -> tuple[Path, Path]:
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("<html>spa-index-marker</html>", encoding="utf-8")
    (assets / "app.js").write_text("console.log('asset-js-marker');", encoding="utf-8")
    (assets / "app.css").write_text(".ok{color:red}", encoding="utf-8")
    secret = tmp_path / "secret.txt"
    secret.write_text("TOPSECRET-OUTSIDE-DIST", encoding="utf-8")
    return dist, secret


def _app(dist: Path, monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_SERVE_FRONTEND", "true")
    monkeypatch.setenv("OFFICEHOURS_FRONTEND_DIST", str(dist))
    app = FastAPI()
    assert mount_frontend(app) is True
    return PathPrefixASGI(app, PREFIX)


def _client(dist: Path, monkeypatch) -> TestClient:
    return TestClient(_app(dist, monkeypatch))


def _asgi_get(app, path: str) -> tuple[int, bytes, dict[str, str]]:
    """GET with an exact ASGI path (httpx normalizes bare ``../`` away)."""
    status_code = 0
    body = b""
    headers: dict[str, str] = {}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status_code, body, headers
        if message["type"] == "http.response.start":
            status_code = int(message["status"])
            headers = {
                key.decode("latin-1"): value.decode("latin-1")
                for key, value in message.get("headers", [])
            }
        elif message["type"] == "http.response.body":
            body += message.get("body") or b""

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def run():
        await app(scope, receive, send)

    anyio.run(run)
    return status_code, body, headers


def test_safe_dist_file_blocks_traversal(tmp_path: Path):
    dist, secret = _build_dist(tmp_path)
    assert _safe_dist_file(dist, "assets/app.js") == (dist / "assets" / "app.js").resolve()
    assert _safe_dist_file(dist, "../secret.txt") is None
    assert _safe_dist_file(dist, "%2e%2e/secret.txt") is None
    assert _safe_dist_file(dist, "assets/%2e%2e/%2e%2e/secret.txt") is None
    assert _safe_dist_file(dist, "assets/..%2f..%2fsecret.txt") is None
    # Confirmed secret exists but must never be selected.
    assert secret.is_file()


def test_assets_under_prefix_return_200(tmp_path: Path, monkeypatch):
    dist, _ = _build_dist(tmp_path)
    client = _client(dist, monkeypatch)

    js = client.get(f"{PREFIX}/assets/app.js")
    assert js.status_code == 200
    assert "asset-js-marker" in js.text
    ctype = (js.headers.get("content-type") or "").lower()
    assert "javascript" in ctype or "ecmascript" in ctype

    css = client.get(f"{PREFIX}/assets/app.css")
    assert css.status_code == 200
    assert ".ok" in css.text
    assert "text/css" in (css.headers.get("content-type") or "").lower()

    bare = client.get("/assets/app.js")
    assert bare.status_code == 404


def test_path_traversal_returns_spa_index_never_secret(tmp_path: Path, monkeypatch):
    dist, secret = _build_dist(tmp_path)
    app = _app(dist, monkeypatch)
    probes = [
        f"{PREFIX}/../secret.txt",
        f"{PREFIX}/%2e%2e/secret.txt",
        f"{PREFIX}/%2e%2e%2fsecret.txt",
        f"{PREFIX}/assets/%2e%2e/%2e%2e/secret.txt",
        f"{PREFIX}/assets/..%2f..%2fsecret.txt",
    ]
    for probe in probes:
        status_code, body, _headers = _asgi_get(app, probe)
        text = body.decode("utf-8", errors="replace")
        assert status_code == 200, probe
        assert "spa-index-marker" in text, probe
        assert "TOPSECRET-OUTSIDE-DIST" not in text, probe
        assert secret.read_text(encoding="utf-8") == "TOPSECRET-OUTSIDE-DIST"
