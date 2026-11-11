PYTHON ?= python
export PYTHONPATH := src
export PYTHONDONTWRITEBYTECODE := 1

.PHONY: test run check seed market-sync market-snapshot modules report

test:
	$(PYTHON) -m pytest

run:
	$(PYTHON) run.py

check:
	$(PYTHON) -m finserve check

seed:
	$(PYTHON) -m finserve seed --reset

modules:
	$(PYTHON) -m finserve modules

market-sync:
	$(PYTHON) -m finserve market-sync

market-snapshot:
	$(PYTHON) -m finserve market-snapshot

report:
	$(PYTHON) -m finserve report
