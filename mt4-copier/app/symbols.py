"""Translate a master symbol into the subscriber broker's symbol."""

from __future__ import annotations


def map_symbol(
    symbol: str,
    prefix: str = "",
    suffix: str = "",
    symbol_map: dict | None = None,
) -> str:
    """Apply an explicit map first, otherwise prefix + symbol + suffix."""
    symbol = (symbol or "").strip()
    if not symbol:
        return ""
    table = symbol_map or {}
    if symbol in table and table[symbol]:
        return str(table[symbol])
    upper = symbol.upper()
    for key, value in table.items():
        if str(key).upper() == upper and value:
            return str(value)
    return f"{prefix or ''}{symbol}{suffix or ''}"
