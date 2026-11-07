"""Opt-in single-year aligned inputs with observed-source eligibility (ADR-421).

Anchors are externally audited claims. This does not authenticate original XBRL
or reconstruct historical availability from later CompanyFacts captures.
"""

import hashlib
import json
import math
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.data.flow_facts import SelectedFlowFact, SelectedFlowFacts
from app.data.fundamentals import (
    _CAPEX_TAGS,
    _COGS_TAGS,
    _CURRENT_ASSETS_TAGS,
    _CURRENT_LIABILITIES_TAGS,
    _EPS_TAGS,
    _EQUITY_TAGS,
    _GROSS_PROFIT_TAGS,
    _LONG_TERM_DEBT_TAGS,
    _NET_INCOME_TAGS,
    _OCF_TAGS,
    _RETAINED_EARNINGS_TAGS,
    _REVENUE_TAGS,
    _SHARES_TAGS,
    _TOTAL_ASSETS_TAGS,
    AnnualFundamentals,
    FundamentalsHistory,
)
from app.data.models.json_value import freeze_json
from app.research.fundamentals.record import FundamentalRecord, compute_fundamental_record


class _Claim(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", revalidate_instances="always", strict=True
    )


class SourceObservation(_Claim):
    url: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: AwareDatetime

    @field_validator("observed_at")
    @classmethod
    def utc_observation(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class FilingAnnualAnchor(_Claim):
    """Supplied audited DEI/header annual identity; validity alone is not authentication."""

    cik: int = Field(gt=0)
    fiscal_year: int = Field(gt=0)
    accession_number: str = Field(pattern=r"^\d{10}-\d{2}-\d{6}$")
    annual_start: date
    report_end: date
    form: Literal["10-K"] = "10-K"
    fiscal_focus: Literal["FY"] = "FY"
    transition: Literal[False] = False
    original: SourceObservation
    header_labels: dict[str, object]

    @field_validator("header_labels")
    @classmethod
    def freeze_labels(cls, value: dict[str, object]) -> dict[str, object]:
        frozen = freeze_json(value)
        assert isinstance(frozen, dict)
        return frozen

    @model_validator(mode="after")
    def ordered_interval(self) -> "FilingAnnualAnchor":
        if self.annual_start >= self.report_end:
            raise ValueError("annual anchor start must precede report end")
        return self


class AnchoredSelection(_Claim):
    field: str
    exact_value: str
    facts: tuple[SelectedFlowFact, ...]


class AnchoredEvaluation(_Claim):
    method: Literal["explicit-annual-observed-v1"] = "explicit-annual-observed-v1"
    anchor: FilingAnnualAnchor
    observation: SourceObservation
    available_at: AwareDatetime
    evaluated_as_of: AwareDatetime
    selections: tuple[AnchoredSelection, ...]
    missing_fields: tuple[str, ...]
    history: FundamentalsHistory
    record: FundamentalRecord


# field, ordered tags, unit, instant. Weighted-average shares are a duration flow.
_SPECS = (
    ("revenue", _REVENUE_TAGS, "USD", False),
    ("net_income", _NET_INCOME_TAGS, "USD", False),
    ("eps", _EPS_TAGS, "USD/shares", False),
    ("shares_diluted", _SHARES_TAGS, "shares", False),
    ("operating_cash_flow", _OCF_TAGS, "USD", False),
    ("capex", _CAPEX_TAGS, "USD", False),
    ("gross_profit", _GROSS_PROFIT_TAGS, "USD", False),
    ("cogs", _COGS_TAGS, "USD", False),
    ("total_assets", _TOTAL_ASSETS_TAGS, "USD", True),
    ("total_current_assets", _CURRENT_ASSETS_TAGS, "USD", True),
    ("total_current_liabilities", _CURRENT_LIABILITIES_TAGS, "USD", True),
    ("long_term_debt", _LONG_TERM_DEBT_TAGS, "USD", True),
    ("retained_earnings", _RETAINED_EARNINGS_TAGS, "USD", True),
    ("total_equity", _EQUITY_TAGS, "USD", True),
)
_ROW_KEYS = ("fy", "fp", "form", "filed", "accn", "start", "end", "frame", "val")


def _finite_projection(value: int | Decimal | float, field: str) -> float:
    try:
        projected = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field} is not representable") from exc
    if not math.isfinite(projected):
        raise ValueError(f"{field} is not finite")
    return projected


def _select(
    gaap: dict[str, Any],
    exact_gaap: dict[str, Any],
    anchor: FilingAnnualAnchor,
    field: str,
    tags: tuple[str, ...],
    unit: str,
    instant: bool,
) -> AnchoredSelection | None:
    for tag in tags:
        rows = gaap.get(tag, {}).get("units", {}).get(unit, [])
        exact_rows = exact_gaap.get(tag, {}).get("units", {}).get(unit, [])
        admitted: list[SelectedFlowFact] = []
        values: list[Decimal] = []
        for index, row in enumerate(rows):
            if not (
                row.get("accn") == anchor.accession_number
                and row.get("form") == "10-K"
                and row.get("end") == anchor.report_end.isoformat()
                and (
                    "start" not in row
                    if instant
                    else row.get("start") == anchor.annual_start.isoformat()
                )
            ):
                continue
            value = exact_rows[index].get("val")
            if type(value) not in (int, Decimal, float):
                raise ValueError(f"{field} eligible value is not numeric")
            exact = Decimal(value) if type(value) is int else Decimal(str(value))
            if not exact.is_finite():
                raise ValueError(f"{field} eligible value is not finite")
            values.append(exact)
            admitted.append(
                SelectedFlowFact(tag=tag, unit=unit, row={k: row[k] for k in _ROW_KEYS if k in row})
            )
        if admitted:
            if any(value != values[0] for value in values[1:]):
                raise ValueError(f"conflicting eligible {field} values")
            # Verify representability only after exact duplicate comparison.
            _finite_projection(values[0], field)
            admitted.sort(
                key=lambda fact: json.dumps(fact.row, sort_keys=True, separators=(",", ":"))
            )
            return AnchoredSelection(
                field=field, exact_value=min(map(str, values)), facts=tuple(admitted)
            )
    return None


def evaluate_anchored_fundamentals(
    *,
    raw: bytes,
    symbol: str,
    observation: SourceObservation,
    anchor: FilingAnnualAnchor,
    as_of: datetime,
) -> AnchoredEvaluation:
    """Select one aligned annual input and score without price, retaining its evidence.

    Notes:
        Eligibility is bounded by actual observations, not historical filed labels.
        The supplied original anchor does not certify other aggregate-source fields.
    """
    observation = SourceObservation.model_validate(observation)
    anchor = FilingAnnualAnchor.model_validate(anchor)
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be aware")
    as_of = as_of.astimezone(UTC)
    available_at = max(observation.observed_at, anchor.original.observed_at)
    if as_of < available_at:
        raise ValueError("as_of precedes observed-source availability")
    if hashlib.sha256(raw).hexdigest() != observation.sha256:
        raise ValueError("CompanyFacts SHA256 mismatch")
    data = json.loads(raw)
    # A second exact numeric parse detects disagreement hidden by binary64 rounding;
    # retained metadata uses ordinary JSON types, with the exact admitted value beside it.
    exact_data = json.loads(raw, parse_float=Decimal)
    if type(data.get("cik")) is not int or data["cik"] != anchor.cik:
        raise ValueError("CompanyFacts issuer does not match anchor")
    gaap = data.get("facts", {}).get("us-gaap", {})
    exact_gaap = exact_data.get("facts", {}).get("us-gaap", {})
    selections: list[AnchoredSelection] = []
    missing: list[str] = []
    values: dict[str, float | None] = {}
    by_field: dict[str, SelectedFlowFact] = {}
    for field, tags, unit, instant in _SPECS:
        selection = _select(gaap, exact_gaap, anchor, field, tags, unit, instant)
        if selection is None:
            missing.append(field)
            values[field] = None
        else:
            selections.append(selection)
            values[field] = _finite_projection(Decimal(selection.exact_value), field)
            by_field[field] = selection.facts[0]
    revenue = values["revenue"]
    if revenue is None:
        raise ValueError("no revenue for explicit annual anchor")
    gp = values["gross_profit"]
    if gp is None and values["cogs"] is not None:
        gp = _finite_projection(revenue - values["cogs"], "derived gross profit")
    ocf, capex = values["operating_cash_flow"], values["capex"]
    fcf = (
        _finite_projection(ocf - capex, "derived FCF")
        if ocf is not None and capex is not None
        else None
    )
    year = AnnualFundamentals(
        fiscal_year=anchor.fiscal_year,
        period_end=anchor.report_end,
        revenue=revenue,
        net_income=values["net_income"],
        eps=values["eps"],
        shares_diluted=values["shares_diluted"],
        free_cash_flow=fcf,
        total_assets=values["total_assets"],
        total_current_assets=values["total_current_assets"],
        total_current_liabilities=values["total_current_liabilities"],
        long_term_debt=values["long_term_debt"],
        gross_profit=gp,
        operating_cash_flow=ocf,
        retained_earnings=values["retained_earnings"],
        total_equity=values["total_equity"],
        flow_facts=SelectedFlowFacts(
            revenue=by_field["revenue"],
            net_income=by_field.get("net_income"),
            eps=by_field.get("eps"),
        ),
    )
    history = FundamentalsHistory(
        symbol=symbol,
        cik=anchor.cik,
        entity_name=str(data.get("entityName", symbol)),
        form=anchor.form,
        accession_number=anchor.accession_number,
        source_url=anchor.original.url,
        years=(year,),
    )
    return AnchoredEvaluation(
        anchor=anchor,
        observation=observation,
        available_at=available_at,
        evaluated_as_of=as_of,
        selections=tuple(selections),
        missing_fields=tuple(missing),
        history=history,
        record=compute_fundamental_record(history),
    )
