"""Offline conformance of ADR418's one final evaluator (ADR424)."""

import importlib
import json
import os
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.data.models import PriceBar

REPO = Path(__file__).resolve().parents[3]
OPEN = datetime(2027, 2, 11, tzinfo=UTC)
END = datetime(2027, 2, 12, tzinfo=UTC)


def api():
    return importlib.import_module("app.research.cross_sectional.prospective_portfolio")


def prepared():
    return api().prepare(REPO)


def fake_source(plan, *, rising=False, fail=None, mutation=None):
    cohort = plan.cohort
    dates = cohort["geometry"]["session_labels"]
    selected = set(cohort["selection"]["selected"])
    calls = []

    def provider(symbol, start, end):
        calls.append((symbol, start, end))
        if symbol == fail:
            raise OSError("synthetic unavailable")
        bars = []
        for i, label in enumerate(dates):
            price = Decimal(100 + i if rising and symbol in selected else 100)
            bars.append(
                PriceBar(
                    symbol=symbol,
                    timestamp_utc=datetime.fromisoformat(label).replace(tzinfo=UTC),
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=100,
                    adj_factor=Decimal(1),
                    source="yfinance",
                )
            )
        if mutation:
            mutation(bars)
        return bars

    return provider, calls


def execute(tmp_path, *, rising=False, fail=None, mutation=None, clock=lambda: OPEN):
    plan = prepared()
    provider, calls = fake_source(plan, rising=rising, fail=fail, mutation=mutation)
    result = api().evaluate_synthetic(
        plan, tmp_path / "attempt", provider_factory=lambda: provider, clock=clock
    )
    return result, calls, plan


def test_preflight_binds_original_cohort_inputs_publications_and_policy():
    plan = prepared()
    assert len(plan.cohort["selection"]["eligible"]) == 412
    assert len(plan.cohort["selection"]["selected"]) == 83
    assert len(plan.cohort["geometry"]["session_labels"]) == 64
    assert plan.identity["git_revision"]
    assert plan.identity["policy_revision"] == "7048c785fd34fa0fc5b8357fc711929c7fe48fb9"
    assert plan.identity["installed_distributions"]
    assert plan.identity["actual_application_sha256"]
    assert plan.identity["policy_sha256"]


@pytest.mark.parametrize(
    "now",
    [OPEN - timedelta(microseconds=1), END, END + timedelta(days=1), OPEN.replace(tzinfo=None)],
)
def test_window_refuses_before_root_and_provider(tmp_path, now):
    plan = prepared()
    with pytest.raises(ValueError, match=r"window|aware|EXPIRED"):
        api().evaluate_synthetic(
            plan,
            tmp_path / "attempt",
            provider_factory=lambda: pytest.fail("provider constructed"),
            clock=lambda: now,
        )
    assert not (tmp_path / "attempt").exists()


@pytest.mark.parametrize("kind", ["directory", "file", "symlink"])
def test_occupied_root_never_constructs_provider(tmp_path, kind):
    plan = prepared()
    root = tmp_path / "attempt"
    if kind == "directory":
        root.mkdir()
    elif kind == "file":
        root.write_text("occupied")
    else:
        root.symlink_to(tmp_path / "missing")
    with pytest.raises(FileExistsError):
        api().evaluate_synthetic(
            plan, root, provider_factory=lambda: pytest.fail("constructed"), clock=lambda: OPEN
        )


def test_synthetic_api_forbids_registered_root():
    plan = prepared()
    with pytest.raises(ValueError, match="registered"):
        api().evaluate_synthetic(
            plan,
            Path(plan.cohort["source"]["attempt_root"]),
            provider_factory=lambda: pytest.fail("constructed"),
            clock=lambda: OPEN,
        )


def test_complete_413_flat_sources_fail_after_cost_with_full_provenance(tmp_path):
    result, calls, plan = execute(tmp_path)
    assert result["status"] == "COMPLETE"
    assert result["screen_passed"] is False
    assert [c[0] for c in calls] == [*plan.cohort["selection"]["eligible"], "SPY"]
    assert len(calls) == 413
    assert all(c[1:] == (datetime(2026, 11, 9, tzinfo=UTC), OPEN) for c in calls)
    account = result["accounts"]["top_quintile"]
    assert account["net_return"] == pytest.approx(float(Fraction(999, 1001) - 1))
    assert account["turnover"] == pytest.approx(float(Fraction(2000, 1001)))
    assert result["net_excess"]["SPY"] == 0
    assert result["gate_status"] == "NOT MEASURED"
    root = tmp_path / "attempt"
    assert len(list(root.glob("source-*.json"))) == 413
    assert len(list(root.glob("quality-*.json"))) == 413
    assert len(list(root.glob("evidence-*.json"))) == 413
    report = json.loads((root / "quality-0000.json").read_text())
    assert any(i["check"] == "survivorship_risk" for i in report["issues"])
    evidence = json.loads((root / "evidence-0000.json").read_text())
    assert evidence["quality_report"] == report
    assert json.loads((root / "result.json").read_text()) == result


def test_complete_selected_outperformance_passes_strict_three_control_screen(tmp_path):
    result, _, _ = execute(tmp_path, rising=True)
    assert result["status"] == "COMPLETE" and result["screen_passed"] is True
    assert all(v > 0 for v in result["net_excess"].values())
    assert result["exposure"] == {"after_entry": 1.0, "after_liquidation": 0.0}


def test_late_symbol_source_failure_has_no_subset_economics(tmp_path):
    plan = prepared()
    failed = plan.cohort["selection"]["eligible"][-1]
    result, calls, _ = execute(tmp_path, fail=failed)
    assert result["status"] == "UNEVALUABLE"
    assert result["failed_symbol"] == failed and len(calls) == 412
    assert "accounts" not in result and "screen_passed" not in result


@pytest.mark.parametrize(
    "mutation",
    [
        lambda b: b.pop(),
        lambda b: b.append(b[-1]),
        lambda b: b.reverse(),
        lambda b: b.__setitem__(1, b[0]),
    ],
)
def test_missing_duplicate_extra_or_reordered_calendar_refuses(tmp_path, mutation):
    result, calls, _ = execute(tmp_path, mutation=mutation)
    assert result["status"] == "UNEVALUABLE" and len(calls) == 1
    assert "accounts" not in result
    assert (tmp_path / "attempt" / "quality-0000.json").exists()


def test_failed_quality_report_is_retained_before_refusal(tmp_path):
    result, _, _ = execute(tmp_path, mutation=lambda b: b.clear())
    report = json.loads((tmp_path / "attempt" / "quality-0000.json").read_text())
    assert report["passed"] is False
    assert result["status"] == "UNEVALUABLE"
    assert not (tmp_path / "attempt" / "evidence-0000.json").exists()


def test_start_is_durable_before_provider_construction_and_interruption_frozen(tmp_path):
    plan = prepared()
    root = tmp_path / "attempt"

    def factory():
        assert (root / "START.json").exists()
        raise RuntimeError("interrupted")

    with pytest.raises(RuntimeError, match="interrupted"):
        api().evaluate_synthetic(plan, root, provider_factory=factory, clock=lambda: OPEN)
    assert not (root / "result.json").exists()
    with pytest.raises(FileExistsError):
        api().evaluate_synthetic(
            plan, root, provider_factory=lambda: pytest.fail("retry"), clock=lambda: OPEN
        )


def test_request_crossing_deadline_retains_received_evidence_without_accounts(tmp_path):
    plan = prepared()
    source, calls = fake_source(plan)
    current = [OPEN]

    def provider(*args):
        bars = source(*args)
        current[0] = END
        return bars

    result = api().evaluate_synthetic(
        plan, tmp_path / "attempt", provider_factory=lambda: provider, clock=lambda: current[0]
    )
    assert result["status"] == "INCOMPLETE" and len(calls) == 1
    assert (tmp_path / "attempt" / "source-0000.json").exists()
    assert (tmp_path / "attempt" / "quality-0000.json").exists()
    assert "accounts" not in result


def test_unexpected_method_and_storage_errors_propagate(tmp_path, monkeypatch):
    plan = prepared()
    provider, _ = fake_source(plan)
    monkeypatch.setattr(
        api(), "session_prices", lambda *a: (_ for _ in ()).throw(RuntimeError("method"))
    )
    with pytest.raises(RuntimeError, match="method"):
        api().evaluate_synthetic(
            plan, tmp_path / "method", provider_factory=lambda: provider, clock=lambda: OPEN
        )
    assert not (tmp_path / "method" / "result.json").exists()
    original = api().write_json

    def broken(path, value):
        if path.name.startswith("quality-"):
            raise OSError("disk")
        return original(path, value)

    monkeypatch.setattr(api(), "write_json", broken)
    with pytest.raises(OSError, match="disk"):
        api().evaluate_synthetic(
            plan, tmp_path / "storage", provider_factory=lambda: provider, clock=lambda: OPEN
        )
    assert not (tmp_path / "storage" / "result.json").exists()


@pytest.mark.parametrize("target", ["cohort", "input", "publication", "policy"])
def test_tampered_preflight_identity_refuses_before_attempt(monkeypatch, target):
    mod = api()
    original = mod.read_bytes

    def altered(path):
        data = original(path)
        if (
            (target == "cohort" and path.name == "cohort.json.gz")
            or (target == "publication" and path.name == "seal-publication-ci.json")
            or (target == "policy" and path.name == "ohlcv.py")
            or (target == "input" and path.name == "input-fundamentals.json.gz")
        ):
            return data + b"tamper"
        return data

    monkeypatch.setattr(mod, "read_bytes", altered)
    with pytest.raises(ValueError, match=r"hash|identity|policy"):
        mod.prepare(REPO)


def test_portable_preflight_needs_no_historical_git_objects(monkeypatch):
    mod = api()
    original = subprocess.check_output

    def shallow(args, **kwargs):
        if args[:2] == ["git", "show"]:
            pytest.fail("historical git objects unavailable in shallow CI")
        return original(args, **kwargs)

    monkeypatch.setattr(subprocess, "check_output", shallow)
    plan = mod.prepare(REPO)
    assert plan.identity["adapter_version"].startswith("yfinance-")


def test_passing_dataset_evidence_survives_calendar_refusal(tmp_path):
    result, _, _ = execute(tmp_path, mutation=lambda bars: bars.pop())
    assert result["status"] == "UNEVALUABLE"
    assert (tmp_path / "attempt" / "evidence-0000.json").exists()


def test_start_write_crossing_deadline_never_constructs_provider(tmp_path, monkeypatch):
    plan = prepared()
    current = [OPEN]
    original = api().write_json

    def delayed(path, value):
        result = original(path, value)
        if path.name == "START.json":
            current[0] = END
        return result

    monkeypatch.setattr(api(), "write_json", delayed)
    result = api().evaluate_synthetic(
        plan,
        tmp_path / "attempt",
        provider_factory=lambda: pytest.fail("constructed after deadline"),
        clock=lambda: current[0],
    )
    assert result["status"] == "INCOMPLETE"


def test_attempt_marker_crossing_deadline_never_requests_source(tmp_path, monkeypatch):
    plan = prepared()
    current = [OPEN]
    original = api().write_json

    def delayed(path, value):
        result = original(path, value)
        if path.name.startswith("attempt-"):
            current[0] = END
        return result

    monkeypatch.setattr(api(), "write_json", delayed)
    result = api().evaluate_synthetic(
        plan,
        tmp_path / "attempt",
        provider_factory=lambda: lambda *args: pytest.fail("source request after deadline"),
        clock=lambda: current[0],
    )
    assert result["status"] == "INCOMPLETE"


def test_root_reservation_parent_is_synced_before_provider(tmp_path, monkeypatch):
    plan = prepared()
    opened = []
    original = os.open

    def record(path, *args, **kwargs):
        opened.append(Path(path))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", record)

    def factory():
        assert tmp_path in opened
        raise RuntimeError("stop after durable reservation")

    with pytest.raises(RuntimeError, match="durable reservation"):
        api().evaluate_synthetic(
            plan, tmp_path / "attempt", provider_factory=factory, clock=lambda: OPEN
        )


def test_cost_sides_reconcile_existing_funded_totals(tmp_path):
    result, _, _ = execute(tmp_path, rising=True)
    for name, account in result["accounts"].items():
        sides = result["cost_breakdown"][name]
        assert sides["entry_turnover"] == pytest.approx(float(Fraction(1000, 1001)))
        assert sides["entry_fee"] == pytest.approx(float(Fraction(1, 1001)))
        assert sides["entry_turnover"] + sides["exit_turnover"] == pytest.approx(
            account["turnover"]
        )
        assert sides["entry_fee"] + sides["exit_fee"] == pytest.approx(account["fees"])


def test_final_accounting_crossing_deadline_has_no_published_economics(tmp_path, monkeypatch):
    plan = prepared()
    provider, _ = fake_source(plan)
    current = [OPEN]
    original = api().funded_hold

    def slow(*args, **kwargs):
        result = original(*args, **kwargs)
        current[0] = END
        return result

    monkeypatch.setattr(api(), "funded_hold", slow)
    result = api().evaluate_synthetic(
        plan, tmp_path / "attempt", provider_factory=lambda: provider, clock=lambda: current[0]
    )
    assert result["status"] == "INCOMPLETE"
    assert "accounts" not in result and "screen_passed" not in result


def test_synthetic_api_refuses_symlink_alias_of_registered_root(tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(api().ROOT)
    with pytest.raises(ValueError, match="registered"):
        api().evaluate_synthetic(
            prepared(),
            alias,
            provider_factory=lambda: pytest.fail("constructed"),
            clock=lambda: OPEN,
        )


@pytest.mark.parametrize("alias", [False, True])
def test_synthetic_api_refuses_registered_attempt_descendants(tmp_path, monkeypatch, alias):
    registered = tmp_path / "fake-registered"
    registered.mkdir()
    monkeypatch.setattr(api(), "ROOT", registered)
    candidate = registered / "child"
    if alias:
        link = tmp_path / "alias"
        link.symlink_to(registered)
        candidate = link / "child"
    with pytest.raises(ValueError, match="registered"):
        api().evaluate_synthetic(
            prepared(),
            candidate,
            provider_factory=lambda: pytest.fail("wrote inside registered attempt"),
            clock=lambda: OPEN,
        )
    assert list(registered.iterdir()) == []


def test_synthetic_api_refuses_lexical_registered_path_with_symlink_escape(tmp_path, monkeypatch):
    registered = tmp_path / "fake-registered"
    outside = tmp_path / "outside"
    registered.mkdir()
    outside.mkdir()
    (registered / "escape").symlink_to(outside)
    monkeypatch.setattr(api(), "ROOT", registered)
    with pytest.raises(ValueError, match="registered"):
        api().evaluate_synthetic(
            prepared(),
            registered / "escape" / "child",
            provider_factory=lambda: pytest.fail("used lexical frozen-root path"),
            clock=lambda: OPEN,
        )
    assert list(outside.iterdir()) == []


def test_mutated_decimal_policy_refuses_without_reset():
    mod = api()
    with localcontext() as context:
        context.prec = 12
        with pytest.raises(ValueError, match="Decimal"):
            mod.prepare(REPO)
        assert context.prec == 12


def test_cli_early_refusal_before_prepare_adapter_or_root(monkeypatch):
    mod = importlib.import_module("scripts.prospective_quality_value_study")
    monkeypatch.setattr(mod, "utc_now", lambda: OPEN - timedelta(days=1))
    monkeypatch.setattr(mod, "prepare", lambda *a: pytest.fail("prepared"))
    with pytest.raises(ValueError, match="window"):
        mod.main()


@given(gain=st.integers(1, 500), cost=st.integers(1, 100))
@settings(max_examples=30, deadline=None)
def test_funded_account_fraction_invariant(gain, cost):
    mod = api()
    import pandas as pd

    prices = pd.DataFrame({"synthetic": [100.0, float(100 + gain)]})
    actual = mod.funded_hold(prices, cost_rate=cost / 10000)
    expected = Fraction(100 + gain, 100) * Fraction(10000 - cost, 10000 + cost) - 1
    assert actual.net_return == pytest.approx(float(expected))
    assert actual.net_return < actual.gross_return


def test_complete_identical_positive_returns_are_exact_ties_and_fail(tmp_path):
    import pandas as pd

    from app.research.cross_sectional.published_portfolio import funded_hold

    def last_close(bars):
        bars[-1] = bars[-1].model_copy(
            update={name: Decimal(101) for name in ("open", "high", "low", "close")}
        )

    result, _, plan = execute(tmp_path, mutation=last_close)
    assert result["status"] == "COMPLETE"
    # Native companions must equal the unchanged account on this runtime's
    # identical panel; platform-dependent aggregation rounding cannot govern
    # the strict canonical-price screen.
    selection = plan.cohort["selection"]
    panel = pd.DataFrame(
        {symbol: [100.0] * 63 + [101.0] for symbol in [*selection["eligible"], "SPY"]},
        index=pd.DatetimeIndex(plan.cohort["geometry"]["session_labels"]),
    )
    for name, symbols in {
        "top_quintile": selection["selected"],
        "eligible_equalweight": selection["eligible"],
        "SPY": ["SPY"],
    }.items():
        expected = json.loads(json.dumps(asdict(funded_hold(panel[symbols], cost_rate=0.001))))
        assert result["accounts"][name] == expected
    assert result["screen_passed"] is False
    assert result["net_excess"]["eligible_equalweight"] == 0
    assert result["net_excess"]["SPY"] == 0
    assert result["exact_net_returns"] == {
        "top_quintile": "799/100100",
        "eligible_equalweight": "799/100100",
        "SPY": "799/100100",
        "cash": "0",
    }
    assert result["exact_net_excess"]["eligible_equalweight"] == "0"
    assert result["exact_net_excess"]["SPY"] == "0"


@pytest.mark.parametrize("sign", [-1, 0, 1])
def test_exact_screen_tiny_sign_survives_float_zero_projection(sign):
    latest = (
        Decimal("2." + "0" * 399 + "1")
        if sign == 1
        else Decimal("1." + "9" * 400)
        if sign == -1
        else Decimal(2)
    )
    endpoints = {
        "A": (Decimal(1), latest),
        "B": (Decimal(1), Decimal(2)),
        "SPY": (Decimal(1), Decimal(2)),
    }
    result = api().exact_funded_screen(endpoints, ["A"], ["A", "B"])
    assert result["net_excess"]["SPY"] == 0
    assert result["screen_passed"] is (sign > 0)
    difference = Fraction(result["exact_net_excess"]["SPY"])
    assert (difference > 0) - (difference < 0) == sign
    assert result["screen_basis"]["method"] == "canonical-decimal-funded-net-v1"


def test_exact_screen_averages_original_endpoint_ratios_and_refuses_nonfinite_projection():
    endpoints = {
        "A": (Decimal(100), Decimal(300)),
        "B": (Decimal(10), Decimal(10)),
        "SPY": (Decimal(1), Decimal(2)),
    }
    result = api().exact_funded_screen(endpoints, ["A"], ["A", "B"])
    assert (
        Fraction(result["exact_net_returns"]["eligible_equalweight"]) == 2 * Fraction(999, 1001) - 1
    )
    assert result["screen_passed"] is True
    endpoints["A"] = (Decimal(1), Decimal("1e1000"))
    with pytest.raises(ValueError, match="finite"):
        api().exact_funded_screen(endpoints, ["A"], ["A", "B"])


@given(
    a=st.integers(1, 1000), b=st.integers(1, 1000), c=st.integers(1, 1000), d=st.integers(1, 1000)
)
@settings(max_examples=50, deadline=None)
def test_exact_screen_fraction_mean_and_contrast_properties(a, b, c, d):
    endpoints = {
        "A": (Decimal(a), Decimal(b)),
        "B": (Decimal(c), Decimal(d)),
        "SPY": (Decimal(1), Decimal(1)),
    }
    result = api().exact_funded_screen(endpoints, ["A"], ["A", "B"])
    means = {
        "top_quintile": Fraction(b, a),
        "eligible_equalweight": (Fraction(b, a) + Fraction(d, c)) / 2,
        "SPY": Fraction(1),
    }
    returns = {name: ratio * Fraction(999, 1001) - 1 for name, ratio in means.items()}
    returns["cash"] = Fraction(0)
    contrasts = {
        name: returns["top_quintile"] - returns[name]
        for name in ("eligible_equalweight", "SPY", "cash")
    }
    assert result["exact_net_returns"] == {name: str(value) for name, value in returns.items()}
    assert result["exact_net_excess"] == {name: str(value) for name, value in contrasts.items()}
    assert result["screen_passed"] is all(value > 0 for value in contrasts.values())
