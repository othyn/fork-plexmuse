format:
	black .
	isort .

lint:
	flake8 .
	pylint app

all: format lint
