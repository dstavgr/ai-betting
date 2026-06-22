from dataclasses import dataclass


KELLY_MULTIPLIER = 0.25


@dataclass(frozen=True)
class EvResult:
    implied_raw: float
    edge: float
    ev_per_unit: float
    kelly: float
    stake_frac: float


def implied_probability(decimal_odds: float) -> float:
    if decimal_odds <= 1:
        raise ValueError("decimal_odds must be greater than 1")
    return 1 / decimal_odds


def two_way_no_vig(odds_a: float, odds_b: float) -> float:
    if odds_a <= 1 or odds_b <= 1:
        raise ValueError("decimal odds must be greater than 1")
    inv_a = 1 / odds_a
    inv_b = 1 / odds_b
    return inv_a / (inv_a + inv_b)


def evaluate_price(p_fair: float, decimal_odds: float, kelly_multiplier: float = KELLY_MULTIPLIER) -> EvResult:
    if not 0 <= p_fair <= 1:
        raise ValueError("p_fair must be between 0 and 1")
    implied_raw = implied_probability(decimal_odds)
    edge = p_fair - implied_raw
    ev_per_unit = p_fair * decimal_odds - 1
    kelly = max(0.0, ev_per_unit / (decimal_odds - 1))
    return EvResult(
        implied_raw=implied_raw,
        edge=edge,
        ev_per_unit=ev_per_unit,
        kelly=kelly,
        stake_frac=kelly_multiplier * kelly,
    )
