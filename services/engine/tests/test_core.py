from app.core.ev import evaluate_price, implied_probability, two_way_no_vig
from app.core.rules import DecisionType, decide


def test_implied_probability() -> None:
    assert implied_probability(2.0) == 0.5


def test_two_way_no_vig() -> None:
    assert round(two_way_no_vig(2.1, 1.8), 4) == 0.4615


def test_evaluate_price_positive_edge() -> None:
    result = evaluate_price(0.55, 2.0)
    assert result.implied_raw == 0.5
    assert round(result.edge, 2) == 0.05
    assert round(result.ev_per_unit, 2) == 0.10
    assert round(result.stake_frac, 3) == 0.025


def test_decision_branches() -> None:
    assert decide(0.05, 0.8, True, False).reason_code == "STALE_INPUTS"
    assert decide(0.05, 0.8, False, True).reason_code == "THIN_MARKET"
    assert decide(0.05, 0.4, True, True).reason_code == "LOW_CONFIDENCE"
    assert decide(0.01, 0.8, True, True).reason_code == "NO_EDGE"
    assert decide(0.05, 0.8, True, True).decision == DecisionType.RECOMMEND
