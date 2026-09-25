"""Subscriber list stored next to the app, not in any other product database."""

from __future__ import annotations

import re
from pathlib import Path

from app.bridge import atomic_write_json, read_json

_SLAVE_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


class AuthorizationError(ValueError):
    """Enabling a subscriber requires an explicit authorization confirmation."""


def parse_symbol_map(text: str) -> dict[str, str]:
    table: dict[str, str] = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Symbol map line needs FROM=TO, got {line!r}")
        source, dest = line.split("=", 1)
        source = source.strip()
        dest = dest.strip()
        if not source or not dest:
            raise ValueError(f"Symbol map line needs FROM=TO, got {line!r}")
        table[source] = dest
    return table


def _number(value: object, default: float) -> float:
    if value is None or value == "":
        return float(default)
    number = float(value)
    if number != number:  # NaN
        raise ValueError("Lot values must be numbers")
    return number


def normalize_subscriber(raw: dict, *, existing: dict | None = None) -> dict:
    base = {
        "display_name": "",
        "slave_id": "",
        "lot_mode": "multiplier",
        "multiplier": 1.0,
        "fixed_lot": 0.01,
        "max_lot": 10.0,
        "min_lot": 0.01,
        "lot_step": 0.01,
        "symbol_prefix": "",
        "symbol_suffix": "",
        "symbol_map": {},
        "enabled": False,
        "authorized": False,
    }
    if existing:
        base.update(existing)
    if "slave_id" in raw and raw["slave_id"] is not None:
        base["slave_id"] = str(raw["slave_id"]).strip()
    if not _SLAVE_ID.match(base["slave_id"]):
        raise ValueError("Slave id must be 1-32 letters, numbers, underscores, or hyphens")
    if "display_name" in raw:
        base["display_name"] = str(raw.get("display_name") or "").strip()[:80]
    if not base["display_name"]:
        base["display_name"] = base["slave_id"]
    mode = str(raw.get("lot_mode", base["lot_mode"]) or "multiplier").lower()
    if mode not in ("multiplier", "fixed"):
        raise ValueError("Lot mode must be multiplier or fixed")
    base["lot_mode"] = mode
    base["multiplier"] = _number(raw.get("multiplier", base["multiplier"]), 1.0)
    base["fixed_lot"] = _number(raw.get("fixed_lot", base["fixed_lot"]), 0.01)
    base["max_lot"] = _number(raw.get("max_lot", base["max_lot"]), 10.0)
    base["min_lot"] = _number(raw.get("min_lot", base["min_lot"]), 0.01)
    base["lot_step"] = _number(raw.get("lot_step", base["lot_step"]), 0.01)
    if base["multiplier"] < 0 or base["fixed_lot"] < 0 or base["max_lot"] < 0:
        raise ValueError("Lot values cannot be negative")
    if base["min_lot"] <= 0 or base["lot_step"] <= 0:
        raise ValueError("Minimum lot and lot step must be greater than zero")
    if base["max_lot"] < base["min_lot"]:
        raise ValueError("Max lot must be at least the minimum lot")
    base["symbol_prefix"] = str(raw.get("symbol_prefix", base["symbol_prefix"]) or "")
    base["symbol_suffix"] = str(raw.get("symbol_suffix", base["symbol_suffix"]) or "")
    if "symbol_map" in raw and isinstance(raw["symbol_map"], dict):
        base["symbol_map"] = {str(k): str(v) for k, v in raw["symbol_map"].items() if str(k) and str(v)}
    elif "symbol_map_text" in raw:
        base["symbol_map"] = parse_symbol_map(str(raw.get("symbol_map_text") or ""))
    if "authorized" in raw:
        base["authorized"] = bool(raw["authorized"])
    if "enabled" in raw:
        base["enabled"] = bool(raw["enabled"])
    if base["enabled"] and not base["authorized"]:
        if bool(raw.get("enabled")):
            raise AuthorizationError("Tick authorization before enabling this account")
        base["enabled"] = False
    return base


class SubscriberStore:
    def __init__(self, path: Path):
        self.path = path
        self.paused = False
        self.killed = False
        self.subscribers: list[dict] = []
        self.load()

    def load(self) -> None:
        data = read_json(self.path) or {}
        self.paused = bool(data.get("paused", False))
        self.killed = bool(data.get("killed", False))
        self.subscribers = []
        for raw in data.get("subscribers") or []:
            if isinstance(raw, dict):
                try:
                    self.subscribers.append(normalize_subscriber(raw))
                except (ValueError, TypeError):
                    continue

    def save(self) -> None:
        atomic_write_json(
            self.path,
            {
                "paused": self.paused,
                "killed": self.killed,
                "subscribers": self.subscribers,
            },
        )

    def get(self, slave_id: str) -> dict | None:
        for sub in self.subscribers:
            if sub["slave_id"] == slave_id:
                return sub
        return None

    def add(self, raw: dict) -> dict:
        """New subscribers are always disabled and not yet authorized."""
        incoming = dict(raw)
        incoming["enabled"] = False
        incoming["authorized"] = False
        sub = normalize_subscriber(incoming)
        if self.get(sub["slave_id"]):
            raise ValueError(f"Slave id {sub['slave_id']} already exists")
        self.subscribers.append(sub)
        self.save()
        return sub

    def update(self, slave_id: str, raw: dict) -> dict:
        current = self.get(slave_id)
        if current is None:
            raise KeyError(slave_id)
        merged = dict(raw)
        merged["slave_id"] = slave_id
        updated = normalize_subscriber(merged, existing=current)
        if updated["enabled"] and not updated["authorized"]:
            raise AuthorizationError("Tick authorization before enabling this account")
        index = self.subscribers.index(current)
        self.subscribers[index] = updated
        self.save()
        return updated

    def remove(self, slave_id: str) -> None:
        self.subscribers = [sub for sub in self.subscribers if sub["slave_id"] != slave_id]
        self.save()

    def active_subscribers(self) -> list[dict]:
        if self.paused or self.killed:
            return []
        return [sub for sub in self.subscribers if sub.get("enabled") and sub.get("authorized")]
