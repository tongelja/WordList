#!/bin/bash
# Copy WordList to the Pi and (re)start it.  Usage: deploy/deploy.sh [user@host]
set -euo pipefail

HOST="${1:-pi@pi-hole}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"

rsync -az --delete \
    --exclude .git --exclude .venv --exclude __pycache__ \
    --exclude 'wordlist/.cache' --exclude 'wordlist/myWords.*.doc' \
    "$REPO/" "$HOST:WordList/"

ssh "$HOST" bash -s <<'EOF'
set -euo pipefail
if [ ! -x ~/.local/bin/uv ]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
cd ~/WordList
~/.local/bin/uv sync --frozen --no-dev
sudo cp deploy/wordlist.service deploy/wordlist-prefetch.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wordlist wordlist-prefetch
sudo systemctl restart wordlist
# Fetches any words not cached yet; does nothing if it is already running.
sudo systemctl start wordlist-prefetch
sleep 3
systemctl is-active wordlist
EOF
