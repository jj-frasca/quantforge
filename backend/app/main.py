from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "environment": settings.environment}
