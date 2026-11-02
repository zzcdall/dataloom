PYTHON ?= python

.PHONY: install backend frontend test build run docker

install:
	$(PYTHON) -m pip install -e "backend[dev]"
	cd frontend && npm install

backend:
	$(PYTHON) -m uvicorn app.main:app --app-dir backend --reload

frontend:
	cd frontend && npm run dev

test:
	$(PYTHON) -m pytest backend/tests

build:
	cd frontend && npm run build

run:
	$(PYTHON) -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000

docker:
	docker compose up --build

