# AUI IT smoke test (~5 minutes)

Assume the app is live at **`https://cdn.aui.ma/officehours-ai/`** (or replace
`BASE` below with your proxy URL that keeps the `/officehours-ai` prefix).

```bash
BASE=https://cdn.aui.ma/officehours-ai
# Local clean-room proxy example:
# BASE=http://127.0.0.1:8080/officehours-ai
```

Password for demo accounts: **`aui-demo`** (names only — no other secrets).

---

## 1. Health

```bash
curl -sS -o /tmp/oh-health.json -w '%{http_code}\n' "$BASE/health"
cat /tmp/oh-health.json
```

**Expect:** HTTP `200`. JSON includes `"status":"healthy"` and `"database_ok":true`.

---

## 2. SPA shell + asset MIME types

```bash
curl -sS -D /tmp/oh-spa.hdr -o /tmp/oh-spa.html -w '%{http_code}\n' "$BASE/"
# Pick the JS/CSS paths from the HTML (CDN build uses /officehours-ai/assets/…):
JS=$(grep -oE '/officehours-ai/assets/[^"]+\.js' /tmp/oh-spa.html | head -1)
CSS=$(grep -oE '/officehours-ai/assets/[^"]+\.css' /tmp/oh-spa.html | head -1)
# If BASE already ends with /officehours-ai, strip the duplicated prefix for curl:
HOST=${BASE%/officehours-ai}
curl -sS -D /tmp/oh-js.hdr -o /dev/null -w 'JS %{http_code}\n' "$HOST$JS"
curl -sS -D /tmp/oh-css.hdr -o /dev/null -w 'CSS %{http_code}\n' "$HOST$CSS"
grep -i '^content-type:' /tmp/oh-js.hdr /tmp/oh-css.hdr
```

**Expect:** SPA `200` with HTML. JS `200` and `Content-Type` containing
`javascript` (or `ecmascript`). CSS `200` and `Content-Type: text/css`.

---

## 3. Demo login — student / TA / professor

```bash
for EMAIL in s.elidrissi@aui.ma a.chen@aui.ma a.benali@aui.ma; do
  echo "LOGIN $EMAIL"
  curl -sS -X POST "$BASE/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"password\":\"aui-demo\"}"
  echo
done
```

**Expect:** each returns HTTP `200` JSON with a non-empty `"token"`.

---

## 4. Submit an ask (MiniLM present + offline)

Requires the MiniLM companion unpacked and `HF_HOME` + offline flags set
(see `.env.production.example`). Clustering may still be `lexical`.

```bash
TOKEN=$(curl -sS -X POST "$BASE/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"s.elidrissi@aui.ma","password":"aui-demo"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')
COURSE=$(curl -sS "$BASE/courses/mine" -H "Authorization: Bearer $TOKEN" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)[0]["id"])')
curl -sS -D /tmp/oh-ask.hdr -o /tmp/oh-ask.json -w '%{http_code}\n' \
  -X POST "$BASE/requests/" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"text\":\"Explain red-black tree delete fixup rotations for CSC 2302\",\"course_id\":$COURSE,\"course\":\"CSC 2302\",\"anonymous\":true,\"help_mode\":\"message\"}"
head -c 400 /tmp/oh-ask.json; echo
```

**Expect:** HTTP `201`. Body includes triage fields (category / urgency). Not `500`.

---

## 5. WebSocket under the prefix

```bash
python3 - <<'PY'
import asyncio, json, os, sys
try:
    import websockets
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "websockets"])
    import websockets

base = os.environ.get("BASE", "https://cdn.aui.ma/officehours-ai").rstrip("/")
# derive http→ws
ws_base = base.replace("https://", "wss://").replace("http://", "ws://")

async def main():
    import urllib.request
    def post(path, data=None, token=None):
        req = urllib.request.Request(
            base + path,
            data=None if data is None else json.dumps(data).encode(),
            headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
            method="GET" if data is None else "POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    login = post("/auth/login", {"email": "s.elidrissi@aui.ma", "password": "aui-demo"})
    token = login["token"]
    course_id = post("/courses/mine", token=token)[0]["id"] if False else None
    req = urllib.request.Request(base + "/courses/mine", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        course_id = json.load(resp)[0]["id"]
    uri = f"{ws_base}/ws?token={token}&course_id={course_id}"
    async with websockets.connect(uri) as ws:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        print(msg)
        assert msg.get("type") == "connected"
        print("WEBSOCKET_OK")

asyncio.run(main())
PY
```

**Expect:** prints a `connected` payload and `WEBSOCKET_OK`.

---

## 6. Path traversal probes (must not leak files)

Probe the **uvicorn** origin (bypasses nginx URI normalization) and, optionally,
the public proxy. Replace `ORIGIN` if uvicorn is not on loopback.

```bash
ORIGIN=http://127.0.0.1:8000/officehours-ai
# --path-as-is keeps ../ from being normalized by curl
curl --path-as-is -sS -o /tmp/oh-trav1.html -w '%{http_code}\n' "$ORIGIN/../.env"
curl --path-as-is -sS -o /tmp/oh-trav2.html -w '%{http_code}\n' "$ORIGIN/%2e%2e/.env"
grep -iE 'doctype|html' /tmp/oh-trav1.html /tmp/oh-trav2.html | head
# Must NOT contain secret-like assignments from a real .env
! grep -E '^(DATABASE_URL|CANVAS_API_TOKEN|GEMINI_API_KEY)=' /tmp/oh-trav1.html /tmp/oh-trav2.html

# Proxy (may be nginx 404 if ../ is normalized out of the location — also OK):
curl --path-as-is -sS -o /tmp/oh-trav-proxy.html -w '%{http_code}\n' "$BASE/%2e%2e/.env"
! grep -E '^(DATABASE_URL|CANVAS_API_TOKEN|GEMINI_API_KEY)=' /tmp/oh-trav-proxy.html
```

**Expect (uvicorn):** HTTP `200` SPA HTML, **not** raw `.env` / file contents.  
**Expect (proxy):** SPA `200` **or** nginx `404` — never secret file contents.

---

## 7. Resources empty state (no API keys)

```bash
TOKEN=$(curl -sS -X POST "$BASE/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"s.elidrissi@aui.ma","password":"aui-demo"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')
curl -sS "$BASE/health" | python3 -m json.tool | head -80
# Optional: hit pedagogy resources endpoint your build exposes and confirm
# YouTube/Gemini-backed rows are empty when keys are unset.
```

**Expect:** health shows LLM/YouTube key flags false (or equivalent). Resources UI/API
does not require keys; empty / keyless-only Wikipedia is OK.

---

## Pass / fail checklist

| Check | Pass? |
| --- | --- |
| `/health` 200 + database_ok | |
| SPA + JS/CSS MIME | |
| Student / TA / professor login | |
| Ask submit 201 (MiniLM offline) | |
| WebSocket `connected` | |
| `../` and `%2e%2e` → SPA, not secrets | |
| Resources empty without keys | |
