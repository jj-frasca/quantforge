"""Attributed conditional NetIncomeLoss/beginning-assets inputs (ADR-423).

These are supplied claims. The separate byte-consuming evaluator checks actual
source linkage; constructing a model cannot authenticate an issuer or source.
"""

import hashlib
import json
import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.data.fundamentals import FundamentalsHistory
from app.data.models.json_value import freeze_json


class _Claim(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, revalidate_instances="always"
    )


def history_sha(history: FundamentalsHistory) -> str:
    """Bind the complete supplied envelope and graph, without certifying them."""
    return hashlib.sha256(
        json.dumps(
            history.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


class ROAObservation(_Claim):
    url: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: AwareDatetime

    @field_validator("observed_at", mode="before")
    @classmethod
    def read_observation(cls, value: object) -> object:
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value)
            if value not in (parsed.isoformat(), parsed.isoformat().replace("+00:00", "Z")):
                raise ValueError("ROA observation must be canonical ISO datetime")
            return parsed
        return value

    @field_validator("observed_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class ROAClosing(_Claim):
    """Caller assertion; no original DEI or contemporaneous vintage is audited."""

    fiscal_year: int = Field(gt=0)
    accession_number: str = Field(pattern=r"^\d{10}-\d{2}-\d{6}$")
    end: date

    @field_validator("end", mode="before")
    @classmethod
    def read_end(cls, value: object) -> object:
        return read_date(value)


class ROAInterval(ROAClosing):
    start: date

    @field_validator("start", mode="before")
    @classmethod
    def read_start(cls, value: object) -> object:
        return read_date(value)

    @model_validator(mode="after")
    def ordered(self) -> "ROAInterval":
        if self.start >= self.end:
            raise ValueError("ROA interval start must precede end")
        return self


def exact_number(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("ROA source value must be numeric")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("ROA source value is not numeric") from exc
    if not result.is_finite():
        raise ValueError("ROA source value must be finite")
    return result


def read_date(value: object) -> object:
    if isinstance(value, str):
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError("ROA dates must be canonical ISO dates")
        return parsed
    return value


class ROAGroup(_Claim):
    name: str
    namespace: Literal["us-gaap"] = "us-gaap"
    tag: Literal["NetIncomeLoss", "Assets"]
    unit: Literal["USD"] = "USD"
    rows: tuple[dict[str, object], ...]
    exact_values: tuple[str, ...]
    value: float

    @field_validator("rows", "exact_values", mode="before")
    @classmethod
    def read_arrays(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("rows")
    @classmethod
    def freeze_rows(cls, rows: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
        result = []
        for row in rows:
            frozen = freeze_json(row)
            assert isinstance(frozen, dict)
            result.append(frozen)
        return tuple(result)

    @model_validator(mode="after")
    def consistent_values(self) -> "ROAGroup":
        if not self.rows or len(self.rows) != len(self.exact_values):
            raise ValueError("ROA group requires every original row and exact value")
        values = []
        for row, spelling in zip(self.rows, self.exact_values, strict=True):
            try:
                exact = Decimal(spelling)
            except InvalidOperation as exc:
                raise ValueError("invalid ROA exact value") from exc
            if not exact.is_finite() or isinstance(row.get("val"), bool):
                raise ValueError("ROA group requires finite numeric values")
            values.append(exact)
        if any(value != values[0] for value in values[1:]):
            raise ValueError("conflicting ROA source values")
        for row, exact in zip(self.rows, values, strict=True):
            native = exact_number(row.get("val"))
            if float(exact) != float(native):
                raise ValueError("ROA exact value projection must match retained row")
        if not math.isfinite(self.value) or self.value != float(values[0]):
            raise ValueError("ROA scalar must be finite and match source projection")
        if values[0] != 0 and self.value == 0:
            raise ValueError("ROA nonzero source value is not representable")
        if self.tag == "Assets" and (values[0] <= 0 or self.value <= 0):
            raise ValueError("ROA Assets must be positive")
        return self


def group_specs(
    intervals: tuple[ROAInterval, ROAInterval], earliest: ROAClosing
) -> tuple[tuple[str, Literal["NetIncomeLoss", "Assets"], ROAClosing, date | None, date], ...]:
    p, t = intervals
    return (
        ("income_prior", "NetIncomeLoss", p, p.start, p.end),
        ("income_latest", "NetIncomeLoss", t, t.start, t.end),
        ("assets_earliest", "Assets", earliest, None, earliest.end),
        ("assets_prior_beginning", "Assets", p, None, earliest.end),
        ("assets_prior_closing", "Assets", p, None, p.end),
        ("assets_latest_beginning", "Assets", t, None, p.end),
        ("assets_latest_closing", "Assets", t, None, t.end),
    )


def validate_row(
    row: dict[str, object], assertion: ROAClosing, start: date | None, end: date
) -> str:
    if row.get("accn") != assertion.accession_number or row.get("end") != end.isoformat():
        raise ValueError("ROA source accession/end mismatch")
    if (start is None and "start" in row) or (
        start is not None and row.get("start") != start.isoformat()
    ):
        raise ValueError("ROA source duration/instant mismatch")
    if (
        row.get("form") != "10-K"
        or type(row.get("fy")) is not int
        or row["fy"] != assertion.fiscal_year
        or row.get("fp") != "FY"
    ):
        raise ValueError("ROA source form/fiscal metadata mismatch")
    filed = row.get("filed")
    if not isinstance(filed, str):
        raise ValueError("ROA source filed label required")
    try:
        if date.fromisoformat(filed).isoformat() != filed:
            raise ValueError("noncanonical date")
    except ValueError as exc:
        raise ValueError("ROA source filed label must be canonical date") from exc
    return filed


class BeginningAssetsROAEvidence(_Claim):
    method: Literal["beginning-assets-conditional-net-income-v1"] = (
        "beginning-assets-conditional-net-income-v1"
    )
    symbol: str = Field(min_length=1)
    cik: int = Field(gt=0)
    intervals: tuple[ROAInterval, ROAInterval]
    earliest: ROAClosing
    observation: ROAObservation
    groups: tuple[ROAGroup, ...]
    history_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    interpretation: Literal[
        "Supplied annual intervals; aggregate NetIncomeLoss proxy; original DEI, numerator equivalence and historical PIT not audited"
    ] = "Supplied annual intervals; aggregate NetIncomeLoss proxy; original DEI, numerator equivalence and historical PIT not audited"

    @field_validator("intervals", "groups", mode="before")
    @classmethod
    def read_arrays(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_geometry_and_groups(self) -> "BeginningAssetsROAEvidence":
        p, t = self.intervals
        if p.fiscal_year != self.earliest.fiscal_year + 1 or t.fiscal_year != p.fiscal_year + 1:
            raise ValueError("ROA requires three consecutive fiscal labels")
        if self.earliest.end + timedelta(days=1) != p.start or p.end + timedelta(days=1) != t.start:
            raise ValueError("ROA physical periods must be contiguous")
        if len({self.earliest.accession_number, p.accession_number, t.accession_number}) != 3:
            raise ValueError("ROA original accessions must be distinct")
        specs = group_specs(self.intervals, self.earliest)
        if tuple(g.name for g in self.groups) != tuple(s[0] for s in specs):
            raise ValueError("ROA requires all seven ordered source groups")
        filed_by_accession: dict[str, str] = {}
        for group, (_, tag, assertion, start, end) in zip(self.groups, specs, strict=True):
            if group.tag != tag:
                raise ValueError("ROA source tag mismatch")
            for row in group.rows:
                filed = validate_row(row, assertion, start, end)
                prior = filed_by_accession.setdefault(assertion.accession_number, filed)
                if prior != filed:
                    raise ValueError("ROA same-filing source metadata conflict")
        if Decimal(self.groups[2].exact_values[0]) != Decimal(
            self.groups[3].exact_values[0]
        ) or Decimal(self.groups[4].exact_values[0]) != Decimal(self.groups[5].exact_values[0]):
            raise ValueError("ROA comparative Assets conflict with original closing")
        return self


def bind_roa_evidence(
    history: FundamentalsHistory, evidence: BeginningAssetsROAEvidence
) -> BeginningAssetsROAEvidence:
    """Revalidate supplied claims before any short-history scorer shortcut."""
    checked = BeginningAssetsROAEvidence.model_validate(evidence.model_dump(round_trip=True))
    h = FundamentalsHistory.model_validate(history.model_dump(round_trip=True))
    if (
        h.symbol != checked.symbol
        or h.cik != checked.cik
        or history_sha(h) != checked.history_sha256
    ):
        raise ValueError("ROA evidence must match complete supplied history identity")
    if len(h.years) < 3:
        raise ValueError("ROA evidence requires three history rows")
    a, p, t = h.years[-3:]
    if (a.fiscal_year, p.fiscal_year, t.fiscal_year) != (
        checked.earliest.fiscal_year,
        checked.intervals[0].fiscal_year,
        checked.intervals[1].fiscal_year,
    ):
        raise ValueError("ROA evidence fiscal labels must match history")
    expected = (
        checked.groups[2].value,
        checked.groups[4].value,
        checked.groups[6].value,
        checked.groups[0].value,
        checked.groups[1].value,
    )
    if (a.total_assets, p.total_assets, t.total_assets, p.net_income, t.net_income) != expected:
        raise ValueError("ROA source projections must match history operands")
    return checked
