from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from math import exp, isfinite, log

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

LOG_RATE_MIN = -4.5
LOG_RATE_MAX = 4.0
RATING_BOUND = 2.5
HOME_ADVANTAGE_BOUND = 1.0
RHO_BOUND = 0.25
MIN_TAU = 1e-12


@dataclass(frozen=True)
class DixonColesModel:
    team_ids: tuple[int, ...]
    attack: dict[int, float]
    defence: dict[int, float]
    home_advantage: float
    rho: float
    average_attack: float
    average_defence: float
    xi: float
    fitted_at: datetime | None
    match_count: int
    log_likelihood: float
    converged: bool


@dataclass(frozen=True)
class _PreparedMatches:
    team_ids: tuple[int, ...]
    home_idx: np.ndarray
    away_idx: np.ndarray
    goals_home: np.ndarray
    goals_away: np.ndarray
    weights: np.ndarray
    fitted_at: datetime | None


def fit_dixon_coles(
    matches: Iterable[tuple[int, int, int, int, datetime]],
    *,
    xi: float = 0.0019,
) -> DixonColesModel:
    prepared = _prepare_matches(matches, xi=max(0.0, float(xi)))
    if prepared.goals_home.size == 0:
        return DixonColesModel(
            team_ids=(),
            attack={},
            defence={},
            home_advantage=0.0,
            rho=0.0,
            average_attack=0.0,
            average_defence=0.0,
            xi=max(0.0, float(xi)),
            fitted_at=None,
            match_count=0,
            log_likelihood=0.0,
            converged=False,
        )

    initial = _initial_parameters(prepared)
    bounds = _parameter_bounds(len(prepared.team_ids))
    result = minimize(
        _negative_log_likelihood,
        initial,
        args=(prepared,),
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 500, "ftol": 1e-9},
    )

    params = result.x if result.x.size and np.all(np.isfinite(result.x)) else initial
    attack_values, defence_values, home_advantage, rho = _unpack_parameters(
        params,
        len(prepared.team_ids),
    )
    log_likelihood = -_negative_log_likelihood(params, prepared)
    attack = {
        team_id: float(attack_values[index])
        for index, team_id in enumerate(prepared.team_ids)
    }
    defence = {
        team_id: float(defence_values[index])
        for index, team_id in enumerate(prepared.team_ids)
    }

    return DixonColesModel(
        team_ids=prepared.team_ids,
        attack=attack,
        defence=defence,
        home_advantage=float(home_advantage),
        rho=float(rho),
        average_attack=float(np.mean(attack_values)) if attack_values.size else 0.0,
        average_defence=float(np.mean(defence_values)) if defence_values.size else 0.0,
        xi=max(0.0, float(xi)),
        fitted_at=prepared.fitted_at,
        match_count=int(prepared.goals_home.size),
        log_likelihood=float(log_likelihood) if isfinite(float(log_likelihood)) else 0.0,
        converged=bool(result.success),
    )


def score_matrix(
    model: DixonColesModel,
    home_id: int,
    away_id: int,
    max_goals: int = 10,
) -> np.ndarray:
    max_goals = max(0, int(max_goals))
    lambda_home, mu_away = _expected_goals(model, home_id, away_id)
    home_pmf = _poisson_pmf(lambda_home, max_goals)
    away_pmf = _poisson_pmf(mu_away, max_goals)
    matrix = np.outer(home_pmf, away_pmf)

    low_score_limit = min(max_goals, 1)
    for home_goals in range(low_score_limit + 1):
        for away_goals in range(low_score_limit + 1):
            matrix[home_goals, away_goals] *= max(
                0.0,
                dixon_coles_tau(home_goals, away_goals, lambda_home, mu_away, model.rho),
            )

    total = float(matrix.sum())
    if not isfinite(total) or total <= 0:
        size = max_goals + 1
        return np.full((size, size), 1.0 / (size * size), dtype=float)
    return matrix / total


def match_probabilities(
    model: DixonColesModel,
    home_id: int,
    away_id: int,
) -> dict[str, float]:
    matrix = score_matrix(model, home_id, away_id)
    goals = np.arange(matrix.shape[0])
    home_goals = goals[:, np.newaxis]
    away_goals = goals[np.newaxis, :]

    home_win = float(matrix[home_goals > away_goals].sum())
    draw = float(np.trace(matrix))
    away_win = float(matrix[home_goals < away_goals].sum())
    total_1x2 = home_win + draw + away_win
    if total_1x2 <= 0 or not isfinite(total_1x2):
        home_win = draw = away_win = 1 / 3
    else:
        home_win /= total_1x2
        draw /= total_1x2
        away_win /= total_1x2

    over_2_5 = float(matrix[(home_goals + away_goals) > 2].sum())
    btts = float(matrix[(home_goals >= 1) & (away_goals >= 1)].sum())
    return {
        "home_win": _clamp_probability(home_win),
        "draw": _clamp_probability(draw),
        "away_win": _clamp_probability(away_win),
        "over_2_5": _clamp_probability(over_2_5),
        "btts": _clamp_probability(btts),
    }


def dixon_coles_tau(
    home_goals: int,
    away_goals: int,
    lambda_home: float,
    mu_away: float,
    rho: float,
) -> float:
    if home_goals == 0 and away_goals == 0:
        return 1.0 - lambda_home * mu_away * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 + lambda_home * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 + mu_away * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    return 1.0


def _prepare_matches(
    matches: Iterable[tuple[int, int, int, int, datetime]],
    *,
    xi: float,
) -> _PreparedMatches:
    rows: list[tuple[int, int, int, int, datetime]] = []
    team_ids: set[int] = set()
    for home_id, away_id, goals_home, goals_away, kickoff_at in matches:
        if home_id is None or away_id is None or kickoff_at is None:
            continue
        home_goals = int(goals_home)
        away_goals = int(goals_away)
        if home_goals < 0 or away_goals < 0:
            continue
        home_team_id = int(home_id)
        away_team_id = int(away_id)
        kickoff = _ensure_utc(kickoff_at)
        rows.append((home_team_id, away_team_id, home_goals, away_goals, kickoff))
        team_ids.update((home_team_id, away_team_id))

    if not rows:
        return _PreparedMatches(
            team_ids=(),
            home_idx=np.array([], dtype=int),
            away_idx=np.array([], dtype=int),
            goals_home=np.array([], dtype=float),
            goals_away=np.array([], dtype=float),
            weights=np.array([], dtype=float),
            fitted_at=None,
        )

    ordered_team_ids = tuple(sorted(team_ids))
    team_index = {team_id: index for index, team_id in enumerate(ordered_team_ids)}
    fitted_at = max(row[4] for row in rows)
    weights = np.array(
        [
            exp(-xi * max(0.0, (fitted_at - row[4]).total_seconds() / 86_400))
            for row in rows
        ],
        dtype=float,
    )
    return _PreparedMatches(
        team_ids=ordered_team_ids,
        home_idx=np.array([team_index[row[0]] for row in rows], dtype=int),
        away_idx=np.array([team_index[row[1]] for row in rows], dtype=int),
        goals_home=np.array([row[2] for row in rows], dtype=float),
        goals_away=np.array([row[3] for row in rows], dtype=float),
        weights=weights,
        fitted_at=fitted_at,
    )


def _initial_parameters(prepared: _PreparedMatches) -> np.ndarray:
    team_count = len(prepared.team_ids)
    scored = np.zeros(team_count, dtype=float)
    conceded = np.zeros(team_count, dtype=float)
    appearances = np.zeros(team_count, dtype=float)
    np.add.at(scored, prepared.home_idx, prepared.goals_home)
    np.add.at(scored, prepared.away_idx, prepared.goals_away)
    np.add.at(conceded, prepared.home_idx, prepared.goals_away)
    np.add.at(conceded, prepared.away_idx, prepared.goals_home)
    np.add.at(appearances, prepared.home_idx, 1.0)
    np.add.at(appearances, prepared.away_idx, 1.0)

    total_goals = prepared.goals_home.sum() + prepared.goals_away.sum()
    league_goal_rate = max(0.25, float(total_goals / (2 * prepared.goals_home.size)))
    scored_rate = (scored + league_goal_rate) / (appearances + 1.0)
    conceded_rate = (conceded + league_goal_rate) / (appearances + 1.0)
    attack = np.log(np.maximum(scored_rate, 0.05) / league_goal_rate)
    attack -= float(np.mean(attack)) if attack.size else 0.0
    defence = -np.log(np.maximum(conceded_rate, 0.05) / league_goal_rate)

    home_goal_rate = max(0.25, float(np.mean(prepared.goals_home)))
    away_goal_rate = max(0.25, float(np.mean(prepared.goals_away)))
    home_advantage = log(home_goal_rate / away_goal_rate)

    attack = np.clip(attack, -RATING_BOUND, RATING_BOUND)
    defence = np.clip(defence, -RATING_BOUND, RATING_BOUND)
    n_attack_params = max(team_count - 1, 0)
    return np.concatenate(
        [
            attack[:n_attack_params],
            defence,
            np.array(
                [
                    float(np.clip(home_advantage, -HOME_ADVANTAGE_BOUND, HOME_ADVANTAGE_BOUND)),
                    0.0,
                ]
            ),
        ]
    )


def _parameter_bounds(team_count: int) -> list[tuple[float, float]]:
    n_attack_params = max(team_count - 1, 0)
    return (
        [(-RATING_BOUND, RATING_BOUND)] * n_attack_params
        + [(-RATING_BOUND, RATING_BOUND)] * team_count
        + [(-HOME_ADVANTAGE_BOUND, HOME_ADVANTAGE_BOUND), (-RHO_BOUND, RHO_BOUND)]
    )


def _negative_log_likelihood(params: np.ndarray, prepared: _PreparedMatches) -> float:
    attack, defence, home_advantage, rho = _unpack_parameters(params, len(prepared.team_ids))
    lambda_home = np.exp(
        np.clip(
            attack[prepared.home_idx] - defence[prepared.away_idx] + home_advantage,
            LOG_RATE_MIN,
            LOG_RATE_MAX,
        )
    )
    mu_away = np.exp(
        np.clip(
            attack[prepared.away_idx] - defence[prepared.home_idx],
            LOG_RATE_MIN,
            LOG_RATE_MAX,
        )
    )

    tau_values = _tau_array(
        prepared.goals_home,
        prepared.goals_away,
        lambda_home,
        mu_away,
        rho,
    )
    if np.any(tau_values <= MIN_TAU) or not np.all(np.isfinite(tau_values)):
        return 1e12 + float(np.sum(np.maximum(MIN_TAU - tau_values, 0.0)))

    log_home = (
        prepared.goals_home * np.log(lambda_home)
        - lambda_home
        - gammaln(prepared.goals_home + 1)
    )
    log_away = prepared.goals_away * np.log(mu_away) - mu_away - gammaln(prepared.goals_away + 1)
    log_likelihood = prepared.weights * (log_home + log_away + np.log(tau_values))
    value = -float(np.sum(log_likelihood))
    return value if isfinite(value) else 1e12


def _unpack_parameters(
    params: np.ndarray,
    team_count: int,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    n_attack_params = max(team_count - 1, 0)
    attack = np.zeros(team_count, dtype=float)
    if n_attack_params:
        attack[:n_attack_params] = params[:n_attack_params]
        attack[-1] = -float(np.sum(attack[:n_attack_params]))
        attack -= float(np.mean(attack))
    defence_start = n_attack_params
    defence_end = defence_start + team_count
    defence = np.array(params[defence_start:defence_end], dtype=float)
    home_advantage = float(params[defence_end])
    rho = float(params[defence_end + 1])
    return attack, defence, home_advantage, rho


def _tau_array(
    goals_home: np.ndarray,
    goals_away: np.ndarray,
    lambda_home: np.ndarray,
    mu_away: np.ndarray,
    rho: float,
) -> np.ndarray:
    tau_values = np.ones_like(lambda_home, dtype=float)
    mask_00 = (goals_home == 0) & (goals_away == 0)
    mask_01 = (goals_home == 0) & (goals_away == 1)
    mask_10 = (goals_home == 1) & (goals_away == 0)
    mask_11 = (goals_home == 1) & (goals_away == 1)
    tau_values[mask_00] = 1.0 - lambda_home[mask_00] * mu_away[mask_00] * rho
    tau_values[mask_01] = 1.0 + lambda_home[mask_01] * rho
    tau_values[mask_10] = 1.0 + mu_away[mask_10] * rho
    tau_values[mask_11] = 1.0 - rho
    return tau_values


def _expected_goals(model: DixonColesModel, home_id: int, away_id: int) -> tuple[float, float]:
    home_attack = _team_value(model.attack, home_id, model.average_attack)
    away_attack = _team_value(model.attack, away_id, model.average_attack)
    home_defence = _team_value(model.defence, home_id, model.average_defence)
    away_defence = _team_value(model.defence, away_id, model.average_defence)
    lambda_home = exp(
        float(
            np.clip(
                home_attack - away_defence + model.home_advantage,
                LOG_RATE_MIN,
                LOG_RATE_MAX,
            )
        )
    )
    mu_away = exp(float(np.clip(away_attack - home_defence, LOG_RATE_MIN, LOG_RATE_MAX)))
    return lambda_home, mu_away


def _team_value(values: dict[int, float], team_id: int, fallback: float) -> float:
    try:
        return float(values[int(team_id)])
    except (KeyError, TypeError, ValueError):
        return float(fallback)


def _poisson_pmf(rate: float, max_goals: int) -> np.ndarray:
    rate = max(exp(LOG_RATE_MIN), min(exp(LOG_RATE_MAX), float(rate)))
    pmf = np.empty(max_goals + 1, dtype=float)
    pmf[0] = exp(-rate)
    for goals in range(1, max_goals + 1):
        pmf[goals] = pmf[goals - 1] * rate / goals
    return pmf


def _clamp_probability(value: float) -> float:
    if not isfinite(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
