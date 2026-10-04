# MA'NA | مَعنى

> **Did the meaning actually arrive?** · هل وصل المعنى بأمانة؟

MA'NA measures the gap between **the meaning Islamic content intends** and **what the audience actually understood**. It proves each gap with trusted sources, diagnoses *why* the misunderstanding happened, chooses the best way to explain it again (simplification, comparison, example, visual or step by step), re-tests the reader with the same question and measures the improvement.

```
المحتوى → تحديد المعنى المقصود → اختبار الفهم → اكتشاف فجوة الفهم → التحقق بالمصادر
       → تحديد سبب الالتباس → اختيار أفضل طريقة للشرح → إعادة الشرح → إعادة الاختبار → قياس التحسن
```

> **ملاحظة للمحكّمين:** يعمل النظام بنموذج لغوي حقيقي، لذلك يحتاج مفتاح API خاصًا بكم. انسخوا `backend/.env.example` إلى `backend/.env` وضعوا المفتاح في `LLM_API_KEY`. لا توجد أي مفاتيح داخل المستودع. واجهة الموقع عربية بالكامل ومن اليمين إلى اليسار.

---

## 1. The problem

Islamic content can be linguistically correct and well translated and still be misunderstood:

> Content: *«الزكاة صدقة يخرجها المسلم من ماله.»*
> Reader: *«الزكاة تبرع يدفعه المسلم إذا أراد.»*

Every word arrived, but the meaning did not: the word «صدقة» led the reader to think Zakat is optional, while it is an obligatory pillar. MA'NA detects this, proves it from the sources, and explains it again in the way that fits the cause.

**Key principle:** MA'NA does not test the reader's Islamic knowledge. Only meanings the content itself states are scored. Background knowledge retrieved by RAG is context and never becomes a requirement.

## 2. Architecture

LLM + RAG + Multi-Agent, orchestrated by **LangGraph** with human-in-the-loop interrupts and a SQLite checkpointer.

```mermaid
flowchart TD
    S([START]) --> R[retrieve_knowledge · strict RAG]
    R -->|evidence passes all gates| M[Meaning Agent]
    R -->|no covered topic / no relevant evidence| A[safe_abstention]
    M -->|intended meaning grounded in the text| W1{{WAIT: reader answer}}
    M -->|nothing grounded| A
    W1 --> U[Understanding Agent]
    U --> V[Verification Agent]
    V -->|understood| F[finalize]
    V -->|claims unsupported| A
    V -->|partial / major gap| W2{{WAIT: re-explain}}
    W2 --> RF[Refinement Agent · adaptive explanation]
    RF --> W3{{WAIT: re-test, same question}}
    W3 --> U2[Understanding Agent]
    U2 --> V2[Verification Agent]
    V2 --> F
    A --> F --> E([END])
```

| Agent | File | Sees | Produces |
|---|---|---|---|
| Meaning | `agents/meaning_agent.py` | content, evidence | intended concepts quoted from the content (weights sum to 1), background knowledge and ambiguities (each with a verbatim evidence quote), neutral question |
| Understanding | `agents/understanding_agent.py` | what the reader read, their answer. **No knowledge base** | neutral description of the reader's interpretation |
| Verification | `agents/verification_agent.py` | intended concepts, interpretation, evidence | gap type per concept, misunderstandings with verbatim evidence quotes; score and status computed in code |
| Refinement | `agents/refinement_agent.py` | original content, verified gaps, cited evidence | root cause, explanation strategy, new explanation (+ comparison table / steps / example / diagram), supporting quotes |

### 2.1 Adaptive explanation

The Refinement Agent diagnoses **why** the misunderstanding happened and chooses a strategy that fits the cause. Code enforces the mapping and falls back safely when the model ignores it:

| Root cause | Allowed strategies |
|---|---|
| concept_confusion (e.g. Hajj = Umrah) | comparison |
| ambiguous_wording (e.g. «صدقة» read as optional) | simplification, comparison, example |
| abstract_concept | example, visual, simplification |
| missing_context | simplification, example, step_by_step |
| complex_process | step_by_step, visual |
| overgeneralization | example, comparison, simplification |

The reader is then re-tested with **the same neutral question** as the first time, so before and after are directly comparable and the question cannot leak the answer. The re-test is scored against the same intended concepts and evidence; each earlier misunderstanding is marked *resolved*, *partially resolved* or *remains*, and newly missing meanings are reported as remaining gaps.

### 2.2 Strict RAG

`rag/pipeline.py`:

1. **Topic gate.** The planner must map the content to one covered topic (topics carry descriptions). Content about uncovered subjects (prayer, music, inheritance, food) abstains immediately, even if it mentions a covered word in passing.
2. **Multi-query dense search** (multilingual embeddings, FAISS cosine) restricted to the primary topic and at most one commonly confused topic.
3. **Rule filters:** absolute threshold (`RAG_MIN_RELEVANCE=0.5`), relative margin from the best primary-topic hit (`0.15`), the chunk must mention the concept's key terms, one chunk per document, near-duplicate removal.
4. **Relevance grading:** an LLM grader rejects passages about a different practice that only shares a word (e.g. voluntary fasts for content about Ramadan, Zakat al-Fitr for content about Zakat in general).
5. **At most 4 chunks.** Every decision (kept / below threshold / off concept / duplicate / judged irrelevant…) is stored and shown on the technology page.

If nothing survives, the answer is **«تعذر التحقق من خلال المصادر المتاحة»**.

### 2.3 Validation between agents

`agents/base.py:call_validated` runs a validator on every agent output before it reaches the next agent:

- schema validity (Pydantic), with repair of malformed JSON and retries;
- intended concepts must be quoted from the content itself (Arabic-aware normalisation), so background facts cannot become scored meaning;
- no duplicate concepts or misunderstandings; weights normalised to sum to 1;
- one judgement per concept, no unknown IDs, no contradictions (a concept affected by a misunderstanding cannot be judged correct);
- every religious claim (background, ambiguity, confusion, ambiguity-triggered gap, refinement fact) must carry a quote that code finds **verbatim** in a cited chunk; otherwise it is rejected and logged in `rejected_claims`;
- the refinement strategy must fit the root cause and include the fields that strategy needs.

An invalid output gets one corrective retry with the exact issues listed; anything still invalid is corrected deterministically. Every validation is recorded in `validation_log`.

## 3. Evaluation

```bash
cd backend
python -m evaluation.evaluator                    # full system, real LLM
python -m evaluation.evaluator --cases id1,id2    # selected cases
python -m evaluation.evaluator --retrieval-only   # dense retrieval only, no API key
```

`evaluation/dataset.json` holds 25 cases written before running the system: correct, partial and wrong understanding, concept confusion, ambiguous content, irrelevant retrieval, insufficient evidence, correct abstention, unverifiable extra claims, an evasive answer, a re-test where the reader is still confused, Arabic and English content. Every metric is computed in code from the real outputs; citations and quotes are re-verified independently against the source text. No LLM judges the system.

**Last complete run** (25 cases, `gemini-3.5-flash-lite`, 2026-10-03). Two guards were added after this run (misunderstandings must quote the reader's own words, and a restriction such as "only" cannot be attributed to a reader who never said it); they target the two remaining false positives. A re-run on the final code was cut short by the free tier's daily quota, so run the evaluator again with a working key to regenerate `results/latest.*`.

| Metric | Result |
|---|---|
| Intended Concept Extraction | 100% |
| Background leakage into intended meaning | 0% |
| Meaning Gap Detection Accuracy (status) | 96% (24/25) |
| Gap Type Accuracy | 90% |
| RAG topic gate accuracy | 100% |
| RAG Relevance (precision of kept evidence) | 96.3% |
| Irrelevant retrieval rejected (out-of-scope content) | 100% |
| Citation Correctness (103 citations re-verified) | 100% |
| Unsupported Claim Rate (70 claims re-verified) | 0% |
| Abstention Accuracy / precision / recall | 100% / 100% / 100% |
| Refinement: strategy fits the cause | 100% |
| Refinement Relevance | 100% |
| Before/After: misunderstanding resolved or partially resolved (incl. a still-confused reader correctly reported as "remains") | 100% |
| Mean alignment before → after (12 re-tested cases) | 16.7% → 91.7% (+75 points) |
| Agent outputs valid on first attempt / after correction | 97.9% / 100% |

The one status miss in that run was a reader who restated the content correctly ("Hajj is travel to Makkah") but was flagged for not mentioning worship. That is exactly the background-penalty error MA'NA must avoid, and it is what the two new guards block.

Running the evaluator writes per-case output to `evaluation/results/latest.json` and a summary to `evaluation/results/latest.md`. `incomplete-quota-exhausted.*` is the interrupted re-run, kept for transparency.

Automated tests (fake LLM, real FAISS index): graph flow, validators, quote verification, strict retrieval filters, strategy correction, Arabic API errors.

```bash
cd backend && python -m pytest -q
```

## 4. Running locally

Requirements: Python 3.12+, Node 18+.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env, then set LLM_API_KEY
python -m rag.ingest
uvicorn main:app --port 8000
```

```bash
cd frontend
copy .env.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                       # http://localhost:3000
```

### Environment variables (`backend/.env`)

| Variable | Meaning |
|---|---|
| `LLM_PROVIDER` | `openai` (or any OpenAI-compatible API with `LLM_BASE_URL`), `gemini`, `anthropic` |
| `LLM_API_KEY` | your key (required) |
| `LLM_MODEL` | optional; provider default otherwise |
| `LLM_BASE_URL` | optional, for OpenAI-compatible providers |
| `LLM_TEMPERATURE`, `LLM_TIMEOUT` | generation settings |
| `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` | `local` multilingual ONNX model by default (no key) |
| `RAG_TOP_K`, `RAG_MIN_RELEVANCE`, `RAG_RELATIVE_MARGIN` | retrieval strictness (4, 0.5, 0.15) |
| `APP_ENV` | `production` uses only sources with `review_status: reviewed` |
| `DEMO_MODE` | exposes sample inputs on the analyze page |
| `CORS_ORIGINS` | allowed frontend origins |

## 5. Knowledge base

`backend/data/sources/*.json`, one file per topic, each with a description used by the topic gate. Every document has Arabic and English source names and references and a review status. The MVP covers Zakat, Sadaqah, Fasting, Hajj and Tawhid (Qur'an in the Sahih International translation; hadith from Bukhari, Muslim, Abu Dawud and Tirmidhi) and must be replaced by officially reviewed sources before real-world use. Add a file and run `python -m rag.ingest`; no prompt changes are needed.

## 6. Deployment

- **Backend → Render:** `render.yaml` (build, ingestion, start). Set `LLM_API_KEY` in the dashboard and `CORS_ORIGINS` to the frontend URL.
- **Frontend → Netlify:** base directory `frontend`, `netlify.toml` builds the static export; set `NEXT_PUBLIC_API_URL` to the backend URL.

## 7. Project structure

```
maana-ai/
├── backend/
│   ├── agents/        meaning, understanding, verification, refinement, validation helpers, text normalisation
│   ├── graph/         LangGraph workflow, state, live progress
│   ├── rag/           ingestion, embeddings, retriever, strict pipeline
│   ├── llm/           provider-independent client
│   ├── scoring/       Meaning Alignment Score
│   ├── evaluation/    dataset, evaluator, results
│   ├── db/, services/ dashboard persistence
│   ├── api/           FastAPI routes (Arabic error messages)
│   ├── data/          sources and demo inputs
│   └── tests/
├── frontend/          Next.js 14 static export, TypeScript, Tailwind, Arabic RTL UI
└── render.yaml
```

**API:** `POST /api/content/analyze` · `POST /api/understanding/analyze` · `POST /api/content/refine` · `POST /api/understanding/retest` · `GET /api/session/{id}` · `GET /api/session/{id}/progress` · `GET /api/dashboard` · `GET /api/sources` · `GET /api/demo` · `GET /api/health`
