.PHONY: install dev test lint format check clean up down logs migrate migrate-down migrate-rev web web-test web-lint web-format hooks

install:
	uv sync

up:
	docker compose up -d
	@echo "等待 PG/Redis 就绪..."
	@sleep 3

down:
	docker compose down

logs:
	docker compose logs -f

dev:
	uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

migrate-rev:
	uv run alembic revision -m "$(m)"

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: lint test

web:
	cd app && pnpm dev

web-test:
	cd app && pnpm test

web-lint:
	cd app && pnpm lint

web-format:
	cd app && pnpm format

hooks:
	uv run pre-commit install
	uv run pre-commit run --all-files

clean:
	rm -rf .pytest_cache .ruff_cache .venv __pycache__ */__pycache__
