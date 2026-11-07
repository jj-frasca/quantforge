"""Network-free source-to-score known-witness evaluation (ADR-423)."""

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.data.fundamentals import FundamentalsHistory
from app.data.roa_evidence import (
    BeginningAssetsROAEvidence,
    ROAClosing,
    ROAGroup,
    ROAInterval,
    ROAObservation,
    bind_roa_evidence,
    exact_number,
    group_specs,
    history_sha,
    validate_row,
)
from app.research.fundamentals.quality import FScore, QualityScore, piotroski_f_score, quality_score
from app.research.fundamentals.record import FundamentalRecord, compute_fundamental_record


class ROAEvaluation(BaseModel):
    """Known-witness comparison; ratio strings rationalize consumed binary64 operands.

    Exact source Decimal values remain separately retained in the evidence groups.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", revalidate_instances="always")
    history: FundamentalsHistory
    evidence: BeginningAssetsROAEvidence
    available_at: AwareDatetime
    evaluated_as_of: AwareDatetime
    default_f_score: FScore
    f_score: FScore
    default_quality: QualityScore
    quality: QualityScore
    default_record: FundamentalRecord
    record: FundamentalRecord
    closing_roa: tuple[str, str]
    beginning_roa: tuple[str, str]


def evaluate_beginning_assets_roa(
    *,
    raw: bytes,
    history: FundamentalsHistory,
    intervals: tuple[ROAInterval, ROAInterval],
    earliest: ROAClosing,
    observation: ROAObservation,
    as_of: datetime,
) -> ROAEvaluation:
    """Check retained aggregate bytes and explicit assertions; never infer original DEI/PIT."""
    h = FundamentalsHistory.model_validate(history.model_dump(round_trip=True))
    obs = ROAObservation.model_validate(observation.model_dump(round_trip=True))
    if hashlib.sha256(raw).hexdigest() != obs.sha256:
        raise ValueError("ROA source SHA mismatch")
    if as_of.tzinfo is None or as_of.utcoffset() is None or as_of < obs.observed_at:
        raise ValueError("ROA evaluated cutoff must follow aware source observation")
    payload = json.loads(raw)
    exact_payload = json.loads(raw, parse_float=Decimal)
    if type(payload.get("cik")) is not int or payload["cik"] != h.cik:
        raise ValueError("ROA source issuer mismatch")
    intervals = tuple(ROAInterval.model_validate(i.model_dump(round_trip=True)) for i in intervals)  # type: ignore[assignment]
    earliest = ROAClosing.model_validate(earliest.model_dump(round_trip=True))
    groups = []
    for name, tag, assertion, start, end in group_specs(intervals, earliest):
        rows = (
            payload.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {}).get("USD", [])
        )
        exact_rows = (
            exact_payload.get("facts", {})
            .get("us-gaap", {})
            .get(tag, {})
            .get("units", {})
            .get("USD", [])
        )
        matches: list[tuple[dict[str, Any], Decimal]] = []
        for row, exact_row in zip(rows, exact_rows, strict=True):
            if row.get("accn") != assertion.accession_number or row.get("end") != end.isoformat():
                continue
            # Select accession/physical period before validating metadata. An
            # explicit null start on a candidate instant must refuse, not vanish.
            if start is not None and row.get("start") != start.isoformat():
                continue
            validate_row(row, assertion, start, end)
            value = exact_number(exact_row.get("val"))
            matches.append((row, value))
        if not matches:
            raise ValueError(f"ROA required source group missing: {name}")
        if any(value != matches[0][1] for _, value in matches[1:]):
            raise ValueError(f"conflicting ROA source values: {name}")
        matches.sort(
            key=lambda pair: (
                json.dumps(
                    pair[0],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ),
                str(pair[1]),
            )
        )
        groups.append(
            ROAGroup(
                name=name,
                tag=tag,
                rows=tuple(row for row, _ in matches),
                exact_values=tuple(str(value) for _, value in matches),
                value=float(matches[0][1]),
            )
        )
    evidence = BeginningAssetsROAEvidence(
        symbol=h.symbol,
        cik=h.cik,
        intervals=intervals,
        earliest=earliest,
        observation=obs,
        groups=tuple(groups),
        history_sha256=history_sha(h),
    )
    evidence = bind_roa_evidence(h, evidence)
    p, t = h.years[-2:]
    assert p.net_income is not None and t.net_income is not None
    assert p.total_assets is not None and t.total_assets is not None
    return ROAEvaluation(
        history=h,
        evidence=evidence,
        available_at=obs.observed_at,
        evaluated_as_of=as_of.astimezone(UTC),
        default_f_score=piotroski_f_score(h),
        f_score=piotroski_f_score(h, roa_evidence=evidence),
        default_quality=quality_score(h),
        quality=quality_score(h, roa_evidence=evidence),
        default_record=compute_fundamental_record(h),
        record=compute_fundamental_record(h, roa_evidence=evidence),
        closing_roa=(
            str(Fraction(p.net_income) / Fraction(p.total_assets)),
            str(Fraction(t.net_income) / Fraction(t.total_assets)),
        ),
        beginning_roa=(
            str(Fraction(p.net_income) / Fraction(evidence.groups[3].value)),
            str(Fraction(t.net_income) / Fraction(evidence.groups[5].value)),
        ),
    )
