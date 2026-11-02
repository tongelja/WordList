#!/bin/bash
# Copy the Pi's downloaded words to this Mac and save them to wordlist/data/words.json,
# ready to commit and push (which rebuilds the Azure site).  Usage: deploy/pull_data.sh [user@host]
set -euo pipefail

HOST="${1:-pi@pi-hole}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"

rsync -az "$HOST:WordList/wordlist/.cache/" "$REPO/wordlist/.cache/"
cd "$REPO/wordlist"
uv run python export_data.py
