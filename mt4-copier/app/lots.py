"""Lot sizing for a subscriber. Volume is clamped onto the broker step."""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


def _d(value: float | int | str) -> Decimal:
    return Decimal(str(value))


def clamp_lots(raw: float, min_lot: float, max_lot: float, lot_step: float) -> float:
    """Round a positive size onto the step, then clamp to min and max.

    Zero or negative sizes stay zero so a multiplier of 0 does not become a
    minimum-lot trade. A positive size below the broker minimum is raised.
    """
    step = _d(lot_step)
    if step <= 0:
        return 0.0
    if raw <= 0:
        return 0.0
    minimum = _d(min_lot)
    maximum = _d(max_lot)
    if maximum < minimum:
        return 0.0
    units = (_d(raw) / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    min_units = (minimum / step).to_integral_value(rounding=ROUND_CEILING)
    max_units = (maximum / step).to_integral_value(rounding=ROUND_FLOOR)
    if min_units > max_units:
        return 0.0
    if units > max_units:
        units = max_units
    if units < min_units:
        units = min_units
    lots = units * step
    return float(lots)


def scale_lots(
    master_lots: float,
    mode: str,
    multiplier: float,
    fixed_lot: float,
    min_lot: float,
    max_lot: float,
    lot_step: float,
) -> float:
    """Scale a master volume by multiplier or replace it with a fixed lot."""
    if (mode or "multiplier").lower() == "fixed":
        raw = float(fixed_lot)
    else:
        raw = float(master_lots) * float(multiplier)
    return clamp_lots(raw, min_lot, max_lot, lot_step)
