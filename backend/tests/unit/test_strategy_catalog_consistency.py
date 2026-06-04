"""Consistency: every catalog entry's param NAMES must match the corresponding
Pydantic config's field names. If a config gains a field but the catalog forgets,
the frontend form silently drops the new param — CI catches it here."""

from pydantic import BaseModel

from app.api.v1.backtest import (
    BollingerBandsConfig,
    DonchianBreakoutConfig,
    KeltnerChannelConfig,
    MACDCrossoverConfig,
    MeanReversionConfig,
    MomentumConfig,
    RSIMeanReversionConfig,
    SMAConfig,
    VolTargetedSMAConfig,
)
from app.research.strategies.catalog import STRATEGY_CATALOG

_CONFIG_FOR_NAME: dict[str, type[BaseModel]] = {
    "sma": SMAConfig,
    "momentum": MomentumConfig,
    "mean_reversion": MeanReversionConfig,
    "rsi_mean_reversion": RSIMeanReversionConfig,
    "donchian_breakout": DonchianBreakoutConfig,
    "bollinger_bands": BollingerBandsConfig,
    "macd_crossover": MACDCrossoverConfig,
    "vol_targeted_sma": VolTargetedSMAConfig,
    "keltner_channel": KeltnerChannelConfig,
}


def test_every_catalog_name_has_a_pydantic_config() -> None:
    for entry in STRATEGY_CATALOG:
        assert entry.name in _CONFIG_FOR_NAME, (
            f"catalog entry '{entry.name}' has no matching Pydantic config — "
            "either add the config to StrategyConfig union or remove the catalog entry"
        )


def test_every_catalog_entry_matches_its_pydantic_config_fields() -> None:
    for entry in STRATEGY_CATALOG:
        config_class = _CONFIG_FOR_NAME[entry.name]
        # `name` is the discriminator field on the config; not a tunable param
        config_fields = set(config_class.model_fields.keys()) - {"name"}
        catalog_param_names = {p.name for p in entry.parameters}
        assert config_fields == catalog_param_names, (
            f"strategy '{entry.name}': catalog params {catalog_param_names} "
            f"!= Pydantic config fields {config_fields}"
        )


def test_every_catalog_param_default_satisfies_its_pydantic_config() -> None:
    # The defaults in the catalog must round-trip through the Pydantic config so the
    # frontend's first-render values are guaranteed valid against the backend.
    for entry in STRATEGY_CATALOG:
        config_class = _CONFIG_FOR_NAME[entry.name]
        defaults = {p.name: p.default for p in entry.parameters}
        # Should not raise — Pydantic enforces ge/gt/positive constraints declared on Field
        config_class(name=entry.name, **defaults)  # type: ignore[call-arg]
