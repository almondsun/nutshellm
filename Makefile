.PHONY: install api web test lint typecheck build docker

install:
	python -m pip install -e ".[dev]"
	cd frontend && npm ci

api:
	uvicorn nutshellm.main:app --host 127.0.0.1 --port 8000 --reload

web:
	cd frontend && npm run dev

test:
	pytest -q

lint:
	ruff check backend tests
	cd frontend && npm run lint

typecheck:
	cd frontend && npm run typecheck

build:
	cd frontend && npm run build

docker:
	docker build -t nutshellm .
