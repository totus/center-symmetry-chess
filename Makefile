PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
RUN := $(VENV)/bin/python

.PHONY: setup install-engines validate probe match tournament parse aggregate ratings report test lint fmt clean

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

install-engines:
	bash scripts/install_engines.sh

validate:
	$(RUN) scripts/validate_variant.py --variant swapped_white

probe:
	$(RUN) scripts/depth_probe.py --config configs/probe_swapped_white.yaml

match:
	$(RUN) scripts/run_matches.py --config configs/match_swapped_white.yaml

tournament:
	$(RUN) scripts/run_tournament.py --config configs/tournament.yaml

parse:
	$(RUN) scripts/parse_pgn.py --input data/raw --output data/processed/games.csv

aggregate:
	$(RUN) scripts/aggregate_results.py --games data/processed/games.csv --output data/processed/summary.csv

ratings:
	$(RUN) scripts/compute_ratings.py --games data/processed/games.csv --output data/processed/ratings.csv

report:
	$(RUN) scripts/generate_report.py --config configs/report.yaml --output data/reports/final_report.md

test:
	$(RUN) -m pytest

lint:
	$(VENV)/bin/ruff check src tests scripts
	$(VENV)/bin/mypy src

clean:
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov
