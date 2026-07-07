"""The market-data adapter factory (ADR-019): Alpaca when keyed, else yfinance. Settings are
constructed with _env_file=None so the test is isolated from any local .env."""

from app.config import Settings
from app.data.sources.alpaca import AlpacaDataAdapter
from app.data.sources.yfinance import YFinanceAdapter
from app.dependencies import build_data_adapter


def test_uses_alpaca_when_keys_are_configured() -> None:
    settings = Settings(alpaca_api_key="k", alpaca_secret_key="s", _env_file=None)
    assert isinstance(build_data_adapter(settings), AlpacaDataAdapter)


def test_falls_back_to_yfinance_without_keys() -> None:
    settings = Settings(alpaca_api_key="", alpaca_secret_key="", _env_file=None)
    assert isinstance(build_data_adapter(settings), YFinanceAdapter)


def test_partial_keys_fall_back_to_yfinance() -> None:
    settings = Settings(alpaca_api_key="k", alpaca_secret_key="", _env_file=None)
    assert isinstance(build_data_adapter(settings), YFinanceAdapter)
