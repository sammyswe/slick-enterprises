.PHONY: install test serve cli

install:
	pip install -r requirements.txt

test:
	pytest -q

serve:
	uvicorn app.main:app --host 0.0.0.0 --port 8088 --reload

cli:
	python cli.py $(URL)
