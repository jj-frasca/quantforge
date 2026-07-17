"""Consistency: every catalog entry's param NAMES must match the corresponding
Pydantic config's field names. If a config gains a field but the catalog forgets,
the frontend form silently drops the new param — CI catches it here."""

from pydantic import BaseModel

from app.research.strategies.catalog import STRATEGY_CATALOG
from app.research.strategies.configs import (
    ADXConfig,
    AroonConfig,
    BollingerBandsConfig,
    CCIConfig,
    ChaikinMoneyFlowConfig,
    ConnorsRSIConfig,
    DonchianBreakoutConfig,
    FiftyTwoWeekHighConfig,
    KeltnerChannelConfig,
    MACDCrossoverConfig,
    MeanReversionConfig,
    MomentumConfig,
    RSIMeanReversionConfig,
    SMAConfig,
    StochasticOscillatorConfig,
    TrendFilteredMeanReversionConfig,
    TripleMAAlignmentConfig,
    TRIXConfig,
    UltimateOscillatorConfig,
    VolManagedMomentumConfig,
    VolTargetedSMAConfig,
    VWAPReversionConfig,
    WilliamsRConfig,
)

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
    "trend_filtered_mean_reversion": TrendFilteredMeanReversionConfig,
    "triple_ma_alignment": TripleMAAlignmentConfig,
    "williams_r": WilliamsRConfig,
    "cci": CCIConfig,
    "stochastic_oscillator": StochasticOscillatorConfig,
    "trix": TRIXConfig,
    "aroon": AroonConfig,
    "chaikin_money_flow": ChaikinMoneyFlowConfig,
    "vwap_reversion": VWAPReversionConfig,
    "adx": ADXConfig,
    "connors_rsi": ConnorsRSIConfig,
    "fifty_two_week_high": FiftyTwoWeekHighConfig,
    "ultimate_oscillator": UltimateOscillatorConfig,
    "vol_managed_momentum": VolManagedMomentumConfig,
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


def test_every_catalog_entry_has_a_plain_english_summary() -> None:
    # The summary is the strategy's user-facing face. Empty / placeholder copy ships a
    # nameless dropdown option to a beginner; we'd rather fail CI than ship that.
    # Length is a sanity floor — Pydantic doesn't enforce it on `str` fields.
    for entry in STRATEGY_CATALOG:
        assert entry.summary.strip(), f"catalog entry '{entry.name}' has an empty summary"
        assert len(entry.summary) >= 30, (
            f"catalog entry '{entry.name}' summary is suspiciously short "
            f"({len(entry.summary)} chars) — does it read as a real sentence?"
        )


def test_every_catalog_entry_has_a_known_category() -> None:
    # The category is the Literal StrategyCategory; Pydantic itself rejects unknown values
    # at construction time. This test just documents the expected categories and surfaces
    # any catalog entry that drifts off the list, so adding a new category is a deliberate
    # decision (extend the Literal and update this test in the same commit).
    expected = {"Trend", "Mean Reversion", "Breakout", "Combination"}
    for entry in STRATEGY_CATALOG:
        assert entry.category in expected, (
            f"catalog entry '{entry.name}' has unexpected category '{entry.category}'"
        )
