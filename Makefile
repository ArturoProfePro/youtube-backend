.PHONY=migrate,revision,dev,test,docker-up,docker-down,docker-build,keygen

keygen:
	uv run python scripts/keygen.py $(ARGS)


test:
	uv run pytest --cov-report html --cov=youtube tests

all-test:
	uv run pytest --cov-report html --cov=youtube tests

dev:
	uv run uvicorn youtube.main:app --reload

debug:
	uv run python -Xfrozen_modules=off -m debugpy --listen 127.0.0.1:5678 -m uvicorn youtube.main:app --reload

revision:
	uv run alembic revision --autogenerate -m $(NAME)

migrate:
	uv run alembic upgrade head

rollback:
	uv run alembic downgrade $(NUM)

HOST ?= 0.0.0.0
PORT ?= 8080
start:
	uv run uvicorn youtube.main:app --host $(HOST) --port $(PORT)

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
