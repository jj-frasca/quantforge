"""ADR-033 reporting: the honest state of the research programme in one object. Answers the
questions a session actually asks — how much has been searched, how many graduates there are, how
many are distinguishable from best-of-N selection luck, which ones came closest, and whether the
survivors are outperforming the non-survivors in the forward book."""

from datetime import UTC, datetime

import pytest

from app.research.lab.experiment import Experiment, Graduate, Trial
from app.research.lab.gate import GateConfig, GateResult
from app.research.lab.paper import PaperPosition
from app.research.lab.pool_report import summarize_pool

_NOW = datetime(2026, 8, 18, tzinfo=UTC)


def _trial(dsr: float = 0.5) -> Trial:
    return Trial(
        strategy_name="sma",
        parameters={"fast": 5, "slow": 20},
        observed_sharpe=1.0,
        deflated_sharpe=dsr,
        pbo=0.1,
        parameter_stability_score=0.8,
    )


def _exp(
    symbol: str,
    *,
    holdout_sharpe: float | None = None,
    holdout_n_bars: int = 1080,
    strategy: str = "sma",
) -> Experiment:
    graduate = None
    if holdout_sharpe is not None:
        graduate = Graduate(
            strategy_name=strategy,
            parameters={"fast": 5, "slow": 20},
            gate_result=GateResult(
                passed=True,
                dsr_ok=True,
                pbo_ok=True,
                stability_ok=True,
                mintrl_ok=True,
                holdout_ok=True,
                required_track_record_years=1.0,
                gate_config_version="v",
            ),
            holdout_sharpe=holdout_sharpe,
            holdout_total_return=0.1,
            holdout_n_bars=holdout_n_bars,
        )
    return Experiment(
        symbol=symbol,
        strategy_names=[strategy],
        gate_config=GateConfig(),
        trials=[_trial()],
        lifetime_trials=10,
        graduate=graduate,
    )


def test_report_counts_the_search_effort() -> None:
    report = summarize_pool([_exp("A"), _exp("B"), _exp("A", holdout_sharpe=0.5)], [])
    assert report.n_experiments == 3
    assert report.n_symbols == 2
    assert report.n_trials == 30  # lifetime trials, the DSR/MinTRL denominator


def test_report_separates_graduate_experiments_from_leaderboard_graduates() -> None:
    # A symbol hunted twice collapses to ONE leaderboard row — the raw graduate-experiment count
    # overstates how many distinct names actually graduated.
    report = summarize_pool(
        [_exp("A", holdout_sharpe=0.5), _exp("A", holdout_sharpe=0.6), _exp("B")], []
    )
    assert report.n_graduate_experiments == 2
    assert report.n_leaderboard_graduates == 1


def test_report_counts_how_many_graduates_clear_the_deflation_bar() -> None:
    # 2 symbols, 4.3y holdout -> a low bar that a 3.0 Sharpe clears and a 0.2 does not.
    report = summarize_pool([_exp("A", holdout_sharpe=3.0), _exp("B", holdout_sharpe=0.2)], [])
    assert report.n_leaderboard_graduates == 2
    assert report.n_surviving_deflation == 1


def test_report_ranks_near_misses_by_how_close_they_came_to_the_bar() -> None:
    # "Closest" is the RATIO to its own bar, not the raw Sharpe: a 1.4 Sharpe against a 2.8 bar
    # (short holdout) is further away than a 1.2 against a 1.3.
    # 100 names in the universe, so the bar is high enough that both genuinely fail it.
    filler = [_exp(f"F{i}") for i in range(98)]
    report = summarize_pool(
        [
            _exp("FAR", holdout_sharpe=1.4, holdout_n_bars=400, strategy="far"),
            _exp("CLOSE", holdout_sharpe=1.2, holdout_n_bars=1080, strategy="close"),
            *filler,
        ],
        [],
        top_near_misses=2,
    )
    assert [m.symbol for m in report.near_misses] == ["CLOSE", "FAR"]
    assert report.near_misses[0].ratio_to_bar > report.near_misses[1].ratio_to_bar
    assert report.near_misses[0].strategy_name == "close"


def test_report_excludes_survivors_from_the_near_miss_list() -> None:
    report = summarize_pool([_exp("WINNER", holdout_sharpe=9.0), _exp("B", holdout_sharpe=0.1)], [])
    assert [m.symbol for m in report.near_misses] == ["B"]


def test_report_of_an_empty_pool_is_all_zeros() -> None:
    report = summarize_pool([], [])
    assert (report.n_experiments, report.n_symbols, report.n_leaderboard_graduates) == (0, 0, 0)
    assert report.near_misses == []
    assert report.book.n_survivors == 0


def test_report_carries_the_forward_book_cohorts() -> None:
    book = [
        PaperPosition(
            symbol="A",
            strategy_name="sma",
            parameters={"fast": 5},
            frozen_at=_NOW,
            survives_universe_deflation=False,
        )
    ]
    report = summarize_pool([_exp("A", holdout_sharpe=0.2)], book)
    assert report.book.n_non_survivors == 1
    assert report.n_open_positions == 1


def test_report_ignores_closed_positions_in_the_book_summary() -> None:
    closed = PaperPosition(
        symbol="A",
        strategy_name="sma",
        parameters={"fast": 5},
        frozen_at=_NOW,
        status="closed",
        closed_at=_NOW,
        survives_universe_deflation=True,
    )
    report = summarize_pool([_exp("A", holdout_sharpe=0.2)], [closed])
    assert report.n_open_positions == 0
    assert report.book.n_survivors == 0


def test_near_miss_bar_matches_the_adr_018_formula() -> None:
    from app.research.lab.universe import expected_max_sharpe_under_null

    report = summarize_pool([_exp("A", holdout_sharpe=0.2), _exp("B", holdout_sharpe=0.1)], [])
    miss = report.near_misses[0]
    assert miss.bar == pytest.approx(expected_max_sharpe_under_null(2, 1080 / 252))


def test_near_misses_collapse_repeat_hunts_of_the_same_symbol_and_strategy() -> None:
    # The pool holds one experiment per hunt, so a name re-hunted daily produces near-identical
    # rows. Showing seven FDX lines crowds out six other names — keep the best per pair.
    filler = [_exp(f"F{i}") for i in range(98)]
    repeats = [_exp("FDX", holdout_sharpe=1.0 + i / 100, strategy="tfmr") for i in range(7)]
    report = summarize_pool([*repeats, _exp("OTHER", holdout_sharpe=0.9), *filler], [])
    assert [m.symbol for m in report.near_misses] == ["FDX", "OTHER"]
    assert report.near_misses[0].holdout_sharpe == pytest.approx(1.06)  # the best of the repeats


def test_near_misses_keep_distinct_strategies_for_the_same_symbol() -> None:
    filler = [_exp(f"F{i}") for i in range(98)]
    report = summarize_pool(
        [
            _exp("FDX", holdout_sharpe=1.0, strategy="tfmr"),
            _exp("FDX", holdout_sharpe=0.9, strategy="rsi"),
            *filler,
        ],
        [],
    )
    assert {(m.symbol, m.strategy_name) for m in report.near_misses} == {
        ("FDX", "tfmr"),
        ("FDX", "rsi"),
    }


# --- ADR-038/039: the pool's own out-of-sample diagnostics, for comparison against the null ---


def _exp_with_diagnostics(
    symbol: str, *, walk_forward: float | None, purged_cv: float | None, graduated: bool
) -> Experiment:
    experiment = _exp(symbol, holdout_sharpe=1.0 if graduated else None)
    trial = experiment.trials[0].model_copy(
        update={"walk_forward_oos_sharpe": walk_forward, "purged_cv_oos_sharpe": purged_cv}
    )
    return experiment.model_copy(update={"trials": [trial]})


def test_report_summarizes_the_out_of_sample_diagnostics_of_gate_passers() -> None:
    """ADR-038/039's revisit trigger is 'compare passers against the null', so the pool side of
    that comparison has to be one command, not a fresh script every session."""
    experiments = [
        _exp_with_diagnostics("AAA", walk_forward=1.4, purged_cv=0.9, graduated=True),
        _exp_with_diagnostics("BBB", walk_forward=0.6, purged_cv=0.2, graduated=True),
        _exp_with_diagnostics("CCC", walk_forward=-0.3, purged_cv=-0.1, graduated=False),
    ]
    report = summarize_pool(experiments, [])

    assert report.walk_forward_graduates is not None
    assert report.walk_forward_graduates.n == 2  # only the gate passers
    assert report.walk_forward_graduates.median == pytest.approx(1.0)
    assert report.walk_forward_graduates.maximum == pytest.approx(1.4)
    assert report.purged_cv_graduates is not None
    assert report.purged_cv_graduates.n == 2


def test_diagnostics_are_none_when_no_graduate_carries_them() -> None:
    """The 3,227 experiments predating ADR-038 have no walk-forward number. 'Not measured' must
    not read as 'measured zero'."""
    report = summarize_pool([_exp("AAA", holdout_sharpe=1.0)], [])
    assert report.walk_forward_graduates is None
    assert report.purged_cv_graduates is None


# --- ADR-043: what must be TRUE, reported beside what must be OBSERVED ---


def test_report_carries_the_detectable_edge_frontier() -> None:
    """The bar answers "what must be observed"; a session reading "0 of N clear the bar" needs the
    other half — the true edge that clears it 80% of the time — in the same breath."""
    report = summarize_pool([_exp("AAA", holdout_sharpe=1.2), _exp("BBB")], [])
    frontier = report.frontier
    assert frontier is not None
    assert frontier.n_symbols == 2
    assert frontier.holdout_years == pytest.approx(1080 / 252)
    assert frontier.detectable_sharpe > frontier.bar


def test_the_frontier_uses_the_median_holdout_length_of_the_graduates() -> None:
    """A pool mixing 4-year and 1-year holdouts has no single bar, so the frontier is quoted at the
    median length — taking the max or the min would flatter or damn the design by selection."""
    report = summarize_pool(
        [
            _exp("AAA", holdout_sharpe=1.2, holdout_n_bars=252),
            _exp("BBB", holdout_sharpe=1.2, holdout_n_bars=1080),
            _exp("CCC", holdout_sharpe=1.2, holdout_n_bars=2520),
        ],
        [],
    )
    assert report.frontier is not None
    assert report.frontier.holdout_years == pytest.approx(1080 / 252)


def test_a_pool_with_no_graduate_has_no_frontier() -> None:
    """No graduate means no measured holdout length, and inventing one would publish a detectable
    edge for a design that was never run."""
    assert summarize_pool([_exp("AAA"), _exp("BBB")], []).frontier is None


# --- ADR-051: the same statistic the null records — every finalist, not only the gate passers ---


def test_report_summarizes_the_out_of_sample_diagnostics_of_every_finalist() -> None:
    """The null artifacts record one finalist per SEARCHED symbol, graduate or not. Restricting the
    pool side to gate passers compared two different statistics and, under ADR-046's repaired trial
    denominator, compared against nothing at all."""
    experiments = [
        _exp_with_diagnostics("AAA", walk_forward=1.4, purged_cv=0.9, graduated=True),
        _exp_with_diagnostics("BBB", walk_forward=0.6, purged_cv=0.2, graduated=True),
        _exp_with_diagnostics("CCC", walk_forward=-0.3, purged_cv=-0.1, graduated=False),
    ]
    report = summarize_pool(experiments, [])

    assert report.walk_forward_finalists is not None
    assert report.walk_forward_finalists.n == 3  # the non-graduate counts too
    assert report.walk_forward_finalists.median == pytest.approx(0.6)
    assert report.purged_cv_finalists is not None
    assert report.purged_cv_finalists.n == 3
    assert report.purged_cv_finalists.median == pytest.approx(0.2)


def test_finalist_diagnostics_survive_a_pool_with_no_graduate_at_all() -> None:
    """The 2026-08-20 run: 603 experiments, 0 graduates. The gate-passer window is empty and the
    finalist window is the only one left, so it must not depend on graduation."""
    experiments = [
        _exp_with_diagnostics("AAA", walk_forward=0.5, purged_cv=0.4, graduated=False),
        _exp_with_diagnostics("BBB", walk_forward=0.7, purged_cv=0.6, graduated=False),
    ]
    report = summarize_pool(experiments, [])

    assert report.walk_forward_graduates is None
    assert report.walk_forward_finalists is not None
    assert report.walk_forward_finalists.n == 2
    assert report.walk_forward_finalists.median == pytest.approx(0.6)


def test_finalist_diagnostics_are_none_when_no_experiment_carries_them() -> None:
    """A pre-ADR-038/039 pool must still report 'not measured' rather than a measured zero — the
    finalist window widens the sample, it does not invent one."""
    report = summarize_pool([_exp("AAA", holdout_sharpe=1.0)], [])
    assert report.walk_forward_finalists is None
    assert report.purged_cv_finalists is None


# --- ADR-052: which search families the summarized rows actually came from ---


def test_report_counts_the_experiments_of_each_search_family() -> None:
    """A pool that mixes families has no single median — it has a blend of two procedures, and the
    reader cannot see that without being told which families are present."""
    experiments = [
        _exp("AAA").model_copy(update={"search_config_version": "fam-a"}),
        _exp("BBB").model_copy(update={"search_config_version": "fam-a"}),
        _exp("CCC").model_copy(update={"search_config_version": "fam-b"}),
    ]
    report = summarize_pool(experiments, [])

    assert report.search_config_versions == {"fam-a": 2, "fam-b": 1}


def test_an_empty_pool_reports_no_search_families() -> None:
    assert summarize_pool([], []).search_config_versions == {}


def test_report_takes_the_median_searched_history_of_the_pool() -> None:
    """The number a reader compares against the null artifact's own n_bars. The median, because a
    pool mixing 21-year names with recent listings has no single length."""
    experiments = [
        _exp("AAA").model_copy(update={"n_bars": 5000}),
        _exp("BBB").model_copy(update={"n_bars": 5400}),
        _exp("CCC").model_copy(update={"n_bars": 900}),
    ]
    assert summarize_pool(experiments, []).median_n_bars == 5000


def test_a_pool_of_experiments_with_no_bar_count_reports_no_median() -> None:
    """3,237 rows predate the field; a median over an empty set would be a fabricated match."""
    assert summarize_pool([_exp("AAA")], []).median_n_bars is None
