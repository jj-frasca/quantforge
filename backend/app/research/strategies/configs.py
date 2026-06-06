"""Pydantic configs that mirror the strategy classes 1:1 for the wire layer.

Notes:
    These models live next to the strategy implementations (not under the API layer)
    because (a) /backtest and /validate both need them, (b) the StrategyConfig
    discriminated union is a domain artifact more than an HTTP artifact, and (c) it
    avoids a cross-layer import from app/api -> app/research that would otherwise be
    odd. See ADR-010 for the catalog-as-source-of-truth pattern.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class SMAConfig(BaseModel):
    name: Literal["sma"] = "sma"
    fast: int = Field(default=20, ge=1)
    slow: int = Field(default=50, ge=2)


class MomentumConfig(BaseModel):
    name: Literal["momentum"] = "momentum"
    lookback: int = Field(default=60, ge=1)
    skip: int = Field(default=5, ge=0)


class MeanReversionConfig(BaseModel):
    name: Literal["mean_reversion"] = "mean_reversion"
    window: int = Field(default=20, ge=2)
    k: float = Field(default=2.0, gt=0)


class RSIMeanReversionConfig(BaseModel):
    name: Literal["rsi_mean_reversion"] = "rsi_mean_reversion"
    window: int = Field(default=14, ge=2)
    oversold: float = Field(default=30.0, gt=0, lt=100)
    overbought: float = Field(default=70.0, gt=0, lt=100)


class DonchianBreakoutConfig(BaseModel):
    name: Literal["donchian_breakout"] = "donchian_breakout"
    lookback: int = Field(default=20, ge=2)


class BollingerBandsConfig(BaseModel):
    name: Literal["bollinger_bands"] = "bollinger_bands"
    window: int = Field(default=20, ge=2)
    num_std: float = Field(default=2.0, gt=0)


class MACDCrossoverConfig(BaseModel):
    name: Literal["macd_crossover"] = "macd_crossover"
    fast: int = Field(default=12, ge=1)
    slow: int = Field(default=26, ge=2)
    signal: int = Field(default=9, ge=1)


class VolTargetedSMAConfig(BaseModel):
    name: Literal["vol_targeted_sma"] = "vol_targeted_sma"
    fast: int = Field(default=20, ge=1)
    slow: int = Field(default=50, ge=2)
    vol_window: int = Field(default=30, ge=2)
    target_vol: float = Field(default=0.15, gt=0)


class KeltnerChannelConfig(BaseModel):
    name: Literal["keltner_channel"] = "keltner_channel"
    ma_window: int = Field(default=20, ge=1)
    atr_window: int = Field(default=14, ge=2)
    multiplier: float = Field(default=2.0, gt=0)


class TrendFilteredMeanReversionConfig(BaseModel):
    name: Literal["trend_filtered_mean_reversion"] = "trend_filtered_mean_reversion"
    z_window: int = Field(default=20, ge=2)
    z_threshold: float = Field(default=1.5, gt=0)
    trend_window: int = Field(default=100, ge=2)


class TripleMAAlignmentConfig(BaseModel):
    name: Literal["triple_ma_alignment"] = "triple_ma_alignment"
    fast: int = Field(default=10, ge=1)
    medium: int = Field(default=30, ge=2)
    slow: int = Field(default=100, ge=3)


StrategyConfig = Annotated[
    SMAConfig
    | MomentumConfig
    | MeanReversionConfig
    | RSIMeanReversionConfig
    | DonchianBreakoutConfig
    | BollingerBandsConfig
    | MACDCrossoverConfig
    | VolTargetedSMAConfig
    | KeltnerChannelConfig
    | TrendFilteredMeanReversionConfig
    | TripleMAAlignmentConfig,
    Field(discriminator="name"),
]
