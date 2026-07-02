"""'Sane fundamentals' screen (ADR-017): a tunable, conservative filter — unverifiable metrics
fail, so the lab never trades a company whose fundamentals it can't confirm."""

from app.data.fundamentals import (
    FundamentalCriteria,
    FundamentalScreen,
    FundamentalSnapshot,
    screen_fundamentals,
)


def _snap(growth: float | None, net_margin: float | None) -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol="AAPL",
        cik=320193,
        entity_name="Apple Inc.",
        fiscal_year=2024,
        form="10-K",
        accession_number="a",
        source_url="http://x",
        revenue=400_000,
        revenue_growth_yoy=growth,
        net_margin=net_margin,
    )


def test_healthy_fundamentals_pass() -> None:
    screen = screen_fundamentals(_snap(0.12, 0.25), FundamentalCriteria())
    assert isinstance(screen, FundamentalScreen)
    assert screen.passed is True
    assert screen.reasons == []


def test_negative_growth_fails_with_reason() -> None:
    screen = screen_fundamentals(_snap(-0.05, 0.25), FundamentalCriteria())
    assert screen.passed is False
    assert any("revenue growth" in r for r in screen.reasons)


def test_negative_margin_fails() -> None:
    screen = screen_fundamentals(_snap(0.12, -0.10), FundamentalCriteria())
    assert screen.passed is False
    assert any("net margin" in r for r in screen.reasons)


def test_unverifiable_metric_fails_conservatively() -> None:
    screen = screen_fundamentals(_snap(None, None), FundamentalCriteria())
    assert screen.passed is False
    assert len(screen.reasons) == 2  # both unavailable


def test_none_threshold_skips_the_check() -> None:
    # Only screen on margin; ignore growth entirely.
    criteria = FundamentalCriteria(min_revenue_growth_yoy=None, min_net_margin=0.0)
    screen = screen_fundamentals(_snap(-0.9, 0.3), criteria)
    assert screen.passed is True
