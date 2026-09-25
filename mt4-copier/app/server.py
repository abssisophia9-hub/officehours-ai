"""Localhost-only page for subscribers, the kill switch, and the live log."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from app.engine import Engine
from app.store import AuthorizationError

AUTH_LABEL = "I am authorized to trade this account."

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MT4 local trade copier</title>
<style>
  :root { color-scheme: light; --ink: #1c2430; --muted: #5c6b7a; --line: #d5dde6; --paper: #f4f7f8; --card: #fff; --green: #0f6b4c; --red: #9d2c2c; --amber: #8a5a00; }
  * { box-sizing: border-box; }
  body { margin: 0; font: 16px/1.45 "Segoe UI", sans-serif; color: var(--ink); background: var(--paper); }
  header { padding: 20px 24px 8px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  h2 { font-size: 16px; margin: 0 0 10px; }
  main { padding: 8px 24px 40px; display: grid; gap: 16px; }
  .note, .banner, .card, .panel { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
  .note { background: #eef6f2; }
  .banner { background: #fff6e8; border-color: #efd3a3; }
  .warn { color: var(--red); font-weight: 600; }
  .row { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; }
  label { display: grid; gap: 4px; font-size: 13px; color: var(--muted); }
  input, select, textarea, button { font: inherit; color: var(--ink); }
  input, select, textarea { border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; background: #fff; }
  textarea { min-height: 64px; width: 100%; }
  button { border: 0; border-radius: 6px; padding: 8px 12px; background: var(--green); color: white; cursor: pointer; }
  button.secondary { background: #3d4d5c; }
  button.danger { background: var(--red); }
  button.amber { background: var(--amber); }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }
  .check { display: flex; gap: 8px; align-items: center; color: var(--ink); font-size: 15px; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 4px 8px 4px 0; vertical-align: top; border-bottom: 1px solid var(--line); }
  .muted { color: var(--muted); }
  .log { max-height: 280px; overflow: auto; font-family: Consolas, monospace; font-size: 13px; }
  .tag { display: inline-block; min-width: 64px; font-weight: 600; }
</style>
</head>
<body>
<header>
  <h1>MT4 local trade copier</h1>
  <p class="muted">Runs on this computer only. It watches the master terminal's snapshot file and writes commands for subscriber terminals.</p>
</header>
<main>
  <section class="note" id="explain"></section>
  <section class="banner" id="simBanner" hidden></section>
  <section class="panel">
    <h2>Master</h2>
    <div id="master"></div>
    <p class="muted" id="bus"></p>
    <div class="row">
      <button class="amber" id="pauseBtn" type="button">Pause copying</button>
      <button class="danger" id="killBtn" type="button">Kill switch</button>
      <button class="secondary" id="resumeBtn" type="button" hidden>Resume copying</button>
    </div>
    <p id="controlMsg"></p>
  </section>
  <section class="panel">
    <h2>Add a subscriber</h2>
    <form id="addForm">
      <div class="grid">
        <label>Display name<input name="display_name" required placeholder="Alex"></label>
        <label>Slave id<input name="slave_id" required placeholder="alex-mt4" pattern="[A-Za-z0-9_-]{1,32}" title="Letters, numbers, underscore, hyphen"></label>
        <label>Lot mode
          <select name="lot_mode">
            <option value="multiplier">Multiplier</option>
            <option value="fixed">Fixed lot</option>
          </select>
        </label>
        <label>Multiplier<input name="multiplier" type="number" min="0" step="0.01" value="1"></label>
        <label>Fixed lot<input name="fixed_lot" type="number" min="0" step="0.01" value="0.01"></label>
        <label>Max lot<input name="max_lot" type="number" min="0.01" step="0.01" value="10"></label>
        <label>Broker minimum lot<input name="min_lot" type="number" min="0.01" step="0.01" value="0.01"></label>
        <label>Lot step<input name="lot_step" type="number" min="0.01" step="0.01" value="0.01"></label>
        <label>Symbol prefix<input name="symbol_prefix" placeholder=""></label>
        <label>Symbol suffix<input name="symbol_suffix" placeholder=".raw"></label>
      </div>
      <label>Symbol map, one FROM=TO per line
        <textarea name="symbol_map_text" placeholder="GOLD=XAUUSD"></textarea>
      </label>
      <p class="muted">A new subscriber stays off. Open the card below, tick authorization, then enable it.</p>
      <button type="submit">Add subscriber</button>
      <span id="addMsg"></span>
    </form>
  </section>
  <section class="panel">
    <h2>Subscribers</h2>
    <div id="subs"></div>
  </section>
  <section class="panel">
    <h2>Master events</h2>
    <div id="events" class="log"></div>
  </section>
  <section class="panel">
    <h2>Commands and fills</h2>
    <div id="log" class="log"></div>
  </section>
</main>
<script>
const AUTH_LABEL = "I am authorized to trade this account.";
const explain = document.getElementById("explain");
explain.textContent = "An account number cannot place trades. The subscriber MT4 terminal must already be logged in with the trading password and the broker server. This app never asks for that password. It cannot withdraw or transfer funds. Orders it copies are ordinary MT4 orders the account owner can see. Only connect an account whose owner asked you to trade it, then tick: " + AUTH_LABEL;

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

let editing = false;
let lastSubs = "";
const subsEl = document.getElementById("subs");
subsEl.addEventListener("focusin", () => { editing = true; });
subsEl.addEventListener("focusout", () => {
  setTimeout(() => {
    if (!subsEl.contains(document.activeElement)) editing = false;
  }, 150);
});

function mapText(map) {
  return Object.keys(map || {}).map(function (k) { return k + "=" + map[k]; }).join(String.fromCharCode(10));
}

function renderMaster(data) {
  const hb = data.heartbeat || {};
  const el = document.getElementById("master");
  if (!hb.ok) {
    el.innerHTML = "<p>Waiting for MasterSignal. No heartbeat file yet.</p>";
  } else {
    const stale = hb.stale ? " <span class='warn'>stale</span>" : " <span class='muted'>live</span>";
    el.innerHTML = "<div class='row'><span>Account " + esc(hb.account) + "</span><span>Balance " + esc(hb.balance) + "</span><span>Equity " + esc(hb.equity) + "</span><span>Orders " + esc(hb.order_count) + "</span><span>Heartbeat " + esc(hb.time) + stale + "</span></div>";
  }
  document.getElementById("bus").textContent = "Common Files bus: " + data.copier_dir;
  const stopped = data.killed || data.paused;
  document.getElementById("pauseBtn").hidden = !!data.killed;
  document.getElementById("pauseBtn").textContent = data.paused && !data.killed ? "Paused" : "Pause copying";
  document.getElementById("resumeBtn").hidden = !stopped;
  const msg = document.getElementById("controlMsg");
  if (data.killed) msg.textContent = "Kill switch is on. Subscriber terminals will not place new copies until you resume.";
  else if (data.paused) msg.textContent = "Paused. Changes on the master during the pause are not copied later.";
  else msg.textContent = "Copying is armed for enabled, authorized subscribers.";
  document.getElementById("simBanner").hidden = !data.simulate;
  if (data.simulate) {
    document.getElementById("simBanner").textContent = "Simulate mode. The master stream and the subscriber fills are fake, on this computer, so you can check the copier without MT4. The simulated subscriber is already authorized because it is not a real account.";
  }
}

function renderSubs(list) {
  if (!list.length) {
    subsEl.innerHTML = "<p class='muted'>No subscribers yet.</p>";
    return;
  }
  subsEl.innerHTML = list.map((sub) => {
    const auth = sub.authorized ? "checked" : "";
    const en = sub.enabled ? "checked" : "";
    const dis = sub.authorized ? "" : "disabled";
    return `<form class="card" data-slave="${esc(sub.slave_id)}">
      <div class="grid">
        <label>Display name<input name="display_name" value="${esc(sub.display_name)}"></label>
        <label>Slave id<input name="slave_id" value="${esc(sub.slave_id)}" readonly></label>
        <label>Lot mode<select name="lot_mode">
          <option value="multiplier" ${sub.lot_mode === "multiplier" ? "selected" : ""}>Multiplier</option>
          <option value="fixed" ${sub.lot_mode === "fixed" ? "selected" : ""}>Fixed lot</option>
        </select></label>
        <label>Multiplier<input name="multiplier" type="number" min="0" step="0.01" value="${esc(sub.multiplier)}"></label>
        <label>Fixed lot<input name="fixed_lot" type="number" min="0" step="0.01" value="${esc(sub.fixed_lot)}"></label>
        <label>Max lot<input name="max_lot" type="number" min="0.01" step="0.01" value="${esc(sub.max_lot)}"></label>
        <label>Broker minimum lot<input name="min_lot" type="number" min="0.01" step="0.01" value="${esc(sub.min_lot)}"></label>
        <label>Lot step<input name="lot_step" type="number" min="0.01" step="0.01" value="${esc(sub.lot_step)}"></label>
        <label>Symbol prefix<input name="symbol_prefix" value="${esc(sub.symbol_prefix)}"></label>
        <label>Symbol suffix<input name="symbol_suffix" value="${esc(sub.symbol_suffix)}"></label>
      </div>
      <label>Symbol map<textarea name="symbol_map_text">${esc(mapText(sub.symbol_map))}</textarea></label>
      <label class="check"><input type="checkbox" name="authorized" ${auth}> ${esc(AUTH_LABEL)}</label>
      <label class="check"><input type="checkbox" name="enabled" ${en} ${dis}> Enabled</label>
      <div class="row">
        <button type="submit">Save</button>
        <button type="button" class="secondary remove">Remove</button>
        <span class="msg"></span>
      </div>
    </form>`;
  }).join("");
}

function renderEvents(events) {
  const rows = (events || []).slice().reverse().map((ev) =>
    `<tr><td>${esc(ev.time)}</td><td>${esc(ev.event)}</td><td>${esc(ev.ticket)}</td><td>${esc(ev.symbol)}</td><td>${esc(ev.type)}</td><td>${esc(ev.lots)}</td><td>${esc(ev.sl)}</td><td>${esc(ev.tp)}</td></tr>`
  ).join("");
  document.getElementById("events").innerHTML = rows
    ? `<table><thead><tr><th>Time</th><th>Event</th><th>Ticket</th><th>Symbol</th><th>Type</th><th>Lots</th><th>SL</th><th>TP</th></tr></thead><tbody>${rows}</tbody></table>`
    : "<p class='muted'>No master changes since this copier started.</p>";
}

function renderLog(entries) {
  const html = (entries || []).slice().reverse().map((row) =>
    `<div><span class="tag">${esc(row.kind)}</span> ${esc(row.time)} ${esc(row.slave_id)} ${esc(row.text)}</div>`
  ).join("");
  document.getElementById("log").innerHTML = html || "<p class='muted'>No commands yet.</p>";
}

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function formData(form) {
  const data = Object.fromEntries(new FormData(form).entries());
  data.authorized = form.elements.authorized ? form.elements.authorized.checked : false;
  data.enabled = form.elements.enabled ? form.elements.enabled.checked : false;
  return data;
}

document.getElementById("addForm").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const msg = document.getElementById("addMsg");
  try {
    const data = Object.fromEntries(new FormData(ev.target).entries());
    await api("/api/subscribers", data);
    msg.textContent = "Added. It is off until you tick authorization and enable it.";
    ev.target.reset();
    lastSubs = "";
  } catch (err) {
    msg.textContent = err.message;
  }
});

subsEl.addEventListener("change", (ev) => {
  const form = ev.target.form;
  if (!form || !form.elements.authorized) return;
  const enabled = form.elements.enabled;
  if (ev.target.name === "authorized") {
    enabled.disabled = !ev.target.checked;
    if (!ev.target.checked) enabled.checked = false;
  }
  if (ev.target.name === "enabled" && ev.target.checked && !form.elements.authorized.checked) {
    ev.target.checked = false;
    enabled.disabled = true;
  }
});

subsEl.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const msg = form.querySelector(".msg");
  if (form.elements.enabled.checked && !form.elements.authorized.checked) {
    msg.textContent = "Tick authorization before enabling this account.";
    return;
  }
  try {
    await api("/api/subscribers/update", formData(form));
    msg.textContent = "Saved.";
    lastSubs = "";
    editing = false;
  } catch (err) {
    msg.textContent = err.message;
  }
});

subsEl.addEventListener("click", async (ev) => {
  if (!ev.target.classList.contains("remove")) return;
  const form = ev.target.form;
  const slaveId = form.elements.slave_id.value;
  if (!confirm("Stop copying " + slaveId + "? Open trades on that account stay open.")) return;
  await api("/api/subscribers/delete", {slave_id: slaveId});
  lastSubs = "";
  editing = false;
});

document.getElementById("pauseBtn").addEventListener("click", () => api("/api/control", {action: "pause"}));
document.getElementById("killBtn").addEventListener("click", () => api("/api/control", {action: "kill"}));
document.getElementById("resumeBtn").addEventListener("click", () => api("/api/control", {action: "resume"}));

async function refresh() {
  const res = await fetch("/api/state");
  const data = await res.json();
  renderMaster(data);
  renderEvents(data.events);
  renderLog(data.log);
  const serial = JSON.stringify(data.subscribers);
  if (!editing && serial !== lastSubs) {
    lastSubs = serial;
    renderSubs(data.subscribers);
  }
}
refresh();
setInterval(refresh, 1000);
</script>
</body>
</html>
"""


class CopierHandler(BaseHTTPRequestHandler):
    engine: Engine

    def log_message(self, fmt: str, *args) -> None:
        return

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").strip().lower()
        if host.startswith("["):
            end = host.find("]")
            name = host[: end + 1] if end != -1 else host
        else:
            name = host.split(":")[0]
        return name in ("127.0.0.1", "localhost", "[::1]")

    def _send(self, code: int, body: str, content_type: str) -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload), "application/json; charset=utf-8")

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        if length < 0 or length > 1_000_000:
            raise ValueError("Request body is too large")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data

    def do_GET(self) -> None:  # noqa: N802
        if not self._host_ok():
            self._send(403, "forbidden", "text/plain; charset=utf-8")
            return
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
            return
        if path == "/api/state":
            self._json(200, self.engine.public_state())
            return
        if path == "/favicon.ico":
            self._send(204, "", "text/plain")
            return
        self._send(404, "not found", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        if not self._host_ok():
            self._send(403, "forbidden", "text/plain; charset=utf-8")
            return
        path = urlparse(self.path).path
        try:
            body = self._read_body()
            self._post(path, body)
        except AuthorizationError as exc:
            self._json(400, {"error": str(exc)})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})

    def _post(self, path: str, body: dict) -> None:
        store = self.engine.store
        if path == "/api/control":
            action = str(body.get("action") or "")
            self.engine.set_control(action)
            self._json(200, {"ok": True, "paused": store.paused, "killed": store.killed})
            return
        with self.engine.lock:
            if path == "/api/subscribers":
                sub = store.add(body)
                self.engine.write_configs()
                self.engine.add_log("info", f"Added {sub['slave_id']} (disabled)", sub["slave_id"])
                self._json(200, {"subscriber": sub})
                return
            if path == "/api/subscribers/update":
                slave_id = str(body.get("slave_id") or "")
                sub = store.update(slave_id, body)
                self.engine.write_configs()
                state = "enabled" if sub["enabled"] else "disabled"
                self.engine.add_log("info", f"Updated {slave_id} ({state})", slave_id)
                self._json(200, {"subscriber": sub})
                return
            if path == "/api/subscribers/delete":
                slave_id = str(body.get("slave_id") or "")
                if store.get(slave_id) is None:
                    raise KeyError(slave_id)
                current = dict(store.get(slave_id))
                current["enabled"] = False
                current["authorized"] = False
                store.update(slave_id, current)
                self.engine.write_configs()
                store.remove(slave_id)
                self.engine.add_log(
                    "info",
                    f"Removed {slave_id}. Open trades were left as they are.",
                    slave_id,
                )
                self._json(200, {"ok": True})
                return
        self._json(404, {"error": "not found"})


def serve(engine: Engine, host: str = "127.0.0.1", port: int = 8765) -> None:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit("Refusing to bind anything except localhost")
    CopierHandler.engine = engine
    server = ThreadingHTTPServer((host, port), CopierHandler)
    print(f"UI: http://127.0.0.1:{port}")
    print(f"Bus: {engine.copier}")
    print(f"Config: {engine.store.path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        server.server_close()
