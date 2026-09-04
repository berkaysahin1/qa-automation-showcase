.PHONY: install run test api e2e headed report lint clean

VENV ?= .venv
PY   := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest

install:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip -q
	$(PY) -m pip install -r requirements-dev.txt -q
	$(PY) -m playwright install chromium

run:
	TASKFLOW_TEST_MODE=1 $(PY) -m uvicorn app.main:app --reload --port 8000

test:
	$(PYTEST)

api:
	$(PYTEST) -m api -n auto

e2e:
	$(PYTEST) -m e2e --tracing=retain-on-failure

headed:
	$(PYTEST) -m e2e --headed --slowmo 250

report:
	$(PYTEST) --html=reports/report.html --self-contained-html

lint:
	$(VENV)/bin/ruff check app tests

clean:
	rm -rf reports test-results .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
