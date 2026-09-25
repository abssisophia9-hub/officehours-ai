"""Stable command ids and per-subscriber command bodies."""

from __future__ import annotations

import hashlib

from app.lots import scale_lots
from app.symbols import map_symbol


def _num(value: float | int | str) -> str:
    return f"{float(value):.8f}"


def command_id(event: str, ticket: int, **fields: float) -> str:
    """Id derived from the master ticket, event, and the fields that define it.

    The same logical event always yields the same id, so writing it twice
    does not open a second position.
    """
    kind = event.upper()
    parts = [str(int(ticket)), kind]
    if kind == "MODIFY":
        parts.append(_num(fields["price"]))
        parts.append(_num(fields["sl"]))
        parts.append(_num(fields["tp"]))
    elif kind == "PARTIAL":
        parts.append(_num(fields["lots"]))
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:20]


def _base(event: str, order: dict, symbol: str, cid: str) -> dict:
    return {
        "id": cid,
        "event": event,
        "master_ticket": int(order["ticket"]),
        "symbol": symbol,
        "mapped": True,
        "type": str(order.get("type", "")).upper(),
        "comment": str(order.get("comment", "")),
        "magic": int(order.get("magic", 0)),
        "open_time": str(order.get("open_time", "")),
    }


def build_command(event: dict, subscriber: dict) -> dict | None:
    """Turn one master event into one slave command, or None if there is nothing to send."""
    order = event["order"]
    ticket = int(order["ticket"])
    symbol = map_symbol(
        str(order.get("symbol", "")),
        subscriber.get("symbol_prefix", ""),
        subscriber.get("symbol_suffix", ""),
        subscriber.get("symbol_map") or {},
    )
    if not symbol:
        return None
    kind = event["event"]
    if kind == "OPEN":
        lots = scale_lots(
            float(order.get("lots", 0)),
            subscriber.get("lot_mode", "multiplier"),
            float(subscriber.get("multiplier", 1)),
            float(subscriber.get("fixed_lot", 0)),
            float(subscriber.get("min_lot", 0.01)),
            float(subscriber.get("max_lot", 10)),
            float(subscriber.get("lot_step", 0.01)),
        )
        if lots <= 0:
            return None
        cid = command_id("OPEN", ticket)
        body = _base("OPEN", order, symbol, cid)
        body.update(
            {
                "lots": lots,
                "price": float(order.get("open_price", 0)),
                "sl": float(order.get("sl", 0)),
                "tp": float(order.get("tp", 0)),
            }
        )
        return body
    if kind == "MODIFY":
        price = float(order.get("open_price", 0))
        sl = float(order.get("sl", 0))
        tp = float(order.get("tp", 0))
        cid = command_id("MODIFY", ticket, price=price, sl=sl, tp=tp)
        body = _base("MODIFY", order, symbol, cid)
        body.update({"price": price, "sl": sl, "tp": tp, "lots": float(order.get("lots", 0))})
        return body
    if kind == "PARTIAL":
        previous = event.get("previous") or order
        new_lots = scale_lots(
            float(order.get("lots", 0)),
            subscriber.get("lot_mode", "multiplier"),
            float(subscriber.get("multiplier", 1)),
            float(subscriber.get("fixed_lot", 0)),
            float(subscriber.get("min_lot", 0.01)),
            float(subscriber.get("max_lot", 10)),
            float(subscriber.get("lot_step", 0.01)),
        )
        prev_lots = scale_lots(
            float(previous.get("lots", 0)),
            subscriber.get("lot_mode", "multiplier"),
            float(subscriber.get("multiplier", 1)),
            float(subscriber.get("fixed_lot", 0)),
            float(subscriber.get("min_lot", 0.01)),
            float(subscriber.get("max_lot", 10)),
            float(subscriber.get("lot_step", 0.01)),
        )
        close_lots = round(prev_lots - new_lots, 8)
        if close_lots <= 1e-8:
            return None
        cid = command_id("PARTIAL", ticket, lots=float(order.get("lots", 0)))
        body = _base("PARTIAL", order, symbol, cid)
        body.update(
            {
                "lots": new_lots,
                "close_lots": close_lots,
                "price": float(order.get("open_price", 0)),
                "sl": float(order.get("sl", 0)),
                "tp": float(order.get("tp", 0)),
            }
        )
        return body
    if kind == "CLOSE":
        cid = command_id("CLOSE", ticket)
        body = _base("CLOSE", order, symbol, cid)
        body.update(
            {
                "lots": float(order.get("lots", 0)),
                "price": float(order.get("open_price", 0)),
                "sl": float(order.get("sl", 0)),
                "tp": float(order.get("tp", 0)),
            }
        )
        return body
    return None
