from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.backtest import router as backtest_router
from app.api.v1.bars import router as bars_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.monte_carlo import router as monte_carlo_router
from app.api.v1.strategies import router as strategies_router
from app.api.v1.validation import router as validation_router
from app.config import get_settings

app = FastAPI(title="QuantForge", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(validation_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(bars_router, prefix="/api/v1")
app.include_router(backtest_router, prefix="/api/v1")
app.include_router(strategies_router, prefix="/api/v1")
app.include_router(monte_carlo_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "environment": settings.environment}
