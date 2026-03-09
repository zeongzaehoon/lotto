from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.mongodb import close_database
from app.routers import predict, train, models, mlops, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_database()


app = FastAPI(
    title="Lotto ML Service",
    description="모델 학습, 예측, MLflow Registry 관리",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router)
app.include_router(train.router)
app.include_router(models.router)
app.include_router(mlops.router)
app.include_router(ws.router)


@app.get("/ml/health")
async def health():
    return {"status": "ok"}
