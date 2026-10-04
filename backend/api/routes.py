from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import settings
from graph.maana_graph import WorkflowStageError
from graph.progress import get_progress
from llm import LLMError
from llm.client import DEFAULT_MODELS
from rag.retriever import get_retriever
from rag.schemas import SourceFile
from services.session_service import dashboard, get_workflow, persist, session_view

logger = logging.getLogger("maana.api")

router = APIRouter(prefix="/api")

LLM_ERRORS = {
    "no_key": "لم يُضبط مفتاح نموذج اللغة في الخادم. أضف المفتاح في ملف backend/.env ثم أعد تشغيل الخادم.",
    "rate_limit": "بلغ مزوّد نموذج اللغة حدّ الاستخدام المسموح مؤقتًا. انتظر دقيقة ثم أعد المحاولة.",
    "invalid_output": "لم يُرجع نموذج اللغة نتيجة صالحة بعد عدة محاولات. أعد المحاولة بعد قليل.",
    "refused": "رفض نموذج اللغة معالجة هذا الطلب.",
    "config": "إعدادات مزوّد نموذج اللغة في الخادم غير صحيحة.",
    "provider": "تعذّر الاتصال بمزوّد نموذج اللغة. أعد المحاولة بعد قليل.",
}
SESSION_NOT_FOUND = "الجلسة غير موجودة."
STAGE_CONFLICT = "هذه الخطوة غير متاحة في المرحلة الحالية من الاختبار. حدّث الصفحة وتابع من حيث توقفت."


class AnalyzeContentRequest(BaseModel):
    content: str = Field(min_length=5, max_length=4000)
    content_language: str = "Arabic"
    target_language: str = "Arabic"
    session_id: str | None = None


class ResponseRequest(BaseModel):
    session_id: str
    response: str = Field(min_length=2, max_length=3000)


class SessionRequest(BaseModel):
    session_id: str


def _run(session_id: str, action):
    try:
        action()
    except WorkflowStageError as exc:
        raise HTTPException(status_code=409, detail=STAGE_CONFLICT) from exc
    except LLMError as exc:
        logger.error("LLM error (%s): %s", exc.code, exc)
        raise HTTPException(status_code=502, detail=LLM_ERRORS.get(exc.code, LLM_ERRORS["provider"])) from exc
    view = session_view(session_id)
    if view is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)
    persist(view)
    return view


def _require(session_id: str) -> None:
    if session_view(session_id) is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)


@router.get("/health")
def health():
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model or DEFAULT_MODELS.get(settings.llm_provider, ""),
        "llm_configured": bool(settings.llm_api_key),
        "embedding_provider": settings.embedding_provider,
        "vector_index_ready": (settings.index_dir / "faiss.index").exists(),
        "app_env": settings.app_env,
        "review_filter": sorted(settings.allowed_review_statuses),
        "demo_mode": settings.demo_mode,
    }


@router.post("/content/analyze")
def analyze_content(req: AnalyzeContentRequest):
    session_id = req.session_id or uuid.uuid4().hex
    if session_view(session_id) is not None:
        raise HTTPException(status_code=409, detail="معرّف الجلسة مستخدم مسبقًا.")
    return _run(
        session_id,
        lambda: get_workflow().start(session_id, req.content.strip(), req.content_language, req.target_language),
    )


@router.post("/understanding/analyze")
def analyze_understanding(req: ResponseRequest):
    _require(req.session_id)
    return _run(req.session_id, lambda: get_workflow().submit_response(req.session_id, req.response.strip()))


@router.post("/content/refine")
def refine_content(req: SessionRequest):
    _require(req.session_id)
    return _run(req.session_id, lambda: get_workflow().refine(req.session_id))


@router.post("/understanding/retest")
def retest_understanding(req: ResponseRequest):
    _require(req.session_id)
    return _run(req.session_id, lambda: get_workflow().submit_retest(req.session_id, req.response.strip()))


@router.get("/session/{session_id}")
def get_session(session_id: str):
    view = session_view(session_id)
    if view is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)
    return view


@router.get("/session/{session_id}/progress")
def get_session_progress(session_id: str):
    return get_progress(session_id)


@router.get("/dashboard")
def get_dashboard():
    return dashboard()


@router.get("/sources")
def get_sources():
    docs = []
    for path in sorted(settings.sources_dir.glob("*.json")):
        sf = SourceFile.model_validate_json(path.read_text(encoding="utf-8"))
        docs.extend({"topic": sf.topic, **d.model_dump()} for d in sf.documents)
    return {
        "topics": get_retriever().topics,
        "production_filter": sorted(settings.allowed_review_statuses),
        "documents": docs,
    }


@router.get("/demo")
def get_demo():
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="وضع الأمثلة غير مفعّل.")
    path = settings.sources_dir.parent / "demo_inputs.json"
    return json.loads(path.read_text(encoding="utf-8"))
