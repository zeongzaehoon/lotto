import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.mongodb import close_database
from app.routers import lotto, prediction, stats, mlops, collection

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_database()


app = FastAPI(
    title="Lotto Prediction API",
    description="로또 번호 예측 서비스 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(lotto.router)
app.include_router(stats.router)
app.include_router(prediction.router)
app.include_router(mlops.router)
app.include_router(collection.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
