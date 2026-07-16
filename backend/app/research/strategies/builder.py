"""Construct BaseStrategy instances from Pydantic configs or plain (name, params) dicts.

Notes:
    The two entry points serve different callers:
    - `build_strategy(config)` — for the /backtest endpoint, which has already routed
      its incoming JSON through the discriminated `StrategyConfig` union.
    - `build_strategy_from_dict(name, params)` — for the /validate endpoint and the
      catalog-driven grid generator, which produce raw (name, params) pairs and want
      one function that handles BOTH validation and construction.

    Both paths share the same dispatch table (`_FACTORIES`) keyed by discriminator,
    so adding a strategy in [[ADR-010]] still touches one mapping plus the catalog.
"""

from typing import Final

from pydantic import TypeAdapter

from app.research.strategies.adx import ADXStrategy
from app.research.strategies.aroon import AroonStrategy
from app.research.strategies.base import BaseStrategy
from app.research.strategies.bollinger_bands import BollingerBandsStrategy
from app.research.strategies.cci import CCIStrategy
from app.research.strategies.chaikin_money_flow import ChaikinMoneyFlowStrategy
from app.research.strategies.configs import (
    ADXConfig,
    AroonConfig,
    BollingerBandsConfig,
    CCIConfig,
    ChaikinMoneyFlowConfig,
    ConnorsRSIConfig,
    DonchianBreakoutConfig,
    KeltnerChannelConfig,
    MACDCrossoverConfig,
    MeanReversionConfig,
    MomentumConfig,
    RSIMeanReversionConfig,
    SMAConfig,
    StochasticOscillatorConfig,
    StrategyConfig,
    TrendFilteredMeanReversionConfig,
    TripleMAAlignmentConfig,
    TRIXConfig,
    VolTargetedSMAConfig,
    VWAPReversionConfig,
    WilliamsRConfig,
)
from app.research.strategies.connors_rsi import ConnorsRSIStrategy
from app.research.strategies.donchian_breakout import DonchianBreakoutStrategy
from app.research.strategies.keltner_channel import KeltnerChannelStrategy
from app.research.strategies.macd_crossover import MACDCrossoverStrategy
from app.research.strategies.mean_reversion import MeanReversionStrategy
from app.research.strategies.momentum import MomentumStrategy
from app.research.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from app.research.strategies.sma import SMAStrategy
from app.research.strategies.stochastic_oscillator import StochasticOscillatorStrategy
from app.research.strategies.trend_filtered_mean_reversion import (
    TrendFilteredMeanReversionStrategy,
)
from app.research.strategies.triple_ma_alignment import TripleMAAlignmentStrategy
from app.research.strategies.trix import TRIXStrategy
from app.research.strategies.vol_targeted_sma import VolTargetedSMAStrategy
from app.research.strategies.vwap_reversion import VWAPReversionStrategy
from app.research.strategies.williams_r import WilliamsRStrategy

_StrategyConfigAdapter: Final = TypeAdapter[StrategyConfig](StrategyConfig)


def build_strategy(config: StrategyConfig) -> BaseStrategy:
    """Construct the concrete strategy for an already-validated Pydantic config."""
    if isinstance(config, SMAConfig):
        return SMAStrategy(fast=config.fast, slow=config.slow)
    if isinstance(config, MomentumConfig):
        return MomentumStrategy(lookback=config.lookback, skip=config.skip)
    if isinstance(config, RSIMeanReversionConfig):
        return RSIMeanReversionStrategy(
            window=config.window,
            oversold=config.oversold,
            overbought=config.overbought,
        )
    if isinstance(config, DonchianBreakoutConfig):
        return DonchianBreakoutStrategy(lookback=config.lookback)
    if isinstance(config, BollingerBandsConfig):
        return BollingerBandsStrategy(window=config.window, num_std=config.num_std)
    if isinstance(config, MACDCrossoverConfig):
        return MACDCrossoverStrategy(fast=config.fast, slow=config.slow, signal=config.signal)
    if isinstance(config, VolTargetedSMAConfig):
        return VolTargetedSMAStrategy(
            fast=config.fast,
            slow=config.slow,
            vol_window=config.vol_window,
            target_vol=config.target_vol,
        )
    if isinstance(config, KeltnerChannelConfig):
        return KeltnerChannelStrategy(
            ma_window=config.ma_window,
            atr_window=config.atr_window,
            multiplier=config.multiplier,
        )
    if isinstance(config, MeanReversionConfig):
        return MeanReversionStrategy(window=config.window, k=config.k)
    if isinstance(config, TrendFilteredMeanReversionConfig):
        return TrendFilteredMeanReversionStrategy(
            z_window=config.z_window,
            z_threshold=config.z_threshold,
            trend_window=config.trend_window,
        )
    if isinstance(config, TripleMAAlignmentConfig):
        return TripleMAAlignmentStrategy(fast=config.fast, medium=config.medium, slow=config.slow)
    if isinstance(config, WilliamsRConfig):
        return WilliamsRStrategy(
            window=config.window,
            oversold=config.oversold,
            overbought=config.overbought,
        )
    if isinstance(config, CCIConfig):
        return CCIStrategy(window=config.window, threshold=config.threshold)
    if isinstance(config, StochasticOscillatorConfig):
        return StochasticOscillatorStrategy(
            k_window=config.k_window,
            d_window=config.d_window,
            oversold=config.oversold,
            overbought=config.overbought,
        )
    if isinstance(config, TRIXConfig):
        return TRIXStrategy(window=config.window, signal=config.signal)
    if isinstance(config, AroonConfig):
        return AroonStrategy(window=config.window)
    if isinstance(config, ChaikinMoneyFlowConfig):
        return ChaikinMoneyFlowStrategy(window=config.window, threshold=config.threshold)
    if isinstance(config, VWAPReversionConfig):
        return VWAPReversionStrategy(window=config.window, threshold=config.threshold)
    if isinstance(config, ADXConfig):
        return ADXStrategy(window=config.window, threshold=config.threshold)
    if isinstance(config, ConnorsRSIConfig):
        return ConnorsRSIStrategy(
            window=config.window,
            oversold=config.oversold,
            overbought=config.overbought,
        )
    # Defensive catch-all. Unreachable as long as StrategyConfig stays in lockstep with
    # the isinstance chain above; the catalog-consistency test enforces that. A missing
    # branch here would surface as this exception in dev rather than a silent wrong type.
    raise ValueError(  # pragma: no cover
        f"unhandled StrategyConfig variant: {type(config).__name__}"
    )


def build_strategy_from_dict(name: str, params: dict[str, int | float]) -> BaseStrategy:
    """Validate `{name, ...params}` through Pydantic then construct the strategy.

    Notes:
        Used by the catalog-driven /validate grid path. Raises Pydantic's
        ValidationError on an unknown discriminator or invalid param value, and
        ValueError if the strategy constructor itself rejects a cross-parameter
        combination (e.g. SMA `fast >= slow`).
    """
    config = _StrategyConfigAdapter.validate_python({"name": name, **params})
    return build_strategy(config)
