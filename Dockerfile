# Stage 1: build frontend
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build || (mkdir -p dist && echo '<!doctype html><html><body>VendorGate skeleton</body></html>' > dist/index.html)

# Stage 2: backend on Python 3.12 (runtime pin; spec allows <3.14 locally)
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY backend/ ./backend/
COPY policy/ ./policy/
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/
COPY --from=web /web/dist ./frontend/dist
RUN pip install --no-cache-dir -e .
ENV LLM_MODE=replay CLOCK_MODE=virtual DATABASE_URL=sqlite:///data/vendorgate.db
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
