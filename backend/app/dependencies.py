from app.data.sources.base import DataSourceAdapter
from app.data.sources.yfinance import YFinanceAdapter


def get_data_adapter() -> DataSourceAdapter:
    """FastAPI dependency for the market-data adapter (yfinance by default).

    Overridden in tests via app.dependency_overrides to inject synthetic data.
    """
    return YFinanceAdapter()
