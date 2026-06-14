.PHONY: install test serve init demo

install:
	pip install -r requirements.txt

test:
	pytest -q

serve:
	uvicorn app.main:app --host 0.0.0.0 --port 8091 --reload

init:
	python cli.py init

demo: init
	python cli.py products
	python cli.py trends --category pool_floats
	python cli.py plan pool-paradise --count 3
	python cli.py report --json
