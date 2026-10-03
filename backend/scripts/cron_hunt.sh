#!/usr/bin/env bash
# Scheduled mass-test (WP-F). TOKEN-FREE: pure Python + git, no `claude -p`, so it
# runs regardless of Claude usage. Runs the universe hunt on max-history yfinance data, commits the
# updated pool, and Slacks a summary. Paper-forward alone reconciles promotions (ADR-152).
# Local/launchd fallback for .github/workflows/hunt.yml (the primary, always-on cloud runner).
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO="${QUANTFORGE_REPO:-$HOME/claude-work/quantforge}"
UNIVERSE="${1:-data/universes/sp500.txt}"
SLACK_WEBHOOK_FILE="$HOME/.claude/.slack_webhook"

echo "=== quantforge-hunt $(date '+%Y-%m-%dT%H:%M:%S%z') (universe: $UNIVERSE) ==="

cd "$REPO/backend" || { echo "no backend dir"; exit 1; }
# The hunt forces yfinance internally (scripts/hunt.py) — do NOT pass Alpaca keys here.
OUTPUT=$(PYTHONPATH=. uv run python scripts/hunt.py "$REPO/$UNIVERSE" 2>&1)
echo "$OUTPUT"

# Persist the pool in git. The managed paper book has one workflow writer (ADR-152).
cd "$REPO" || exit 1
if ! git diff --quiet -- data/research_pool 2>/dev/null; then
  git add data/research_pool
  if git commit -q -m "chore(hunt): scheduled mass-test $(date +%F)"; then
    git push -q origin master || echo "push failed (network?)"
  fi
else
  echo "no pool change"
fi

# Slack the summary (best-effort).
if [[ -f "$SLACK_WEBHOOK_FILE" ]] && command -v jq >/dev/null 2>&1; then
  WEBHOOK=$(cat "$SLACK_WEBHOOK_FILE")
  printf '%s' "$OUTPUT" \
    | jq -Rs '{text: ("*QuantForge scheduled hunt*\n```" + . + "```")}' \
    | curl -s -X POST "$WEBHOOK" -H 'Content-type: application/json' -d @- >/dev/null 2>&1 || true
fi
