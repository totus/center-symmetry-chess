## Task Specification for Codex Agent

### Project title

#### Local Research Pipeline for Evaluating a Chess Variant with White King/Queen Swapped

### High-level objective

Build a fully local, reproducible research project that evaluates the practical balance impact of a chess variant in which **White’s king and queen are swapped in the starting position**, while Black remains in the orthodox setup.

The project must use open source tools only and must support:
 1.	defining and validating the variant,
 2.	running engine analysis from the custom starting position,
 3.	running large batches of engine-vs-engine games,
 4.	parsing and aggregating results,
 5.	computing statistics and rating estimates,
 6.	producing a final human-readable report on whether the variant introduces a measurable advantage or disadvantage.

The end goal is **not** to build a GUI chess app.
The end goal is a **research harness** for controlled experiments.

### Variant under study

#### Baseline

Orthodox chess.

#### Variant

White starts with king and queen swapped:
 *	White back rank: R N B K Q B N R
 *	Black back rank: R N B Q K B N R

Equivalent White first-rank layout:
 *	a1 R
 *	b1 N
 *	c1 B
 *	d1 K
 *	e1 Q
 *	f1 B
 *	g1 N
 *	h1 R

### Important note on castling

The project must treat castling using a **Chess960-style destination convention**, i.e. the resulting squares after castling must be the same as in orthodox chess:
 *	White O-O → king on g1, rook on f1
 *	White O-O-O → king on c1, rook on d1
 *	Black O-O → king on g8, rook on f8
 *	Black O-O-O → king on c8, rook on d8

This must be implemented and documented carefully, because castling semantics are central to the experiment.

### Core research questions

The system should make it possible to answer the following questions with actual data:
 1.	Does swapping White’s king and queen in the initial position measurably affect game balance?
 2.	If yes, in whose favor, and by how much?
 3.	Is the effect visible only in static engine evaluations, or also in large self-play samples?
 4.	Does the variant bias White toward queenside castling and away from kingside castling?
 5.	How much of the impact is mediated through castling patterns, opening choice, and early king safety?
 6.	Is the effect robust across:
       * time controls,
       * search depths,
       * match configurations,
       * and control variants such as “Black swapped instead of White”?

### Required deliverables

The agent must implement the following deliverables.

#### 1. Repository structure
Create a clean repository with a structure close to this:

```terminaloutput
center-symmetry-chess/
  README.md
  LICENSE
  .gitignore
  pyproject.toml
  requirements.txt
  Makefile
  docker-compose.yml
  /engines
    /bin
    /src
  /variants
    orthodox/
    swapped_white/
    swapped_black/
    swapped_both/
  /positions
    orthodox_start.fen
    swapped_white_start.fen
    swapped_black_start.fen
    swapped_both_start.fen
    opening_suite.epd
  /scripts
    install_engines.sh
    validate_variant.py
    depth_probe.py
    run_matches.py
    run_tournament.py
    parse_pgn.py
    aggregate_results.py
    compute_ratings.py
    generate_report.py
  /src
    /chess_variant_research
      __init__.py
      config.py
      fen.py
      engines.py
      matches.py
      parsing.py
      metrics.py
      ratings.py
      reporting.py
      schemas.py
      utils.py
  /tests
    test_fen.py
    test_castling_rules.py
    test_parser.py
    test_metrics.py
  /data
    /raw
    /processed
    /reports
  /notebooks
    01_root_analysis.ipynb
    02_match_analysis.ipynb
    03_opening_analysis.ipynb
```
This exact structure is not mandatory, but the final layout must be similarly clear and maintainable.

#### 2. Variant definition and validation

Implement the variant definitions in a way that is usable by the selected engine stack.

The project should support at least these four modes:
 1.	orthodox
 2.	swapped_white
 3.	swapped_black
 4.	swapped_both

The code must include:
 *	explicit FENs for each start position,
 *	explicit rules/configuration files for the variant engine,
 *	a validation script proving that the engine accepts the custom starting position and castling logic.

The validation script must check at least:
 *	legal move generation from the starting position,
 *	legal castling when conditions are satisfied,
 *	correct king/rook landing squares after castling,
 *	no silent fallback to orthodox castling assumptions.

#### 3. Engine integration

Use open source chess engines and match tools.

Preferred stack:
 *	**Fairy-Stockfish** for variant support,
 *	**fastchess** or **cutechess-cli** for engine-vs-engine match execution,
 *	**python-chess** for PGN/FEN handling and orchestration,
 *	**Ordo** and/or **BayesElo** for rating estimation.

The implementation should aim for this architecture:
 *	Python orchestrates experiments.
 *	Engines are installed or built locally.
 *	External binaries are invoked through robust Python wrappers.
 *	All runs are reproducible from config files and CLI commands.

The code must not assume a GUI.

#### 4. Root/depth analysis pipeline

Implement a pipeline that evaluates the starting position and selected early positions using the engine.

Required features:
 *	analyze the root position for each variant,
 *	configurable depth and/or movetime,
 *	MultiPV support,
 *	save results to structured data files,
 *	include principal variations,
 *	include score in centipawns or mate notation,
 *	include WDL if available,
 *	include depth, seldepth, nodes, nps, time, hashfull if available.

The pipeline must support probing:
 *	the initial position,
 *	and optionally positions after common opening moves such as:
 *	1.e4
 *	1.d4
 *	1.Nf3
 *	1.c4
 *	1.g3

for both orthodox and variant setups.

Outputs should be stored in CSV and/or Parquet.

#### 5. Match execution pipeline

Implement a batch match runner for engine-vs-engine experiments.

Required capabilities:
 *	run self-play matches from a chosen variant,
 *	configurable number of games,
 *	configurable time control,
 *	configurable engine parameters,
 *	color balancing,
 *	PGN output,
 *	raw logs,
 *	resumable execution if possible,
 *	deterministic experiment configs.

At minimum, the project must support these experiment families:

##### A. Baseline
Orthodox chess self-play.

##### B. Variant under study
Swapped White only.

##### C. Side-control
Swapped Black only.

##### D. Optional symmetry-control
Swapped both.

##### E. No-book experiments
Start directly from the custom initial position.

##### F. Opening-suite experiments
Start from a set of predefined opening positions in EPD/FEN form.

The runner must expose experiments from config files or CLI flags rather than hard-coded editing.

#### 6. PGN parsing and feature extraction

Implement a robust PGN parser that extracts structured metrics from completed games.

Required extracted fields per game:
 *	game id / filename / source batch,
 *	variant name,
 *	white engine / black engine,
 *	result,
 *	termination type if available,
 *	ply count / move count,
 *	ECO if present,
 *	initial FEN,
 *	castling side for White,
 *	castling side for Black,
 *	move number when White castled,
 *	move number when Black castled,
 *	whether castling rights were lost before castling,
 *	opening move family:
      *	e4
      *	d4
      *	Nf3
      *	c4
      *	g3
      *	other
 *	whether central files opened early,
 *	optionally: engine eval snapshots if available in comments.

The parser should store extracted rows in machine-readable tabular output.

#### 7. Statistical analysis and rating estimation

Implement post-processing scripts that compute aggregate results.

Required metrics:
 *	White win rate,
 *	Black win rate,
 *	draw rate,
 *	score percentage,
 *	performance by variant,
 *	performance by opening family,
 *	castling frequency by side,
 *	kingside vs queenside castling rates,
 *	average castling move number,
 *	no-castling rates,
 *	average game length.

Also compute or support:
 *	Elo difference estimates,
 *	confidence intervals,
 *	likelihood of superiority / significance proxy,
 *	comparison between swapped_white and swapped_black.

If possible, integrate either:
 *	Ordo,
 *	BayesElo,
 *	or both.

The project must produce a summary table that directly addresses whether the side with swapped king/queen appears penalized.

#### 8. Report generation

Implement a script that generates a final Markdown report summarizing the experiment.

The report should include:
 *	experiment metadata,
 *	engine versions,
 *	variant definitions,
 *	sample sizes,
 *	time controls,
 *	root analysis summary,
 *	match results summary,
 *	castling behavior summary,
 *	opening behavior summary,
 *	rating estimates,
 *	key findings,
 *	known limitations.

The report should be suitable for a human researcher to read without digging through raw files.

### Functional requirements

#### Environment

The project must run locally on macOS and Linux.
Avoid OS-specific assumptions where possible.

#### Languages and tools

Preferred implementation language: Python 3.11+

Use Python for orchestration, parsing, and reporting.

Shell scripts are acceptable for engine install/build steps.

#### Data formats

Use human- and machine-friendly formats:
 *	YAML or TOML for experiment configs,
 *	CSV and/or Parquet for processed data,
 *	PGN for games,
 *	Markdown for reports.

#### Reproducibility

Every experiment must be reproducible from:
 *	explicit config files,
 *	deterministic command lines,
 *	persisted output artifacts.

#### Robustness

The system must fail loudly on:
 *	invalid FEN,
 *	invalid castling configuration,
 *	missing engine binaries,
 *	malformed PGN,
 *	unsupported variant settings.

Do not silently continue with incorrect assumptions.

### Non-goals

The agent **must not** spend time on the following unless needed for the research harness:
 *	web frontend,
 *	desktop GUI,
 *	online multiplayer,
 *	browser-based board rendering,
 *	user account system,
 *	deployment to cloud,
 *	engine training,
 *	custom neural network work.

This is a **local research and experimentation toolkit**, not a consumer chess product.

### Implementation guidance

#### 1. Prefer configuration over code edits

Experiment definitions should be stored in config files, not hard-coded in Python.

For example, define:
 *	engine binary path,
 *	time control,
 *	number of games,
 *	variant name,
 *	opening suite path,
 *	thread count,
 *	hash size,
 *	output directory

in config files or CLI arguments.

#### 2. Provide a thin but reliable CLI

The repository should expose commands such as:
```bash
make install-engines
make validate
make probe
make match
make parse
make aggregate
make report
```
or equivalent Python entry points.

#### 3. Separate raw from processed data

Keep:
 *	raw PGNs and logs untouched,
 *	processed tables generated separately.

#### 4. Make castling test coverage explicit

Because this project depends critically on non-orthodox king placement, add tests specifically around:
 *	White kingside castling path requirements,
 *	White queenside castling path requirements,
 *	final squares after castling,
 *	disallowing illegal castling through check,
 *	compatibility with the chosen engine configuration.

#### 5. Keep the codebase inspectable

The repository should be understandable by a technical user without reading large notebooks first.

### Suggested milestone plan

#### Milestone 1 — Project bootstrap

Deliver:
 *	repository skeleton,
 *	Python project setup,
 *	README,
 *	install/build scripts for engines,
 *	sample config files.

#### Milestone 2 — Variant definition

Deliver:
 *	start-position FENs,
 *	variant config files,
 *	validation script,
 *	tests for castling semantics.

#### Milestone 3 — Root analysis

Deliver:
 *	engine probe script,
 *	saved outputs for at least one depth sweep,
 *	basic tabular summary.

#### Milestone 4 — Match runner

Deliver:
 *	batch match execution script,
 *	config-driven experiments,
 *	PGN generation,
 *	logging.

#### Milestone 5 — Parser and metrics

Deliver:
 *	PGN parser,
 *	extracted game-level table,
 *	aggregate metrics.

#### Milestone 6 — Ratings and report

Deliver:
 *	Elo/rating estimation integration,
 *	final Markdown report generator,
 *	end-to-end runnable workflow.