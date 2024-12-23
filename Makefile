VENV := venv/bin/activate

format: venv
	. $(VENV) && black app && isort app

lint: venv
	. $(VENV) && flake8 app && pylint app

venv:
	python3 -m venv venv
	. $(VENV) && pip install -r requirements.txt && pip install -r requirements-dev.txt

run: venv
	. $(VENV) && uvicorn app.main:app --reload --port 8000

all: venv format lint
