from fastapi import FastAPI

from app.config import get_settings

app = FastAPI(title="QuantForge", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "environment": settings.environment}
