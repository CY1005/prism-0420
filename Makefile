.PHONY: install dev test lint format check clean

install:
	uv sync

dev:
	uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: lint test

clean:
	rm -rf .pytest_cache .ruff_cache .venv __pycache__ */__pycache__
