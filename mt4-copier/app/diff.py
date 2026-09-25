"""Diff two master order snapshots into copy events."""

from __future__ import annotations

_PRICE_FIELDS = ("sl", "tp", "open_price")
_EPSILON = 1e-8


def _ticket(order: dict) -> int:
    return int(order["ticket"])


def _lots(order: dict) -> float:
    return float(order.get("lots", 0))


def _price_changed(old: dict, new: dict) -> bool:
    for field in _PRICE_FIELDS:
        if abs(float(old.get(field, 0)) - float(new.get(field, 0))) > _EPSILON:
            return True
    return False


def diff_orders(prev_orders: list[dict], curr_orders: list[dict]) -> list[dict]:
    """Compare open-order lists keyed by ticket.

    OPEN: ticket appeared.
    MODIFY: stop loss, take profit, or open price changed.
    PARTIAL: volume decreased and the ticket is still open.
    CLOSE: ticket disappeared.
    Identical books produce an empty list.
    """
    prev = {_ticket(order): order for order in prev_orders}
    curr = {_ticket(order): order for order in curr_orders}
    events: list[dict] = []
    for ticket in sorted(set(prev) | set(curr)):
        if ticket not in prev:
            events.append({"event": "OPEN", "ticket": ticket, "order": curr[ticket]})
            continue
        if ticket not in curr:
            events.append({"event": "CLOSE", "ticket": ticket, "order": prev[ticket]})
            continue
        old = prev[ticket]
        new = curr[ticket]
        if _price_changed(old, new):
            events.append(
                {
                    "event": "MODIFY",
                    "ticket": ticket,
                    "order": new,
                    "previous": old,
                }
            )
        closed = _lots(old) - _lots(new)
        if closed > _EPSILON:
            events.append(
                {
                    "event": "PARTIAL",
                    "ticket": ticket,
                    "order": new,
                    "previous": old,
                    "close_lots": closed,
                }
            )
    return events
