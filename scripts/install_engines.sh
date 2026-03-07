#!/usr/bin/env bash
set -euo pipefail

mkdir -p engines/bin engines/src

echo "Place Fairy-Stockfish binary at engines/bin/fairy-stockfish (chmod +x)."
echo "Optional: place fastchess at engines/bin/fastchess."
echo "This script is intentionally minimal for fully-local/manual engine management."
