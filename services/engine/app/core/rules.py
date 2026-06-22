from dataclasses import dataclass
from enum import StrEnum


MIN_EV = 0.03
MIN_CONFIDENCE = 0.62
RULESET_VERSION = "mvp-scaffold-2026-06-21"


class DecisionType(StrEnum):
    RECOMMEND = "recommend"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class Decision:
    decision: DecisionType
    reason_code: str | None


def decide(ev_per_unit: float, confidence: float, market_liquid: bool, inputs_fresh: bool) -> Decision:
    if not inputs_fresh:
        return Decision(DecisionType.ABSTAIN, "STALE_INPUTS")
    if not market_liquid:
        return Decision(DecisionType.ABSTAIN, "THIN_MARKET")
    if confidence < MIN_CONFIDENCE:
        return Decision(DecisionType.ABSTAIN, "LOW_CONFIDENCE")
    if ev_per_unit < MIN_EV:
        return Decision(DecisionType.ABSTAIN, "NO_EDGE")
    return Decision(DecisionType.RECOMMEND, None)
