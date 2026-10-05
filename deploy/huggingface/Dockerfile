FROM node:20-slim AS site
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_PUBLIC_API_URL=same-origin
RUN npm run build

FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user backend/ ./
COPY --from=site --chown=user /app/frontend/out ./site
USER user
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    LLM_PROVIDER=openai \
    LLM_MODEL=gpt-4.1 \
    EMBEDDING_PROVIDER=local \
    APP_ENV=production \
    CORS_ORIGINS=*
RUN python -m rag.ingest
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
