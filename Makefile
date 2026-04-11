.PHONY: install test lint format clean

install:
	python -m pip install -e .[dev]

test:
	python -m pytest

lint:
	python -m ruff check .

format:
	python -m black .
	python -m isort .

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
