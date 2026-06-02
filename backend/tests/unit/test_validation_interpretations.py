"""_interpret: plain-English thresholds for PBO, deflated Sharpe, and parameter stability.
Cover every branch of every metric — the thresholds drive a recruiting-facing UI verdict
and silently shifting them would mislead readers."""

from app.validation.engine import _interpret


def _by_metric(items: list[object]) -> dict[str, object]:
    return {item.metric: item for item in items}  # type: ignore[attr-defined]


def test_pbo_low_is_good() -> None:
    item = _by_metric(_interpret(pbo=0.1, dsr=0.5, stability=0.8))["pbo"]
    assert item.verdict == "good"  # type: ignore[attr-defined]
    assert "low" in item.message.lower()  # type: ignore[attr-defined]


def test_pbo_moderate_is_warning() -> None:
    item = _by_metric(_interpret(pbo=0.35, dsr=0.5, stability=0.8))["pbo"]
    assert item.verdict == "warning"  # type: ignore[attr-defined]
    assert "moderate" in item.message.lower()  # type: ignore[attr-defined]


def test_pbo_high_is_bad() -> None:
    item = _by_metric(_interpret(pbo=0.85, dsr=0.5, stability=0.8))["pbo"]
    assert item.verdict == "bad"  # type: ignore[attr-defined]
    assert "high" in item.message.lower()  # type: ignore[attr-defined]


def test_deflated_sharpe_positive_is_good() -> None:
    item = _by_metric(_interpret(pbo=0.1, dsr=0.5, stability=0.8))["deflated_sharpe"]
    assert item.verdict == "good"  # type: ignore[attr-defined]


def test_deflated_sharpe_non_positive_is_bad() -> None:
    item = _by_metric(_interpret(pbo=0.1, dsr=-0.2, stability=0.8))["deflated_sharpe"]
    assert item.verdict == "bad"  # type: ignore[attr-defined]
    assert "luck" in item.message.lower()  # type: ignore[attr-defined]


def test_stability_high_is_good() -> None:
    item = _by_metric(_interpret(pbo=0.1, dsr=0.5, stability=0.85))["parameter_stability_score"]
    assert item.verdict == "good"  # type: ignore[attr-defined]


def test_stability_moderate_is_warning() -> None:
    item = _by_metric(_interpret(pbo=0.1, dsr=0.5, stability=0.5))["parameter_stability_score"]
    assert item.verdict == "warning"  # type: ignore[attr-defined]


def test_stability_low_is_bad() -> None:
    item = _by_metric(_interpret(pbo=0.1, dsr=0.5, stability=0.3))["parameter_stability_score"]
    assert item.verdict == "bad"  # type: ignore[attr-defined]
    assert "fragility" in item.message.lower()  # type: ignore[attr-defined]
