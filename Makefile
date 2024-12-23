VENV := venv/bin/activate
PYTHON := python3

.PHONY: venv requirements dev-requirements format lint test run all clean

venv:
	$(PYTHON) -m venv venv

requirements: venv
	. $(VENV) && pip install --upgrade pip
	. $(VENV) && pip install -r requirements.txt

dev-requirements: requirements
	. $(VENV) && pip install -r requirements-dev.txt

format: dev-requirements
	. $(VENV) && black app && isort app

lint: dev-requirements
	. $(VENV) && flake8 app && pylint app

test: dev-requirements
	. $(VENV) && pytest

run: requirements
	. $(VENV) && uvicorn app.main:app --reload --port 8000

clean:
	rm -rf venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

all: format lint test
