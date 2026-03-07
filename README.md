# Center Symmetry Chess Research Harness

Local, reproducible research pipeline to evaluate the chess variant where White starts with king/queen swapped.

## Variant definitions

- `orthodox`: normal chess
- `swapped_white`: White back rank `R N B K Q B N R`
- `swapped_black`: Black back rank `R N B K Q B N R`
- `swapped_both`: both sides swapped

Castling uses Chess960-style legality with orthodox destination squares:
- White O-O -> king `g1`, rook `f1`
- White O-O-O -> king `c1`, rook `d1`
- Black O-O -> king `g8`, rook `f8`
- Black O-O-O -> king `c8`, rook `d8`

## Quick start

```bash
make setup
make validate
make test
```

## Engine setup

Install Fairy-Stockfish (example via Homebrew on macOS):

```bash
brew install fairy-stockfish
mkdir -p engines/bin
ln -sf "$(command -v fairy-stockfish)" engines/bin/fairy-stockfish
```

Verify engine wiring:

```bash
./engines/bin/fairy-stockfish --help >/dev/null
make validate
```

If you do not want a symlink, edit `engine.path` in the `configs/*.yaml` files.

## Run experiments

### Single experiment (default swapped White)

```bash
make probe
make match
```

### Multi-variant batch

```bash
make tournament
```

This runs all configs listed in `configs/tournament.yaml` (`orthodox`, `swapped_white`, `swapped_black`, `swapped_both`) and writes PGNs/logs to `data/raw/`.

## Parse and aggregate

```bash
make parse
make aggregate
```

`make aggregate` writes:
- `data/processed/summary.csv`
- `data/processed/openings.csv`

## Compute ratings

```bash
make ratings
```

Writes `data/processed/ratings.csv` with score, Elo estimate, CI, and LoS proxy.

## Generate report

```bash
make report
```

Writes `data/reports/final_report.md` using `configs/report.yaml`.

## End-to-end sequence

```bash
make setup
make validate
make tournament
make parse
make aggregate
make ratings
make report
```

## Directory layout

- `configs/`: YAML experiment configs
- `positions/`: canonical starting FENs and opening suite
- `variants/`: variant metadata
- `scripts/`: CLI entry points for each stage
- `src/chess_variant_research/`: core package
- `tests/`: castling/parser/metrics tests
- `data/raw`: PGNs/logs
- `data/processed`: tabular outputs
- `data/reports`: generated markdown reports

## Engine stack

- Primary expected engine: Fairy-Stockfish binary in `engines/bin/fairy-stockfish`
- Optional match runner binary: `fastchess` (if available)
- Current workflow uses `python-chess` UCI orchestration for self-play and analysis.
- `fastchess` is optional and not required for the documented workflow.

### Third-party engine licenses

- Fairy-Stockfish: GPL-3.0
  - Repository: https://github.com/fairy-stockfish/Fairy-Stockfish
- fastchess: MIT
  - Repository: https://github.com/Disservin/fastchess

## Reproducibility

- All experiments are config-driven through YAML files in `configs/`.
- Raw and processed outputs are written to separate directories.
- Scripts fail loudly on invalid FENs, missing binaries, malformed PGNs, or unsupported variants.

## Notes

- This repository is intentionally local-first.
- No GUI/web application is included.
