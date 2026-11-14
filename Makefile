.PHONY: setup db-up db-reset psql generate validate repro load test lint dev build down

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

setup generate validate repro load test lint dev build down:
	@echo "TODO: implement the $@ target."
