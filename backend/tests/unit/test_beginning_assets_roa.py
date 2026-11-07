"""ADR423 source-linked beginning Assets; no network or prices."""

import gzip
import hashlib
import importlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.data.fundamentals import FundamentalsHistory, parse_company_facts_history
from app.research.fundamentals.quality import piotroski_f_score, quality_score
from app.research.fundamentals.record import (
    FundamentalRecord,
    compute_fundamental_record,
    merge_fundamental_records,
)

OBSERVED = datetime(2026, 10, 30, 7, 28, 44, 145492, tzinfo=UTC)
ACCS = ["0000320193-20-000096", "0000320193-21-000105", "0000320193-22-000108"]
ENDS = ["2020-09-26", "2021-09-25", "2022-09-24"]
STARTS = ["2020-09-27", "2021-09-26"]


def api():
    return importlib.import_module("app.research.fundamentals.roa_evaluation")


def source_api():
    return importlib.import_module("app.data.roa_evidence")


def assertions():
    m = source_api()
    return [
        m.ROAInterval(
            fiscal_year=2021 + i,
            accession_number=ACCS[i + 1],
            start=date.fromisoformat(STARTS[i]),
            end=date.fromisoformat(ENDS[i + 1]),
        )
        for i in range(2)
    ]


def evaluate(data, history=None, **changes):
    raw = json.dumps(data).encode()
    if history is None:
        history = synthetic_history()
    args = {
        "raw": raw,
        "history": history,
        "intervals": tuple(assertions()),
        "earliest": source_api().ROAClosing(
            fiscal_year=2020, accession_number=ACCS[0], end=date.fromisoformat(ENDS[0])
        ),
        "observation": source_api().ROAObservation(
            url="retained-source", sha256=hashlib.sha256(raw).hexdigest(), observed_at=OBSERVED
        ),
        "as_of": OBSERVED,
    }
    args.update(changes)
    return api().evaluate_beginning_assets_roa(**args)


def synthetic(assets=(100, 1000, 100), incomes=(10, 15)):
    ni = []
    balances = []
    for i in range(3):
        common = {
            "accn": ACCS[i],
            "form": "10-K",
            "fy": 2020 + i,
            "fp": "FY",
            "filed": f"{2020 + i}-10-30",
        }
        balances.append(dict(common, end=ENDS[i], val=assets[i]))
        if i:
            balances.append(dict(common, end=ENDS[i - 1], val=assets[i - 1]))
            ni.append(dict(common, start=STARTS[i - 1], end=ENDS[i], val=incomes[i - 1]))
    return {
        "cik": 320193,
        "facts": {
            "us-gaap": {
                "Assets": {"units": {"USD": balances}},
                "NetIncomeLoss": {"units": {"USD": ni}},
            }
        },
    }


def synthetic_history(assets=(100, 1000, 100), incomes=(10, 15)):
    return FundamentalsHistory(
        symbol="AAPL",
        cik=320193,
        entity_name="Fixture",
        form="10-K",
        accession_number="retained-2025",
        source_url="retained",
        years=[
            {
                "fiscal_year": 2020 + i,
                "revenue": 100.0,
                "total_assets": assets[i],
                "net_income": None if i == 0 else incomes[i - 1],
                "operating_cash_flow": None if i == 0 else incomes[i - 1] + 1,
            }
            for i in range(3)
        ],
    )


def test_integrated_actual_source_witness_and_unchanged_history():
    raw = gzip.decompress(
        Path(
            "../docs/evidence/FINDING-322/companyfacts.CIK0000320193.20261030.json.gz"
        ).read_bytes()
    )
    assert (
        hashlib.sha256(raw).hexdigest()
        == "73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43"
    )
    data = json.loads(raw)
    whole = parse_company_facts_history(data, "AAPL")
    h = FundamentalsHistory.model_validate(
        {**whole.model_dump(), "years": [y for y in whole.years if y.fiscal_year <= 2022]}
    )
    before = h.model_dump(mode="json")
    r = api().evaluate_beginning_assets_roa(
        raw=raw,
        history=h,
        intervals=tuple(assertions()),
        earliest=source_api().ROAClosing(
            fiscal_year=2020, accession_number=ACCS[0], end=date.fromisoformat(ENDS[0])
        ),
        observation=source_api().ROAObservation(
            url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
            sha256="73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43",
            observed_at=OBSERVED,
        ),
        as_of=OBSERVED,
    )
    assert r.evidence.observation.sha256 == hashlib.sha256(raw).hexdigest()
    assert r.history.model_dump(mode="json") == before == h.model_dump(mode="json")
    assert r.default_f_score.score == 8 and r.f_score.score == 7
    assert r.default_f_score.delta_roa_positive and not r.f_score.delta_roa_positive
    old = r.default_f_score.model_dump()
    new = r.f_score.model_dump()
    assert {k: v for k, v in old.items() if k not in ("score", "delta_roa_positive")} == {
        k: v for k, v in new.items() if k not in ("score", "delta_roa_positive")
    }
    assert r.default_quality.score == 0.6675842309900554
    assert r.quality.score == pytest.approx(r.default_quality.score - 1 / 27)
    assert r.quality.gross_profitability == r.default_quality.gross_profitability
    assert r.quality.safety == r.default_quality.safety
    assert r.record.value_score is None and r.record.combined_score is None
    assert r.record.history_citation.accession_number == "0000320193-25-000079"
    assert r.quality.roa_evidence == r.record.roa_evidence == r.evidence
    assert len(r.evidence.groups) == 7
    assert r.available_at == OBSERVED


@pytest.mark.parametrize(
    "assets,incomes",
    [((100, 1000, 100), (10, 15)), ((1000, 100, 1000), (10, 15)), ((100, 100, 100), (10, 15))],
)
def test_both_reversal_directions_and_constant_assets(assets, incomes):
    h = synthetic_history(assets, incomes)
    r = evaluate(synthetic(assets, incomes), h)
    assert r.f_score.delta_roa_positive == (
        Fraction(incomes[1], assets[1]) > Fraction(incomes[0], assets[0])
    )
    assert r.default_f_score.delta_roa_positive == (
        Fraction(incomes[1], assets[2]) > Fraction(incomes[0], assets[1])
    )


@settings(max_examples=50, deadline=None)
@given(
    st.tuples(st.integers(1, 100000), st.integers(1, 100000), st.integers(1, 100000)),
    st.tuples(st.integers(-1000, 1000), st.integers(-1000, 1000)),
)
def test_beginning_ratio_order_matches_fraction(assets, incomes):
    r = evaluate(synthetic(assets, incomes), synthetic_history(assets, incomes))
    assert r.f_score.delta_roa_positive == (
        Fraction(incomes[1], assets[1]) > Fraction(incomes[0], assets[0])
    )
    assert r.f_score.accruals_quality == r.default_f_score.accruals_quality


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "conflict",
        "nullstart",
        "badform",
        "badfy",
        "badfp",
        "badfiled",
        "comparative",
        "boolean",
        "string",
        "nonpositive",
    ],
)
def test_bad_source_groups_refuse(mutation):
    d = synthetic()
    rows = d["facts"]["us-gaap"]["Assets"]["units"]["USD"]
    if mutation == "missing":
        rows.pop(0)
    elif mutation == "conflict":
        rows.append(dict(rows[0], val=101))
    elif mutation == "nullstart":
        rows[0]["start"] = None
    elif mutation == "badform":
        rows[0]["form"] = "10-Q"
    elif mutation == "badfy":
        rows[0]["fy"] = 2021
    elif mutation == "badfp":
        rows[0]["fp"] = "Q4"
    elif mutation == "badfiled":
        rows[0]["filed"] = "bad"
    elif mutation == "comparative":
        rows[2]["val"] = 101
    elif mutation == "boolean":
        rows[0]["val"] = True
    elif mutation == "string":
        rows[0]["val"] = "100"
    else:
        rows[0]["val"] = 0
    reason = {
        "missing": "required source group missing",
        "conflict": "conflicting ROA source values",
        "nullstart": "duration/instant mismatch",
        "badform": "form/fiscal metadata mismatch",
        "badfy": "form/fiscal metadata mismatch",
        "badfp": "form/fiscal metadata mismatch",
        "badfiled": "filed label must be canonical date",
        "comparative": "comparative Assets conflict",
        "boolean": "must be numeric",
        "string": "must be numeric",
        "nonpositive": "Assets must be positive",
    }[mutation]
    with pytest.raises(ValueError, match=reason):
        evaluate(d)


@pytest.mark.parametrize(
    "change", ["sha", "issuer", "early", "naive", "history", "geometry", "short"]
)
def test_source_cutoff_history_geometry_refusals(change):
    d = synthetic()
    kwargs = {}
    if change == "sha":
        kwargs["observation"] = source_api().ROAObservation(
            url="x", sha256="0" * 64, observed_at=OBSERVED
        )
    elif change == "issuer":
        d["cik"] = 1
    elif change == "early":
        kwargs["as_of"] = OBSERVED - timedelta(seconds=1)
    elif change == "naive":
        kwargs["as_of"] = OBSERVED.replace(tzinfo=None)
    elif change == "history":
        kwargs["history"] = synthetic_history((101, 1000, 100))
    elif change == "geometry":
        kwargs["intervals"] = (
            assertions()[0],
            assertions()[1].model_copy(update={"start": date(2021, 9, 27)}),
        )
    else:
        kwargs["history"] = FundamentalsHistory.model_validate(
            {**synthetic_history().model_dump(), "years": []}
        )
    reason = {
        "sha": "source SHA mismatch",
        "issuer": "source issuer mismatch",
        "early": "cutoff must follow aware source observation",
        "naive": "cutoff must follow aware source observation",
        "history": "source projections must match history operands",
        "geometry": "required source group missing",
        "short": "requires three history rows",
    }[change]
    with pytest.raises(ValueError, match=reason):
        evaluate(d, **kwargs)


def test_evidence_immutable_defaults_roundtrip_and_whole_winner():
    h = synthetic_history()
    r = evaluate(synthetic(), h)
    assert "roa_evidence" not in quality_score(h).model_dump()
    assert "roa_evidence" not in compute_fundamental_record(h).model_dump()
    with pytest.raises((ValueError, TypeError)):
        r.evidence.groups[0].rows[0]["val"] = 42
    restored = FundamentalRecord.model_validate_json(r.record.model_dump_json())
    assert restored == r.record
    legacy = compute_fundamental_record(h)
    assert merge_fundamental_records([legacy], [r.record])[0] == r.record
    assert merge_fundamental_records([r.record], [legacy])[0] == legacy
    other = FundamentalsHistory.model_validate({**h.model_dump(), "entity_name": "different"})
    with pytest.raises(ValueError, match="complete supplied history identity"):
        piotroski_f_score(other, roa_evidence=r.evidence)
    short = FundamentalsHistory.model_validate({**h.model_dump(), "years": []})
    with pytest.raises(ValueError, match="complete supplied history identity"):
        piotroski_f_score(short, roa_evidence=r.evidence)


@pytest.mark.parametrize("price", [0, 10, -1, float("nan")])
def test_explicit_price_refuses_before_scoring(price, monkeypatch):
    h = synthetic_history()
    r = evaluate(synthetic(), h)
    import app.research.fundamentals.record as mod

    monkeypatch.setattr(mod, "quality_score", lambda *args, **kwargs: pytest.fail("scored"))
    with pytest.raises(ValueError, match="price"):
        mod.compute_fundamental_record(h, price, roa_evidence=r.evidence)
    with pytest.raises(ValueError, match="no-price records"):
        FundamentalRecord.model_validate(
            {
                **r.record.model_dump(),
                "value_score": 0.5,
                "combined_score": r.record.quality_score * 0.5,
            }
        )


def test_agreeing_duplicates_and_source_order_invariance():
    d = synthetic()
    r = evaluate(d)
    rows = d["facts"]["us-gaap"]["Assets"]["units"]["USD"]
    rows.append(dict(rows[0]))
    a = evaluate(d)
    rows.reverse()
    b = evaluate(d)
    assert a.evidence.groups == b.evidence.groups
    assert a.f_score == r.f_score


def test_exact_conflict_refuses_before_any_float_projection(monkeypatch):
    data = synthetic()
    rows = data["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"]
    rows.append(dict(rows[0], val=11))

    class NoProjection(Decimal):
        def __float__(self):
            pytest.fail("projected before exact conflict refusal")

    monkeypatch.setattr(api(), "exact_number", lambda v: NoProjection(str(v)))
    with pytest.raises(ValueError, match="conflicting ROA source values"):
        evaluate(data)


def test_equal_decimal_spelling_permutation_has_canonical_group_order():
    data = synthetic()
    rows = data["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"]
    rows.insert(1, dict(rows[0]))
    raw = json.dumps(data).replace('"val": 10}', '"val": 10.0}', 1)
    raw = raw.replace('"val": 10}', '"val": 10.00}', 1).encode()
    observation = source_api().ROAObservation(
        url="retained", sha256=hashlib.sha256(raw).hexdigest(), observed_at=OBSERVED
    )
    first = evaluate({}, raw=raw, observation=observation)
    reversed_raw = (
        raw.replace(b'"val": 10.0}', b'"val": PLACEHOLDER}')
        .replace(b'"val": 10.00}', b'"val": 10.0}')
        .replace(b'"val": PLACEHOLDER}', b'"val": 10.00}')
    )
    second = evaluate(
        {},
        raw=reversed_raw,
        observation=observation.model_copy(
            update={"sha256": hashlib.sha256(reversed_raw).hexdigest()}
        ),
    )
    assert first.evidence.groups == second.evidence.groups


@pytest.mark.parametrize("field", ["Assets", "NetIncomeLoss"])
def test_nonzero_source_projection_to_zero_refuses(field):
    assets = (0, 1000, 100) if field == "Assets" else (100, 1000, 100)
    incomes = (0, 15) if field == "NetIncomeLoss" else (10, 15)
    raw = json.dumps(synthetic(assets, incomes)).replace('"val": 0}', '"val": 1e-400}').encode()
    obs = source_api().ROAObservation(
        url="retained", sha256=hashlib.sha256(raw).hexdigest(), observed_at=OBSERVED
    )
    with pytest.raises(ValueError, match="not representable"):
        evaluate({}, synthetic_history(assets, incomes), raw=raw, observation=obs)


def test_same_filing_metadata_conflict_refuses_and_unrelated_rows_stay_unrelated():
    data = synthetic()
    rows = data["facts"]["us-gaap"]["Assets"]["units"]["USD"]
    rows.append(dict(rows[0], accn="unrelated", val=999999))
    assert evaluate(data).f_score.score == evaluate(synthetic()).f_score.score
    rows[1]["filed"] = "2021-10-31"
    with pytest.raises(ValueError, match="same-filing source metadata conflict"):
        evaluate(data)


@pytest.mark.parametrize("field", ["symbol", "cik", "fiscal_year"])
def test_record_retained_evidence_binds_available_identity(field):
    record = evaluate(synthetic()).record
    changed = {**record.model_dump(), field: "OTHER" if field == "symbol" else 1}
    with pytest.raises(ValueError, match="match record issuer and fiscal year"):
        FundamentalRecord.model_validate(changed)


@pytest.mark.parametrize("change", ["labels", "values"])
def test_direct_scorer_revalidates_evidence_against_history_operands(change):
    h = synthetic_history()
    evidence = evaluate(synthetic(), h).evidence
    years = list(h.years)
    years[0] = years[0].model_copy(
        update={"fiscal_year": 2019} if change == "labels" else {"total_assets": 101}
    )
    other = FundamentalsHistory.model_validate({**h.model_dump(), "years": years})
    forged = evidence.model_copy(update={"history_sha256": source_api().history_sha(other)})
    reason = (
        "fiscal labels must match history"
        if change == "labels"
        else "source projections must match history operands"
    )
    with pytest.raises(ValueError, match=reason):
        piotroski_f_score(other, roa_evidence=forged)


def test_positive_explicit_assets_reach_all_three_actual_ratios(monkeypatch):
    import app.research.fundamentals.quality as mod

    h = synthetic_history()
    evidence = evaluate(synthetic(), h).evidence
    calls = []
    original = mod._ratio

    def retain(numerator, denominator):
        calls.append((numerator, denominator))
        return original(numerator, denominator)

    monkeypatch.setattr(mod, "_ratio", retain)
    piotroski_f_score(h, roa_evidence=evidence)
    assert calls[:3] == [(15.0, 1000.0), (10.0, 100.0), (16.0, 1000.0)]


@pytest.mark.parametrize(
    "change", ["gap", "duplicate", "source_tag", "group_name", "exact_conflict"]
)
def test_unchecked_evidence_is_revalidated_before_use(change):
    h = synthetic_history()
    evidence = evaluate(synthetic(), h).evidence
    if change == "gap":
        latest = evidence.intervals[1].model_copy(update={"start": date(2021, 9, 27)})
        evidence = evidence.model_copy(update={"intervals": (evidence.intervals[0], latest)})
        reason = "physical periods must be contiguous"
    elif change == "duplicate":
        earliest = evidence.earliest.model_copy(update={"accession_number": ACCS[1]})
        evidence = evidence.model_copy(update={"earliest": earliest})
        reason = "accessions must be distinct"
    else:
        groups = list(evidence.groups)
        if change == "source_tag":
            groups[0] = groups[0].model_copy(update={"tag": "Assets"})
            reason = "source tag mismatch"
        elif change == "group_name":
            groups[0] = groups[0].model_copy(update={"name": "other"})
            reason = "seven ordered source groups"
        else:
            groups[0] = groups[0].model_copy(update={"exact_values": ("11",)})
            reason = "projection must match retained row"
        evidence = evidence.model_copy(update={"groups": tuple(groups)})
    with pytest.raises(ValueError, match=reason):
        piotroski_f_score(h, roa_evidence=evidence)


def test_source_conflict_that_collapses_to_identical_float_still_refuses():
    data = synthetic()
    rows = data["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"]
    rows[0]["val"] = 10**30
    rows.append(dict(rows[0], val=10**30 + 1))
    assert float(rows[0]["val"]) == float(rows[-1]["val"])
    with pytest.raises(ValueError, match="conflicting ROA source values"):
        evaluate(data)


def test_evaluation_roundtrip_and_timezone_normalization():
    r = evaluate(synthetic())
    restored = api().ROAEvaluation.model_validate_json(r.model_dump_json())
    assert restored == r
    assert r.evidence.observation.observed_at.utcoffset() == timedelta(0)


def test_existing_pool_and_shard_json_readers_retain_explicit_evidence(tmp_path):
    from app.research.fundamentals.record import load_fundamentals_pool, load_fundamentals_shard

    record = evaluate(synthetic()).record
    path = tmp_path / "records.json"
    path.write_text(json.dumps([record.model_dump(mode="json")]))
    assert load_fundamentals_pool(path) == [record]
    assert load_fundamentals_shard(path) == [record]
