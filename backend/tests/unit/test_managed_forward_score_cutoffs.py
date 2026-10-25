"""Stale checked responses cannot rewind managed forward evidence (ADR-365)."""

from decimal import Decimal
from typing import Literal

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.data.models import PriceBar
from app.research.cross_sectional import forward
from app.research.cross_sectional.forward import CrossSectionalPosition
from app.research.dataset import ResearchDataset, prepare_research_dataset
from app.research.lab import portfolio_manager
from app.research.lab.paper import PaperPosition

Kind = Literal["single", "panel"]
Position = PaperPosition | CrossSectionalPosition
_INDEX = pd.bdate_range("2024-01-01", periods=512, tz="UTC")
_NOW = (_INDEX[-1] + pd.Timedelta(days=4)).to_pydatetime()


@pytest.fixture(scope="module")
def datasets() -> dict[str, dict[str, ResearchDataset]]:
    result: dict[str, dict[str, ResearchDataset]] = {}
    for name, count, adjustment in [
        ("stale", 504, 0),
        ("full", 510, 0),
        ("same", 510, 1),
        ("new", 512, 0),
    ]:
        result[name] = {}
        for symbol, sign in [("A", 1), ("B", -1)]:
            bars = []
            for i, timestamp in enumerate(_INDEX[:count]):
                price = Decimal(100 + adjustment) + Decimal(sign * i) / Decimal(100)
                bars.append(
                    PriceBar(
                        symbol=symbol,
                        timestamp_utc=timestamp.to_pydatetime(),
                        open=price,
                        high=price,
                        low=price,
                        close=price,
                        volume=100,
                        adj_factor=Decimal(1),
                        source="yfinance",
                    )
                )
            dataset = prepare_research_dataset(
                bars,
                symbol=symbol,
                source="yfinance",
                adapter_version="synthetic-v1",
                start=_INDEX[0].to_pydatetime(),
                end=_NOW,
                git_commit_hash="a" * 40,
            )
            assert dataset.quality_report.passed
            result[name][symbol] = dataset
    return result


def _position(kind: Kind) -> Position:
    frozen_at = _INDEX[505].to_pydatetime()
    if kind == "single":
        return PaperPosition(
            symbol="A",
            strategy_name="momentum",
            parameters={"lookback": 3, "skip": 0},
            frozen_at=frozen_at,
        )
    return CrossSectionalPosition(
        strategy_name="xs_value",
        parameters={"quantile": 0.5},
        universe_symbols=("A", "B"),
        cost_rate=0.001,
        frozen_at=frozen_at,
        value_scores={"A": 1.0, "B": 0.0},
    )


def _manage(position: Position, data: dict[str, ResearchDataset]) -> Position:
    if isinstance(position, PaperPosition):
        return portfolio_manager.manage_portfolio([position], [], lambda _: data["A"], now=_NOW)[0]
    return forward.manage_cross_sectional_book([position], [], lambda _: data, now=_NOW)[0]


@pytest.mark.parametrize("kind", ["single", "panel"])
@pytest.mark.parametrize("legacy", [False, True])
def test_manager_given_earlier_checked_response_preserves_complete_later_position(
    kind: Kind, legacy: bool, datasets: dict[str, dict[str, ResearchDataset]]
) -> None:
    prior = _manage(_position(kind), datasets["full"])
    assert prior.score is not None
    assert prior.score.forward_bars == 4
    if legacy:
        payload = prior.model_dump(round_trip=True)
        payload["score"]["evidence"] = None
        payload["score"]["forward_equity"] = []
        prior = type(prior).model_validate(payload)
    before = prior.model_dump_json()
    after = _manage(prior, datasets["stale"])
    assert after is prior
    assert after.model_dump_json() == before
    assert after.score is not None
    assert after.score.as_of == _INDEX[509].to_pydatetime()
    assert after.score.forward_bars == 4


@pytest.mark.parametrize("kind", ["single", "panel"])
def test_manager_given_earlier_score_defers_before_lifecycle_evaluation(
    kind: Kind, datasets: dict[str, dict[str, ResearchDataset]], monkeypatch: pytest.MonkeyPatch
) -> None:
    prior = _manage(_position(kind), datasets["full"])

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("stale candidate must not reach lifecycle")

    if kind == "single":
        monkeypatch.setattr(portfolio_manager, "evaluate_lifecycle", forbidden)
    else:
        monkeypatch.setattr(forward, "evaluate_cross_sectional_lifecycle", forbidden)
    assert _manage(prior, datasets["stale"]) is prior


@pytest.mark.parametrize("kind", ["single", "panel"])
def test_manager_given_equal_cutoff_correction_recomputes_score(
    kind: Kind, datasets: dict[str, dict[str, ResearchDataset]]
) -> None:
    prior = _manage(_position(kind), datasets["full"])
    after = _manage(prior, datasets["same"])
    assert prior.score is not None and after.score is not None
    assert after.score.as_of == prior.score.as_of
    assert after.score.forward_return != prior.score.forward_return
    assert after.score.evidence != prior.score.evidence


@pytest.mark.parametrize("kind", ["single", "panel"])
def test_manager_given_newer_cutoff_advances_existing_score(
    kind: Kind, datasets: dict[str, dict[str, ResearchDataset]]
) -> None:
    prior = _manage(_position(kind), datasets["full"])
    after = _manage(prior, datasets["new"])
    assert prior.score is not None and after.score is not None
    assert after.score.as_of > prior.score.as_of
    assert after.score.forward_bars == 6
    assert len(after.score.forward_equity) == 6


@pytest.mark.parametrize("kind", ["single", "panel"])
def test_manager_given_no_prior_score_accepts_initial_zero_bar_score(
    kind: Kind, datasets: dict[str, dict[str, ResearchDataset]]
) -> None:
    after = _manage(_position(kind), datasets["stale"])
    assert after.score is not None
    assert after.score.as_of == _INDEX[503].to_pydatetime()
    assert after.score.forward_bars == 0


@pytest.mark.parametrize("kind", ["single", "panel"])
def test_manager_given_terminal_position_leaves_it_untouched_without_provider(
    kind: Kind, datasets: dict[str, dict[str, ResearchDataset]]
) -> None:
    prior = _manage(_position(kind), datasets["full"])
    payload = prior.model_dump(round_trip=True)
    if kind == "single":
        payload.update(status="closed", closed_at=_NOW, exit_reasons=["terminal fixture"])
    else:
        payload.update(status="retired", retired_at=_NOW, exit_reasons=["terminal fixture"])
    terminal = type(prior).model_validate(payload)

    def forbidden(_: object) -> dict[str, ResearchDataset]:
        raise AssertionError("terminal position must not fetch")

    if isinstance(terminal, PaperPosition):
        after = portfolio_manager.manage_portfolio([terminal], [], forbidden, now=_NOW)[0]
    else:
        after = forward.manage_cross_sectional_book([terminal], [], forbidden, now=_NOW)[0]
    assert after is terminal


@pytest.mark.parametrize("kind", ["single", "panel"])
@given(
    prior_name=st.sampled_from(["stale", "full", "new"]),
    candidate_name=st.sampled_from(["stale", "full", "new"]),
)
@settings(max_examples=9, deadline=None)
def test_manager_retained_cutoff_never_moves_backward_for_checked_response_order(
    kind: Kind,
    datasets: dict[str, dict[str, ResearchDataset]],
    prior_name: str,
    candidate_name: str,
) -> None:
    prior = _manage(_position(kind), datasets[prior_name])
    assert prior.score is not None
    candidate_cutoff = datasets[candidate_name]["A"].frame.index.max().to_pydatetime()
    after = _manage(prior, datasets[candidate_name])
    assert after.score is not None
    assert after.score.as_of == max(prior.score.as_of, candidate_cutoff)
    if candidate_cutoff < prior.score.as_of:
        assert after is prior
