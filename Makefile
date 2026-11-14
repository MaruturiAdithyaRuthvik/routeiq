.PHONY: setup db-up db-reset psql generate validate repro load test lint dev build up down

up:
	@test -f .env || cp .env.example .env
	docker compose up -d --build --wait

db-up:
	@test -f .env || cp .env.example .env
	docker compose up -d --wait db

db-reset:
	@test -f .env || cp .env.example .env
	docker compose down -v
	docker compose up -d --wait db

psql:
	@test -f .env || cp .env.example .env
	docker compose exec db sh -c 'exec psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

setup:
	cd backend && uv sync

generate:
	cd backend && uv run python -m app.datagen --seed 20261022 --scale full --out ../data

validate:
	cd backend && uv run python -m app.datagen.validate --data ../data

repro:
	cd backend && uv run python ../scripts/repro.py

load:
	cd backend && uv run python -m app.db.load --from ../data/csv

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check app tests

dev:
	cd backend && uv run python -m app.api.main

build:
	cd frontend && npm run build

down:
	docker compose down
