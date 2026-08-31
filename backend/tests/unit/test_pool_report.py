"""ADR-033 reporting: the honest state of the research programme in one object. Answers the
questions a session actually asks — how much has been searched, how many graduates there are, how
many are distinguishable from best-of-N selection luck, which ones came closest, and whether the
survivors are outperforming the non-survivors in the forward book."""

from datetime import UTC, datetime

import numpy as np
import pytest

from app.research.lab.calibration import NullCalibration
from app.research.lab.experiment import Experiment, Graduate, Trial
from app.research.lab.gate import GateConfig, GateResult
from app.research.lab.paper import PaperPosition
from app.research.lab.pool_report import (
    compare_search_windows,
    compare_with_null,
    summarize_pool,
    window_experiment_symbols,
)

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
    first_a = _exp("A")
    latest_a = _exp("A", holdout_sharpe=0.5).model_copy(update={"lifetime_trials": 20})
    report = summarize_pool([first_a, _exp("B"), latest_a], [])
    assert report.n_experiments == 3
    assert report.n_symbols == 2
    # A's 10 trials are already carried into its cumulative 20; only the maximum per-symbol
    # denominator is counted. Summing rows would double-count A's first 10 and report 40.
    assert report.n_trials == 30


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


# --- ADR-051: run the comparison in code, not by hand in a session ---


def _null(
    mode: str,
    *,
    walk_forward: list[float],
    purged_cv: list[float],
    search_version: str = "fam-a",
    n_bars: int = 5400,
) -> NullCalibration:
    return NullCalibration(
        n_symbols=len(walk_forward),
        n_graduates=0,
        false_graduation_rate=0.0,
        n_clear_deflation_bar=0,
        deflation_bar=2.1,
        max_deflated_sharpe=-0.3,
        max_holdout_sharpe=None,
        graduates=[],
        holdout_years=[4.3] * len(walk_forward),
        n_bars=[n_bars] * len(walk_forward),
        walk_forward_oos_sharpes=walk_forward,
        purged_cv_oos_sharpes=purged_cv,
        errors={},
        gate_config_version="v1",
        search_config_version=search_version,
        null_mode=mode,
    )


def _pool(values: list[float]) -> list[Experiment]:
    return [
        _exp_with_diagnostics(f"S{i}", walk_forward=v, purged_cv=v, graduated=False).model_copy(
            update={"search_config_version": "fam-a", "n_bars": 5400}
        )
        for i, v in enumerate(values)
    ]


def test_the_comparison_reports_the_real_median_against_each_null() -> None:
    pool = _pool([0.5, 0.6, 0.7])
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1, 0.2, 0.3], purged_cv=[0.1, 0.2, 0.3])],
        pool,
    )

    walk = next(r for r in rows if r.statistic == "walk-forward")
    assert walk.null_mode == "iid_normal"
    assert walk.real_median == pytest.approx(0.6)
    assert walk.null_median == pytest.approx(0.2)
    assert walk.real_exceeds_null_p95 is True


def test_a_real_median_inside_the_null_does_not_separate() -> None:
    pool = _pool([0.1, 0.2, 0.3])
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("bootstrap", walk_forward=[0.5, 0.6, 0.7], purged_cv=[0.5, 0.6, 0.7])],
        pool,
    )

    assert all(row.real_exceeds_null_p95 is False for row in rows)


def test_the_comparison_refuses_to_call_a_mismatched_pair_comparable() -> None:
    """Match the identity before quoting a difference — the rule this session had to apply by hand
    against commit timestamps."""
    pool = _pool([0.5, 0.6, 0.7])
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1], search_version="fam-b")],
        pool,
    )

    assert all(row.comparable is False for row in rows)
    assert all("search family" in row.mismatch for row in rows)


def test_a_history_length_mismatch_is_also_not_comparable() -> None:
    pool = _pool([0.5, 0.6, 0.7])
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1], n_bars=3000)],
        pool,
    )

    assert all(row.comparable is False for row in rows)
    assert all("history" in row.mismatch for row in rows)


def test_nothing_to_compare_when_the_pool_carries_no_diagnostics() -> None:
    report = summarize_pool([_exp("AAA")], [])
    assert (
        compare_with_null(report, [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1])]) == []
    )


# --- ADR-054: how often the two Sharpe statistics reach the same verdict ---


def _exp_with_probability(
    symbol: str, *, deflated_sharpe: float, probability: float | None, dsr_min: float = 0.0
) -> Experiment:
    return Experiment(
        symbol=symbol,
        strategy_names=["sma"],
        gate_config=GateConfig(dsr_min=dsr_min),
        trials=[
            Trial(
                strategy_name="sma",
                parameters={"fast": 5, "slow": 20},
                observed_sharpe=1.0,
                deflated_sharpe=deflated_sharpe,
                pbo=0.1,
                parameter_stability_score=0.8,
                deflated_sharpe_probability=probability,
            )
        ],
        lifetime_trials=10,
    )


def test_report_counts_where_the_margin_and_the_probability_disagree() -> None:
    """ADR-054's payoff: the gate uses the MARGIN, the paper's statistic is the PROBABILITY, and
    a case for switching needs their disagreement measured on real trials rather than assumed."""
    experiments = [
        _exp_with_probability("AAA", deflated_sharpe=0.4, probability=0.99),  # both pass
        _exp_with_probability("BBB", deflated_sharpe=0.4, probability=0.10),  # margin only
        _exp_with_probability("CCC", deflated_sharpe=-0.4, probability=0.99),  # probability only
        _exp_with_probability("DDD", deflated_sharpe=-0.4, probability=0.10),  # neither
    ]
    report = summarize_pool(experiments, [])

    agreement = report.statistic_agreement
    assert agreement is not None
    assert agreement.n == 4
    assert agreement.probability_reference == pytest.approx(0.95)
    assert (agreement.both_pass, agreement.both_fail) == (1, 1)
    assert (agreement.margin_only, agreement.probability_only) == (1, 1)
    assert agreement.median_probability == pytest.approx(0.545)


def test_the_margin_verdict_uses_each_experiment_own_recorded_threshold() -> None:
    """`dsr_min` is versioned per experiment (ADR-015/016). Judging a whole pool against today's
    default would misreport rows that were searched under a different rubric."""
    experiments = [
        _exp_with_probability("AAA", deflated_sharpe=0.4, probability=0.99, dsr_min=0.0),
        _exp_with_probability("BBB", deflated_sharpe=0.4, probability=0.99, dsr_min=0.9),
    ]
    report = summarize_pool(experiments, [])

    assert report.statistic_agreement is not None
    assert report.statistic_agreement.both_pass == 1
    assert report.statistic_agreement.probability_only == 1


def test_finalists_without_a_probability_are_left_out_rather_than_counted_as_failures() -> None:
    """The 3,237 rows written before ADR-054 carry None. Counting them as 'probability fails'
    would manufacture a disagreement rate out of rows that were never measured."""
    experiments = [
        _exp_with_probability("AAA", deflated_sharpe=0.4, probability=0.99),
        _exp_with_probability("BBB", deflated_sharpe=0.4, probability=None),
    ]
    report = summarize_pool(experiments, [])

    assert report.statistic_agreement is not None
    assert report.statistic_agreement.n == 1
    assert report.statistic_agreement.both_pass == 1


def test_a_pool_with_no_probability_at_all_reports_no_agreement() -> None:
    report = summarize_pool([_exp("AAA", holdout_sharpe=1.0)], [])
    assert report.statistic_agreement is None


def test_the_probability_reference_level_is_the_caller_s_to_state() -> None:
    """It is a stated reading level, not a threshold anything gates on — so it must be visible
    and movable, and the report must say which one produced its counts."""
    experiments = [_exp_with_probability("AAA", deflated_sharpe=0.4, probability=0.80)]

    strict = summarize_pool(experiments, [], probability_reference=0.95)
    lenient = summarize_pool(experiments, [], probability_reference=0.50)

    assert strict.statistic_agreement is not None and strict.statistic_agreement.margin_only == 1
    assert lenient.statistic_agreement is not None and lenient.statistic_agreement.both_pass == 1
    assert lenient.statistic_agreement.probability_reference == pytest.approx(0.50)


def _multi_family_exp(
    symbol: str,
    sharpes: dict[str, float],
    *,
    n_bars: int | None = None,
) -> Experiment:
    """An experiment carrying one finalist per strategy family, as a real search writes it."""
    trials = [
        Trial(
            strategy_name=name,
            parameters={},
            observed_sharpe=sharpe,
            # DSR ordering follows the Sharpe ordering within one experiment: the whole-search
            # haircut is common to every family in it.
            deflated_sharpe=sharpe - 0.5,
            pbo=0.1,
            parameter_stability_score=0.8,
        )
        for name, sharpe in sharpes.items()
    ]
    return Experiment(
        symbol=symbol,
        strategy_names=list(sharpes),
        gate_config=GateConfig(),
        trials=trials,
        lifetime_trials=10,
        n_bars=n_bars,
    )


def test_the_report_states_how_far_ahead_the_winning_family_was() -> None:
    """ADR-060. A pool row records `best_strategy_name` with no indication of how far ahead of the
    alternatives it was, while the leaderboard and the capture reading both treat it as
    informative."""
    report = summarize_pool(
        [
            _multi_family_exp("A", {"sma": 1.0, "mean_reversion": 0.9}, n_bars=5400),
            _multi_family_exp("B", {"sma": 0.6, "mean_reversion": 0.8}, n_bars=5400),
        ],
        [],
    )

    separation = report.category_separation
    assert separation is not None
    assert separation.medians == {
        "Trend": pytest.approx(0.8),
        "Mean Reversion": pytest.approx(0.85),
    }
    assert separation.winner_shares == {
        "Trend": pytest.approx(0.5),
        "Mean Reversion": pytest.approx(0.5),
    }
    assert separation.median_gap == pytest.approx(0.15)


def test_a_gap_inside_one_standard_error_is_reported_as_not_separable() -> None:
    """The verdict is a comparison of scales — Lo (2002)'s Sharpe standard error at the pool's own
    history — not an invented cutoff."""
    close = summarize_pool(
        [_multi_family_exp(s, {"sma": 1.0, "mean_reversion": 0.98}, n_bars=5400) for s in "ABC"],
        [],
    )
    assert close.category_separation is not None
    assert close.category_separation.standard_error is not None
    assert close.category_separation.median_gap < close.category_separation.standard_error
    assert close.category_separation.separable is False

    clear = summarize_pool(
        [_multi_family_exp(s, {"sma": 2.0, "mean_reversion": 0.5}, n_bars=5400) for s in "ABC"],
        [],
    )
    assert clear.category_separation is not None
    assert clear.category_separation.separable is True


def test_a_pool_that_does_not_state_its_history_reports_no_verdict() -> None:
    """None, never False: every row written before ADR-052's amendment lacks `n_bars`, and 'not
    measured' must not render as 'not separable'."""
    report = summarize_pool([_multi_family_exp("A", {"sma": 1.0, "mean_reversion": 0.5})], [])
    assert report.category_separation is not None
    assert report.category_separation.standard_error is None
    assert report.category_separation.separable is None


def test_a_pool_with_no_trials_has_no_separation_to_report() -> None:
    report = summarize_pool([], [])
    assert report.category_separation is None


# --- ADR-064: compare the null against the experiments whose history actually matches it ---


def _pool_with_history(pairs: list[tuple[float, int | None]]) -> list[Experiment]:
    return [
        _exp_with_diagnostics(f"H{i}", walk_forward=v, purged_cv=v, graduated=False).model_copy(
            update={"search_config_version": "fam-a", "n_bars": bars}
        )
        for i, (v, bars) in enumerate(pairs)
    ]


def test_a_history_difference_inside_the_tolerance_is_still_comparable() -> None:
    """The pool's median grows a bar per trading day; exact equality could never be satisfied."""
    pool = _pool_with_history([(0.5, 5444)] * 40)
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1], n_bars=5400)],
        pool,
    )

    assert all(row.comparable for row in rows)
    assert all(row.matched_n == 40 for row in rows)


def test_the_real_side_is_computed_only_from_the_matched_experiments() -> None:
    """A bimodal pool (ADR-063) must not be summarized as one population."""
    pool = _pool_with_history([(0.2, 5400)] * 40 + [(0.9, 7400)] * 40)
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1], n_bars=7400)],
        pool,
    )

    walk = next(r for r in rows if r.statistic == "walk-forward")
    assert walk.matched_n == 40
    assert walk.matched_n_bars == 7400
    assert walk.real_median == pytest.approx(0.9)


def test_history_far_outside_the_tolerance_is_refused() -> None:
    pool = _pool_with_history([(0.5, 5400)] * 40)
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1], n_bars=3000)],
        pool,
    )

    assert all(row.comparable is False for row in rows)
    assert all("history" in row.mismatch for row in rows)


def test_a_matched_subset_too_small_to_measure_is_refused() -> None:
    pool = _pool_with_history([(0.5, 5400)] * 5 + [(0.5, 9000)] * 40)
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1], n_bars=5400)],
        pool,
    )

    assert all(row.comparable is False for row in rows)
    assert all("matched" in row.mismatch for row in rows)
    assert all(row.matched_n == 5 for row in rows)


def test_a_matched_subset_with_too_few_measured_diagnostics_is_refused() -> None:
    """The median's sample is `real_n`, not every history-matched experiment (FINDING-009)."""
    pool = [
        _exp_with_diagnostics(
            f"H{i}",
            walk_forward=0.5 if i < 5 else None,
            purged_cv=0.5 if i < 5 else None,
            graduated=False,
        ).model_copy(update={"search_config_version": "fam-a", "n_bars": 5400})
        for i in range(40)
    ]
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1], n_bars=5400)],
        pool,
    )

    assert all(row.comparable is False for row in rows)
    assert all(row.real_n == 5 for row in rows)
    assert all("diagnostics" in row.mismatch for row in rows)


def test_pool_wide_fallback_cannot_satisfy_the_matched_diagnostic_minimum() -> None:
    matched_missing = [
        _exp_with_diagnostics(
            f"M{i}", walk_forward=None, purged_cv=None, graduated=False
        ).model_copy(update={"search_config_version": "fam-a", "n_bars": 5400})
        for i in range(40)
    ]
    unmatched_measured = _pool_with_history([(0.9, 7400)] * 40)
    pool = matched_missing + unmatched_measured
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1], n_bars=5400)],
        pool,
    )

    assert all(row.comparable is False for row in rows)
    assert all("0 matched diagnostics" in row.mismatch for row in rows)


def test_experiments_without_a_history_are_not_assumed_to_match() -> None:
    pool = _pool_with_history([(0.5, None)] * 40 + [(0.9, 5400)] * 40)
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1], n_bars=5400)],
        pool,
    )

    walk = next(r for r in rows if r.statistic == "walk-forward")
    assert walk.matched_n == 40
    assert walk.real_median == pytest.approx(0.9)


def test_the_family_check_reads_the_matched_subset_not_the_whole_pool() -> None:
    """ADR-064 amendment: legacy rows outside the compared subset cannot refuse a comparison
    nobody made with them. Measured on the live pool: all 2,427 history-matched rows carry the
    null's own fingerprint while 227 legacy rows carry none."""
    modern = [
        e.model_copy(update={"search_config_version": "fam-a", "n_bars": 5400})
        for e in _pool_with_history([(0.5, 5400)] * 40)
    ]
    legacy = [
        e.model_copy(update={"search_config_version": "legacy-unspecified", "n_bars": None})
        for e in _pool_with_history([(0.5, None)] * 10)
    ]
    pool = modern + legacy
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1], n_bars=5400)],
        pool,
    )

    assert all(row.comparable for row in rows)
    assert all(row.matched_n == 40 for row in rows)


def test_a_matched_subset_spanning_two_families_is_still_refused() -> None:
    pool = [
        e.model_copy(update={"search_config_version": fam, "n_bars": 5400})
        for fam in ("fam-a", "fam-b")
        for e in _pool_with_history([(0.5, 5400)] * 20)
    ]
    rows = compare_with_null(
        summarize_pool(pool, []),
        [_null("iid_normal", walk_forward=[0.1], purged_cv=[0.1], n_bars=5400)],
        pool,
    )

    assert all(row.comparable is False for row in rows)
    assert all("search family" in row.mismatch for row in rows)


# --- ADR-068: the same comparison, with each side's own drift taken out ---


def _pool_with_hold(pairs: list[tuple[float, float]]) -> list[Experiment]:
    return [
        _exp_with_diagnostics(f"S{i}", walk_forward=oos, purged_cv=oos, graduated=False).model_copy(
            update={
                "search_config_version": "fam-a",
                "n_bars": 5400,
                "walk_forward_hold_sharpe": hold,
            }
        )
        for i, (oos, hold) in enumerate(pairs)
    ]


def test_the_excess_row_takes_each_sides_own_drift_out() -> None:
    pool = _pool_with_hold([(0.5, 0.5), (0.6, 0.55), (0.7, 0.6)])
    null = _null("iid_normal", walk_forward=[0.4, 0.5, 0.6], purged_cv=[0.1, 0.2, 0.3]).model_copy(
        update={"walk_forward_hold_sharpes": [0.4, 0.4, 0.4]}
    )

    rows = compare_with_null(summarize_pool(pool, []), [null], pool)

    excess = next(r for r in rows if r.statistic == "walk-forward excess")
    assert excess.real_median == pytest.approx(0.05)
    assert excess.null_median == pytest.approx(0.1)
    assert excess.real_n == 3
    assert excess.null_n == 3


def test_the_raw_row_survives_the_excess_row() -> None:
    """ADR-068 decision 5: a published verdict is not restated on a new statistic in place."""
    pool = _pool_with_hold([(0.5, 0.5), (0.6, 0.55), (0.7, 0.6)])
    null = _null("iid_normal", walk_forward=[0.4, 0.5, 0.6], purged_cv=[0.1, 0.2, 0.3]).model_copy(
        update={"walk_forward_hold_sharpes": [0.4, 0.4, 0.4]}
    )

    rows = compare_with_null(summarize_pool(pool, []), [null], pool)

    assert [r.statistic for r in rows].count("walk-forward") == 1
    assert next(r for r in rows if r.statistic == "walk-forward").real_median == pytest.approx(0.6)


def test_a_drift_only_lead_over_the_null_disappears_in_the_excess() -> None:
    """The confound ADR-068 measured: a pool can lead a null on the raw statistic purely because
    its symbols drifted harder, and lead it by nothing once both are read against their own."""
    pool = _pool_with_hold([(0.9, 0.9), (1.0, 1.0), (1.1, 1.1)])
    null = _null("iid_normal", walk_forward=[0.2, 0.3, 0.4], purged_cv=[0.1, 0.2, 0.3]).model_copy(
        update={"walk_forward_hold_sharpes": [0.2, 0.3, 0.4]}
    )

    rows = compare_with_null(summarize_pool(pool, []), [null], pool)

    assert next(r for r in rows if r.statistic == "walk-forward").real_exceeds_null_p95 is True
    excess = next(r for r in rows if r.statistic == "walk-forward excess")
    assert excess.real_median == pytest.approx(0.0)
    assert excess.real_exceeds_null_p95 is False


def test_no_excess_row_when_the_null_never_measured_its_own_hold() -> None:
    """ADR-067: every artifact on disk predates the benchmark; absent is not an excess of zero."""
    pool = _pool_with_hold([(0.5, 0.5), (0.6, 0.55), (0.7, 0.6)])
    null = _null("iid_normal", walk_forward=[0.4, 0.5, 0.6], purged_cv=[0.1, 0.2, 0.3])

    rows = compare_with_null(summarize_pool(pool, []), [null], pool)

    assert all(r.statistic != "walk-forward excess" for r in rows)


def test_no_excess_row_when_the_pool_never_measured_its_own_hold() -> None:
    pool = _pool([0.5, 0.6, 0.7])
    null = _null("iid_normal", walk_forward=[0.4, 0.5, 0.6], purged_cv=[0.1, 0.2, 0.3]).model_copy(
        update={"walk_forward_hold_sharpes": [0.4, 0.4, 0.4]}
    )

    rows = compare_with_null(summarize_pool(pool, []), [null], pool)

    assert all(r.statistic != "walk-forward excess" for r in rows)


def test_a_null_whose_two_distributions_do_not_pair_up_is_refused() -> None:
    """They are paired per searched symbol; unequal lengths mean the pairing is unknown, and
    differencing them anyway would invent a measurement."""
    pool = _pool_with_hold([(0.5, 0.5), (0.6, 0.55), (0.7, 0.6)])
    null = _null("iid_normal", walk_forward=[0.4, 0.5, 0.6], purged_cv=[0.1, 0.2, 0.3]).model_copy(
        update={"walk_forward_hold_sharpes": [0.4, 0.4]}
    )

    rows = compare_with_null(summarize_pool(pool, []), [null], pool)

    assert all(r.statistic != "walk-forward excess" for r in rows)


# --- ADR-072: the centered statistic is read against a two-sided band ---


def test_the_excess_row_reports_the_null_lower_edge_too() -> None:
    pool = _pool_with_hold([(0.5, 0.5), (0.6, 0.55), (0.7, 0.6)])
    null = _null(
        "iid_normal", walk_forward=[0.4, 0.5, 0.6, 0.7], purged_cv=[0.1, 0.2, 0.3, 0.4]
    ).model_copy(update={"walk_forward_hold_sharpes": [0.4, 0.4, 0.4, 0.4]})

    rows = compare_with_null(summarize_pool(pool, []), [null], pool)

    excess = next(r for r in rows if r.statistic == "walk-forward excess")
    assert excess.null_p5 == pytest.approx(np.percentile([0.0, 0.1, 0.2, 0.3], 5))
    assert excess.null_p5 < excess.null_p95


def test_a_real_excess_under_the_null_band_separates_below() -> None:
    """The result ADR-072 was written for: with drift out of both sides, a real median BELOW the
    null is as interpretable as one above, and the one-sided rule printed it as neutral."""
    pool = _pool_with_hold([(0.1, 0.9), (0.2, 0.9), (0.3, 0.9)])
    null = _null("iid_normal", walk_forward=[0.4, 0.5, 0.6], purged_cv=[0.1, 0.2, 0.3]).model_copy(
        update={"walk_forward_hold_sharpes": [0.4, 0.5, 0.6]}
    )

    rows = compare_with_null(summarize_pool(pool, []), [null], pool)

    excess = next(r for r in rows if r.statistic == "walk-forward excess")
    assert excess.real_median == pytest.approx(-0.7)
    assert excess.real_below_null_p5 is True
    assert excess.real_exceeds_null_p95 is False


def test_an_excess_inside_the_band_separates_in_neither_direction() -> None:
    pool = _pool_with_hold([(0.5, 0.5), (0.6, 0.55), (0.7, 0.6)])
    null = _null("iid_normal", walk_forward=[0.0, 0.5, 1.0], purged_cv=[0.1, 0.2, 0.3]).model_copy(
        update={"walk_forward_hold_sharpes": [0.5, 0.5, 0.5]}
    )

    rows = compare_with_null(summarize_pool(pool, []), [null], pool)

    excess = next(r for r in rows if r.statistic == "walk-forward excess")
    assert excess.real_below_null_p5 is False
    assert excess.real_exceeds_null_p95 is False


def test_the_raw_row_is_never_read_below_the_null() -> None:
    """ADR-068 measured that the raw statistic's level IS the series' own drift, so a real median
    under the null says the median pool symbol drifted less than SPY — not that the search is
    worse. ADR-072 keeps that row one-sided."""
    pool = _pool([0.1, 0.2, 0.3])
    null = _null("bootstrap", walk_forward=[0.9, 1.0, 1.1], purged_cv=[0.9, 1.0, 1.1])

    rows = compare_with_null(summarize_pool(pool, []), [null], pool)

    raw = [r for r in rows if r.statistic != "walk-forward excess"]
    assert raw
    assert all(r.real_below_null_p5 is False for r in raw)
    assert all(r.real_median < r.null_p5 for r in raw)


# --- ADR-074: the ADR-063 window change, read paired within symbol ---


def _windowed(
    symbol: str,
    *,
    n_bars: int,
    walk_forward: float,
    observed: float = 1.0,
    hold: float | None = None,
    strategy: str = "sma",
) -> Experiment:
    experiment = _exp(symbol, strategy=strategy)
    trial = experiment.trials[0].model_copy(
        update={
            "walk_forward_oos_sharpe": walk_forward,
            "observed_sharpe": observed,
            "strategy_name": strategy,
        }
    )
    return experiment.model_copy(
        update={
            "trials": [trial],
            "n_bars": n_bars,
            "search_config_version": "fam-a",
            "walk_forward_hold_sharpe": hold,
        }
    )


def _both_windows(symbol: str, short: float, long_: float, **kwargs: float) -> list[Experiment]:
    return [
        _windowed(symbol, n_bars=5450, walk_forward=short, **kwargs),
        _windowed(symbol, n_bars=9200, walk_forward=long_, **kwargs),
    ]


def test_the_window_change_is_paired_within_each_symbol() -> None:
    pool = (
        _both_windows("AAA", 0.60, 0.50)
        + _both_windows("BBB", 0.40, 0.35)
        + _both_windows("CCC", 0.80, 0.90)
    )

    comparison = compare_search_windows(pool)

    assert comparison is not None
    assert comparison.n_symbols == 3
    assert comparison.oos_delta_median == pytest.approx(-0.05)
    assert comparison.short_n_bars == 5450
    assert comparison.long_n_bars == 9200


def test_a_symbol_searched_at_only_one_window_is_not_paired() -> None:
    """A young listing never reaches the long window, so it has nothing to difference."""
    pool = [
        *_both_windows("AAA", 0.6, 0.5),
        _windowed("YOUNG", n_bars=1200, walk_forward=0.9),
        _windowed("YOUNG", n_bars=1400, walk_forward=0.2),
    ]

    comparison = compare_search_windows(pool)

    assert comparison is not None
    assert comparison.n_symbols == 1


def test_repeat_runs_at_the_same_window_are_collapsed_to_that_symbol_median() -> None:
    """The daily discovery re-searches a symbol several times per window; a symbol with five short
    runs and one long run must not outweigh a symbol with one of each."""
    pool = [
        _windowed("AAA", n_bars=5450, walk_forward=0.2),
        _windowed("AAA", n_bars=5460, walk_forward=0.6),
        _windowed("AAA", n_bars=5470, walk_forward=1.0),
        _windowed("AAA", n_bars=9200, walk_forward=0.4),
    ]

    comparison = compare_search_windows(pool)

    assert comparison is not None
    assert comparison.n_symbols == 1
    assert comparison.oos_delta_median == pytest.approx(-0.2)


def test_the_pairing_never_crosses_two_search_families() -> None:
    """ADR-052/064: a difference between two families is not a finding about a window. A symbol
    whose windows were searched by different families has no pair, even though it has both."""
    crossed = _both_windows("AAA", 0.6, 0.5)
    crossed[1] = crossed[1].model_copy(update={"search_config_version": "fam-b"})

    assert compare_search_windows(crossed) is None
    assert compare_search_windows(crossed + _both_windows("BBB", 0.9, 0.1)) is not None


def test_the_drift_controlled_delta_is_absent_until_both_windows_carry_the_benchmark() -> None:
    """ADR-068/074: the pre-ADR-063 rows predate the paired benchmark, so the excess delta is not
    measured — never zero."""
    pool = _both_windows("AAA", 0.6, 0.5) + _both_windows("BBB", 0.4, 0.3)
    pool[1] = pool[1].model_copy(update={"walk_forward_hold_sharpe": 0.5})

    comparison = compare_search_windows(pool)

    assert comparison is not None
    assert comparison.excess_delta_median is None
    assert comparison.excess_n == 0


def test_the_drift_controlled_delta_is_measured_where_both_windows_carry_it() -> None:
    pool = [
        _windowed("AAA", n_bars=5450, walk_forward=0.60, hold=0.50),
        _windowed("AAA", n_bars=9200, walk_forward=0.55, hold=0.60),
        _windowed("BBB", n_bars=5450, walk_forward=0.40, hold=0.30),
        _windowed("BBB", n_bars=9200, walk_forward=0.30, hold=0.30),
    ]

    comparison = compare_search_windows(pool)

    assert comparison is not None
    assert comparison.excess_n == 2
    # AAA: (0.55-0.60) - (0.60-0.50) = -0.15 ; BBB: (0.30-0.30) - (0.40-0.30) = -0.10
    assert comparison.excess_delta_median == pytest.approx(-0.125)


def test_the_delta_carries_an_interval_that_can_include_zero() -> None:
    """ADR-070: a point estimate with no interval is what made two criteria unreadable."""
    pool = [e for i in range(20) for e in _both_windows(f"S{i}", 0.5 + 0.01 * i, 0.5 - 0.01 * i)]

    comparison = compare_search_windows(pool)

    assert comparison is not None
    assert comparison.oos_delta_ci_low < comparison.oos_delta_median < comparison.oos_delta_ci_high


def test_how_often_the_longer_window_changes_the_finalist() -> None:
    pool = [
        _windowed("AAA", n_bars=5450, walk_forward=0.6, strategy="sma"),
        _windowed("AAA", n_bars=9200, walk_forward=0.5, strategy="rsi"),
        _windowed("BBB", n_bars=5450, walk_forward=0.4, strategy="sma"),
        _windowed("BBB", n_bars=9200, walk_forward=0.3, strategy="sma"),
    ]

    comparison = compare_search_windows(pool)

    assert comparison is not None
    assert comparison.n_finalist_changed == 1


def test_a_pool_with_no_symbol_at_both_windows_has_nothing_to_compare() -> None:
    assert compare_search_windows([_windowed("AAA", n_bars=5450, walk_forward=0.6)]) is None


# --- ADR-074 decision 3: choosing the sample for the pre-registered re-search ---


def test_the_research_sample_is_symbols_whose_long_window_carries_the_benchmark() -> None:
    """Only the long side of ADR-068's benchmark exists in the pool today, so the re-search has to
    supply the short side for symbols that already have the long one."""
    pool = [
        _windowed("HAS", n_bars=9200, walk_forward=0.5, hold=0.6),
        _windowed("LACKS", n_bars=9200, walk_forward=0.5),
        _windowed("SHORT_ONLY", n_bars=5450, walk_forward=0.5, hold=0.6),
    ]

    assert window_experiment_symbols(pool, 10) == ["HAS"]


def test_a_symbol_that_already_has_both_sides_is_not_re_searched() -> None:
    pool = [
        _windowed("DONE", n_bars=9200, walk_forward=0.5, hold=0.6),
        _windowed("DONE", n_bars=5450, walk_forward=0.5, hold=0.5),
        _windowed("TODO", n_bars=9200, walk_forward=0.5, hold=0.6),
    ]

    assert window_experiment_symbols(pool, 10) == ["TODO"]


def test_the_sample_is_deterministic_and_capped() -> None:
    pool = [_windowed(f"S{i:02d}", n_bars=9200, walk_forward=0.5, hold=0.6) for i in range(40)]

    first = window_experiment_symbols(pool, 8)
    assert len(first) == 8
    assert first == window_experiment_symbols(pool, 8)
    assert set(first) <= {f"S{i:02d}" for i in range(40)}


def test_no_candidate_is_an_empty_sample_not_an_error() -> None:
    assert window_experiment_symbols([_windowed("A", n_bars=5450, walk_forward=0.5)], 5) == []
