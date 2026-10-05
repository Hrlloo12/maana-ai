from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router
from config import settings
from db.database import init_db

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("maana")

INPUT_ERROR = "المدخلات غير صالحة. تأكد من أن النص ليس قصيرًا جدًا (5 أحرف على الأقل) ولا طويلًا جدًا."
SERVER_ERROR = "حدث خطأ غير متوقع في الخادم. أعد المحاولة بعد قليل."


@asynccontextmanager
async def lifespan(_: FastAPI):
    from rag.retriever import get_retriever

    init_db()
    get_retriever()
    yield


app = FastAPI(
    title="MA'NA | معنى",
    description="LLM + RAG + Multi-Agent meaning-gap detection.",
    version="1.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def invalid_input(_: Request, exc: RequestValidationError):
    logger.info("Invalid request: %s", exc.errors())
    return JSONResponse(status_code=422, content={"detail": INPUT_ERROR})


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": SERVER_ERROR})


SITE_DIR = Path(__file__).resolve().parent / "site"

if SITE_DIR.is_dir():
    app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")
else:

    @app.get("/")
    def root():
        return {"name": "MA'NA", "docs": "/docs", "health": "/api/health"}
