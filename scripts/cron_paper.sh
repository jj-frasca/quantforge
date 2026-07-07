#!/usr/bin/env bash
# Daily paper-trading forward accrual (ADR-019). TOKEN-FREE: pure Python + git, no `claude -p`,
# so it runs regardless of Claude usage. Installed as a launchd agent (com.jjfrasca.quantforge-paper).
# Advances every frozen paper position on fresh daily bars, commits the updated portfolio, and
# Slacks the scoreboard.
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO="$HOME/claude-work/quantforge"
SLACK_WEBHOOK_FILE="$HOME/.claude/.slack_webhook"

echo "=== quantforge-paper $(date '+%Y-%m-%dT%H:%M:%S%z') ==="

cd "$REPO/backend" || { echo "no backend dir"; exit 1; }
OUTPUT=$(PYTHONPATH=. uv run python scripts/paper.py 2>&1)
echo "$OUTPUT"

# Persist the accrued portfolio in git (scoped to the one file; token-free).
cd "$REPO" || exit 1
if ! git diff --quiet -- data/paper_portfolio.json 2>/dev/null; then
  git add data/paper_portfolio.json
  if git commit -q -m "chore(paper): daily forward accrual $(date +%F)"; then
    git push -q origin master || echo "push failed (network?)"
  fi
else
  echo "no portfolio change"
fi

# Slack the scoreboard (best-effort).
if [[ -f "$SLACK_WEBHOOK_FILE" ]] && command -v jq >/dev/null 2>&1; then
  WEBHOOK=$(cat "$SLACK_WEBHOOK_FILE")
  printf '%s' "$OUTPUT" \
    | jq -Rs '{text: ("*QuantForge paper forward-test*\n```" + . + "```")}' \
    | curl -s -X POST "$WEBHOOK" -H 'Content-type: application/json' -d @- >/dev/null 2>&1 || true
fi
