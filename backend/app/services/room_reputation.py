"""Weighted AUI Rooms reputation.

Node Points are raw contribution. Hilbert Weight ŵ is a quality inner-product
divided by the L2-norm of activity — accepted solutions and unique “unlocked
it” marks count more than publishing volume. ROOMS score saturates in (0, 1)
so a 0.353 reads like a GPA-style standing, then maps to a rank tier.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Reputation:
    rooms: int
    solutions: int
    accepted: int
    helpful_votes: int
    node_points: int
    hilbert_weight: float
    rooms_score: float
    tier: str
    stars: int


def node_points(*, rooms: int, solutions: int, accepted: int, helpful_votes: int) -> int:
    return int(rooms + solutions + (2 * helpful_votes) + (4 * accepted))


def hilbert_weight(*, rooms: int, solutions: int, accepted: int, helpful_votes: int) -> float:
    quality = (4.0 * accepted) + (2.0 * helpful_votes)
    volume = math.sqrt(1.0 + rooms + solutions)
    return round(quality / volume, 3)


def rooms_score(weight: float) -> float:
    return round(1.0 - math.exp(-max(weight, 0.0) / 3.0), 3)


def rank_tier(score: float) -> str:
    if score < 0.12:
        return "Newcomer"
    if score < 0.28:
        return "Junior"
    if score < 0.45:
        return "Beginner"
    if score < 0.62:
        return "Contributor"
    if score < 0.80:
        return "Helper"
    return "Mentor"


def star_rating(score: float) -> int:
    return max(1, min(5, int(round(score * 5)) or 1)) if score > 0 else 0


def compute_reputation(
    *,
    rooms: int = 0,
    solutions: int = 0,
    accepted: int = 0,
    helpful_votes: int = 0,
) -> Reputation:
    points = node_points(
        rooms=rooms,
        solutions=solutions,
        accepted=accepted,
        helpful_votes=helpful_votes,
    )
    weight = hilbert_weight(
        rooms=rooms,
        solutions=solutions,
        accepted=accepted,
        helpful_votes=helpful_votes,
    )
    score = rooms_score(weight)
    return Reputation(
        rooms=rooms,
        solutions=solutions,
        accepted=accepted,
        helpful_votes=helpful_votes,
        node_points=points,
        hilbert_weight=weight,
        rooms_score=score,
        tier=rank_tier(score),
        stars=star_rating(score),
    )
