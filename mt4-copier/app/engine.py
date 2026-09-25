"""Watch the master snapshot and write one command file per subscriber."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from app.bridge import (
    append_jsonl,
    atomic_write_json,
    commands_path,
    config_path,
    control_path,
    ensure_bus,
    fills_path,
    read_json,
    read_jsonl,
    snapshot_path,
    status_path,
)
from app.commands import build_command
from app.diff import diff_orders
from app.store import SubscriberStore

_LOG_LIMIT = 200
_EVENT_LIMIT = 50


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _orders_list(book: dict[int, dict]) -> list[dict]:
    return [book[ticket] for ticket in sorted(book)]


class Engine:
    def __init__(self, copier: Path, data: Path, *, simulate: bool = False):
        self.copier = Path(copier)
        self.data = Path(data)
        self.simulate = simulate
        self.data.mkdir(parents=True, exist_ok=True)
        ensure_bus(self.copier)
        self.store = SubscriberStore(self.data / "subscribers.json")
        self.lock = threading.Lock()
        self.last_orders: dict[int, dict] | None = None
        self.mappings: dict[str, dict[int, int]] = {}
        self.seen_ids: dict[str, set[str]] = {}
        self.logged_fill_ids: set[str] = set()
        self.log: list[dict] = []
        self.events: list[dict] = []
        self.last_error = ""
        self._baseline_done = False
        self._load_state()
        self.refresh_from_disk()
        self.write_control()
        self.write_configs()

    def _state_path(self) -> Path:
        return self.data / "engine_state.json"

    def _load_state(self) -> None:
        data = read_json(self._state_path())
        if not data:
            return
        book: dict[int, dict] = {}
        for order in data.get("orders") or []:
            if isinstance(order, dict) and "ticket" in order:
                book[int(order["ticket"])] = order
        self.last_orders = book
        self._baseline_done = True
        self.log = list(data.get("log") or [])[-_LOG_LIMIT:]
        self.events = list(data.get("events") or [])[-_EVENT_LIMIT:]
        self.logged_fill_ids = set(data.get("logged_fill_ids") or [])

    def _save_state(self) -> None:
        book = self.last_orders or {}
        atomic_write_json(
            self._state_path(),
            {
                "orders": _orders_list(book),
                "log": self.log[-_LOG_LIMIT:],
                "events": self.events[-_EVENT_LIMIT:],
                "logged_fill_ids": sorted(self.logged_fill_ids)[-1000:],
            },
        )

    def add_log(self, kind: str, text: str, slave_id: str = "") -> None:
        self.log.append({"time": _now(), "kind": kind, "slave_id": slave_id, "text": text})
        self.log = self.log[-_LOG_LIMIT:]

    def refresh_from_disk(self) -> None:
        """Rebuild command ids and master→slave ticket maps from the bus files."""
        mappings: dict[str, dict[int, int]] = {}
        seen: dict[str, set[str]] = {}
        for sub in self.store.subscribers:
            slave_id = sub["slave_id"]
            commands = read_jsonl(commands_path(self.copier, slave_id))
            seen[slave_id] = {row["id"] for row in commands if row.get("id")}
            mapping: dict[int, int] = {}
            for row in read_jsonl(fills_path(self.copier, slave_id)):
                if row.get("ok") and row.get("event") == "OPEN" and row.get("slave_ticket"):
                    try:
                        mapping[int(row["master_ticket"])] = int(row["slave_ticket"])
                    except (TypeError, ValueError):
                        continue
            mappings[slave_id] = mapping
        self.mappings = mappings
        self.seen_ids = seen

    def write_control(self) -> None:
        atomic_write_json(
            control_path(self.copier),
            {
                "paused": bool(self.store.paused),
                "killed": bool(self.store.killed),
                "updated": _now(),
            },
        )

    def write_configs(self) -> None:
        active_ids = set()
        for sub in self.store.subscribers:
            slave_id = sub["slave_id"]
            active_ids.add(slave_id)
            enabled = bool(sub.get("enabled") and sub.get("authorized") and not self.store.killed)
            atomic_write_json(
                config_path(self.copier, slave_id),
                {
                    "slave_id": slave_id,
                    "enabled": enabled,
                    "paused": bool(self.store.paused or self.store.killed),
                    "max_lot": sub.get("max_lot", 10),
                    "min_lot": sub.get("min_lot", 0.01),
                    "lot_step": sub.get("lot_step", 0.01),
                    "symbol_prefix": sub.get("symbol_prefix", ""),
                    "symbol_suffix": sub.get("symbol_suffix", ""),
                },
            )
        return None

    def set_control(self, action: str) -> None:
        with self.lock:
            if action == "kill":
                self.store.killed = True
                self.store.paused = True
                self.add_log("info", "Kill switch is on. No new copies will be sent.")
            elif action == "pause":
                if self.store.killed:
                    return
                self.store.paused = True
                self.add_log("info", "Copying is paused. Master changes during the pause are not backfilled.")
            elif action == "resume":
                self.store.paused = False
                self.store.killed = False
                self.add_log("info", "Copying resumed.")
            else:
                raise ValueError("Unknown control action")
            self.store.save()
            self.write_control()
            self.write_configs()
            self._save_state()

    def _tracked(self, slave_id: str, ticket: int, command: dict) -> bool:
        if command["id"] in self.seen_ids.get(slave_id, set()):
            return True
        if command["event"] == "OPEN" and int(ticket) in self.mappings.get(slave_id, {}):
            return True
        return False

    def plan_commands(self, subscriber: dict, events: list[dict]) -> list[dict]:
        """Commands that still need writing. Existing ids and ticket maps are skipped."""
        if not subscriber.get("enabled") or not subscriber.get("authorized"):
            return []
        slave_id = subscriber["slave_id"]
        planned: list[dict] = []
        seen = set(self.seen_ids.get(slave_id, set()))
        for event in events:
            command = build_command(event, subscriber)
            if command is None:
                continue
            ticket = int(event["ticket"])
            if command["id"] in seen:
                continue
            if command["event"] == "OPEN" and ticket in self.mappings.get(slave_id, {}):
                continue
            planned.append(command)
            seen.add(command["id"])
        return planned

    def append_command(self, slave_id: str, command: dict) -> bool:
        """Append a command unless that id, or an OPEN for a mapped ticket, is already known."""
        self.refresh_from_disk()
        ticket = int(command["master_ticket"])
        if self._tracked(slave_id, ticket, command):
            return False
        command = dict(command)
        command["time"] = _now()
        append_jsonl(commands_path(self.copier, slave_id), command)
        self.seen_ids.setdefault(slave_id, set()).add(command["id"])
        self.add_log(
            "command",
            f"{command['event']} {command.get('symbol', '')} lots {command.get('lots', '')} master {ticket}",
            slave_id,
        )
        return True

    def handle_events(self, subscriber: dict, events: list[dict]) -> list[dict]:
        written = []
        for command in self.plan_commands(subscriber, events):
            if self.append_command(subscriber["slave_id"], command):
                written.append(command)
        return written

    def ingest_fills(self) -> None:
        with self.lock:
            self._ingest_fills_locked()

    def _ingest_fills_locked(self) -> None:
        self.refresh_from_disk()
        for sub in self.store.subscribers:
            slave_id = sub["slave_id"]
            for row in read_jsonl(fills_path(self.copier, slave_id)):
                cid = str(row.get("command_id") or "")
                if not cid or cid in self.logged_fill_ids:
                    continue
                self.logged_fill_ids.add(cid)
                ok = bool(row.get("ok"))
                message = str(row.get("message") or ("ok" if ok else "failed"))
                slave_ticket = row.get("slave_ticket") or ""
                self.add_log(
                    "fill",
                    f"{row.get('event', '')} {'ok' if ok else 'fail'} slave {slave_ticket} {message}",
                    slave_id,
                )
        self._save_state()

    def poll(self) -> list[dict]:
        with self.lock:
            return self._poll_locked()

    def _poll_locked(self) -> list[dict]:
        try:
            self.store.load()
            ensure_bus(self.copier)
            self.refresh_from_disk()
            self.write_control()
            self.write_configs()
            self._ingest_fills_locked()
            snap = read_json(snapshot_path(self.copier))
            if snap is None:
                self._save_state()
                return []
            current_list = []
            for order in snap.get("orders") or []:
                if isinstance(order, dict) and "ticket" in order and order.get("symbol"):
                    current_list.append(order)
            current = {int(order["ticket"]): order for order in current_list}
            if not self._baseline_done or self.last_orders is None:
                self.last_orders = current
                self._baseline_done = True
                self.add_log(
                    "info",
                    "Baseline snapshot stored. Trades already open on the master are not copied.",
                )
                self._save_state()
                return []
            events = diff_orders(_orders_list(self.last_orders), _orders_list(current))
            self.last_orders = current
            stamped = []
            for event in events:
                order = event["order"]
                stamped.append(
                    {
                        "time": _now(),
                        "event": event["event"],
                        "ticket": int(event["ticket"]),
                        "symbol": order.get("symbol", ""),
                        "type": order.get("type", ""),
                        "lots": order.get("lots", 0),
                        "sl": order.get("sl", 0),
                        "tp": order.get("tp", 0),
                        "price": order.get("open_price", 0),
                        "close_lots": event.get("close_lots", 0),
                    }
                )
            if stamped:
                self.events.extend(stamped)
                self.events = self.events[-_EVENT_LIMIT:]
            written: list[dict] = []
            if events and not self.store.paused and not self.store.killed:
                for sub in self.store.active_subscribers():
                    written.extend(self.handle_events(sub, events))
            self._save_state()
            self.last_error = ""
            return written
        except Exception as exc:  # keep the UI process alive if a snapshot is unreadable
            self.last_error = str(exc)
            self.add_log("error", self.last_error)
            return []

    def heartbeat(self) -> dict:
        path = status_path(self.copier)
        data = read_json(path) or {}
        age = None
        stale = True
        if path.exists():
            age = max(0.0, time.time() - path.stat().st_mtime)
            stale = age > 5
        if not data:
            return {
                "ok": False,
                "stale": True,
                "time": "",
                "account": None,
                "balance": None,
                "equity": None,
                "order_count": None,
                "comment_tag": "",
                "trade_allowed": None,
                "age_seconds": age,
            }
        return {
            "ok": True,
            "stale": stale,
            "time": data.get("time", ""),
            "account": data.get("account"),
            "balance": data.get("balance"),
            "equity": data.get("equity"),
            "order_count": data.get("order_count"),
            "comment_tag": data.get("comment_tag", ""),
            "trade_allowed": data.get("trade_allowed"),
            "age_seconds": None if age is None else round(age, 1),
        }

    def public_state(self) -> dict:
        with self.lock:
            return {
                "simulate": self.simulate,
                "copier_dir": str(self.copier),
                "paused": self.store.paused,
                "killed": self.store.killed,
                "heartbeat": self.heartbeat(),
                "events": list(self.events),
                "subscribers": list(self.store.subscribers),
                "log": list(self.log),
                "last_error": self.last_error,
            }
