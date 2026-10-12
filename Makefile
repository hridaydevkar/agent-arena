.PHONY: run setup test lint web docker
run:
	python3 scripts/start.py
setup:
	python3 scripts/start.py --check
web:
	cd frontend && npm ci && npm run build
test:
	python -m pytest -q
lint:
	ruff check backend sdk tests scripts examples
docker:
	docker compose up --build
