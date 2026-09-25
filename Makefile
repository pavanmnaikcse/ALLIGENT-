.PHONY: help install test lint run build up down clean

help:
	@echo "ALLIGENT — Automation & Build Tasks"
	@echo "  install   Install backend and frontend dependencies"
	@echo "  test      Run backend test suite"
	@echo "  run       Run backend server locally (uvicorn)"
	@echo "  up        Start all services using Docker Compose"
	@echo "  down      Stop all Docker Compose services"
	@echo "  clean     Remove python cache and temporary files"

install:
	pip install -r backend/requirements.txt || pip install -r requirements.txt
	cd frontend && npm install || true

test:
	python -m pytest tests/ -v

run:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

up:
	docker compose up -d --build

down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
