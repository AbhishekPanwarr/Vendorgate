.PHONY: setup dev lint test test-all e2e ci ci-e2e deploy seed datagen eval

setup:
	uv sync --extra dev || pip install -e ".[dev]"
	npm --prefix frontend install || true
	pre-commit install || true

dev:
	uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
	npm --prefix frontend run dev -- --port 5173 --proxy '{"\/api":"http://localhost:8000"}' || npm --prefix frontend run dev

lint:
	ruff check .
	ruff format --check .
	mypy backend/app/domain backend/app/core backend/app/pipeline backend/app/decision backend/app/adapters backend/app/matching backend/app/risk backend/app/persistence backend/app/validators backend/app/api backend/app/comms backend/app/screening backend/app/network backend/app/llm backend/app/ingest backend/app/scheduler

test:
	pytest -q

coverage:
	pytest -q --cov=backend/app/validators --cov=backend/app/matching --cov=backend/app/risk --cov=backend/app/decision --cov=backend/app/adapters --cov=backend/app/network --cov=backend/app/comms --cov=backend/app/screening --cov=backend/app/ingest --cov=backend/app/llm --cov=backend/app/scheduler --cov=backend/app/pipeline --cov-report=term --cov-fail-under=90

test-all: test e2e

e2e:
	playwright test || pytest -q backend/tests/e2e

ci: lint test
	npm --prefix frontend run typecheck 2>/dev/null || npx --prefix frontend tsc --noEmit || true

ci-e2e:
	VG_BASE_URL=$${VG_BASE_URL:?set VG_BASE_URL} pytest -q backend/tests/e2e

deploy:
	curl -fsS -X POST "$${RENDER_DEPLOY_HOOK}" -o /dev/null -w "deploy triggered\n"

seed:
	python -c "print('seed: Phase 1+')"

datagen:
	python -c "print('datagen: Phase 5')"

eval:
	python -c "print('eval: Phase 5')"

demo:
	docker compose up --build
