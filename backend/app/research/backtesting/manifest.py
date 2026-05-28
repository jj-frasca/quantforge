import hashlib
import json
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def compute_parameter_hash(params: dict[str, object]) -> str:
    """Deterministic, order-independent SHA256 of a parameter dict."""
    payload = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


class ExperimentManifest(BaseModel):
    """Data-lineage record that makes a backtest a reproducible scientific claim.

    Notes:
        Without the full lineage (code version, parameter hash, data source + quality snapshot,
        adapter version), a backtest result is not reproducible. Round-trips JSON losslessly
        (§8 invariant #10).
    """

    model_config = ConfigDict(frozen=True)

    experiment_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    git_commit_hash: str
    strategy_name: str
    parameter_hash: str
    data_source: str
    symbol: str
    start_date: date
    end_date: date
    data_quality_report_id: UUID | None = None
    adapter_version: str
    validation_config_hash: str | None = None
    benchmark_symbol: str = "SPY"
