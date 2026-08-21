from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from mind_recovery_mvp.db import SessionLocal, init_db
from mind_recovery_mvp.loader import load_seed_data


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    with SessionLocal() as session:
        load_seed_data(session)
    yield


app = FastAPI(title="Mind Recovery MVP", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
