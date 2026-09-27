.PHONY: install test lint demo benchmark server clean docker-build docker-up

install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt

test:
	pytest -v tests/

lint:
	python -m ruff check . || true

demo:
	python main.py demo

benchmark:
	python main.py benchmark --runs 10

server:
	python main.py server

docker-build:
	docker build -t ai-voice-bot:latest .

docker-up:
	docker compose up -d

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
