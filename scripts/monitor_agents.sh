#!/usr/bin/env bash
# Watch the parallel WP agents (token-free: pure git + gh, no claude). Fetches all branches and, for
# each non-master branch, reports commits-ahead, last-activity, open PR, and CI conclusion. Slacks a
# digest ONLY when the state changes since last run (or CI is red), so it's quiet until there's news.
# Installed as a launchd agent (com.jjfrasca.quantforge-monitor), every 30 min.
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO="$HOME/claude-work/quantforge"
STATE="$HOME/.claude/_reports/quantforge-agents-monitor.state"
SLACK_WEBHOOK_FILE="$HOME/.claude/.slack_webhook"

cd "$REPO" || exit 1
git fetch --all --prune -q 2>/dev/null

summary=""
alert=0
while read -r branch; do
  [ -z "$branch" ] && continue
  [ "$branch" = "origin/master" ] && continue
  [ "$branch" = "origin/HEAD" ] && continue
  name="${branch#origin/}"
  ahead=$(git rev-list --count "master..$branch" 2>/dev/null || echo "?")
  last=$(git log -1 --format='%cr' "$branch" 2>/dev/null || echo "?")
  pr=$(gh pr list --head "$name" --state open --json number --jq '.[0].number // empty' 2>/dev/null)
  ci=$(gh run list --branch "$name" --limit 1 --json conclusion --jq '.[0].conclusion // "pending"' 2>/dev/null)

  flag=""
  [ "$ci" = "failure" ] && { flag="🔴 CI-RED"; alert=1; }
  [ -n "$pr" ] && flag="$flag ✅ PR#$pr ready"
  summary+="• ${name}: ${ahead} commits, last ${last}, CI=${ci}${flag:+  →${flag}}"$'\n'
done < <(git branch -r | sed 's/^[* ]*//')

[ -z "$summary" ] && summary="(no agent branches yet)"

# Change-gated: only notify when the digest changed or CI is red.
hash=$(printf '%s' "$summary" | shasum | awk '{print $1}')
prev=$(cat "$STATE" 2>/dev/null || echo "")
mkdir -p "$(dirname "$STATE")"
printf '%s' "$hash" > "$STATE"

echo "=== quantforge-monitor $(date '+%F %T') ==="
echo "$summary"

if { [ "$hash" != "$prev" ] || [ "$alert" = "1" ]; } && [ -f "$SLACK_WEBHOOK_FILE" ] \
    && command -v jq >/dev/null 2>&1; then
  webhook=$(cat "$SLACK_WEBHOOK_FILE")
  printf '%s' "$summary" \
    | jq -Rs '{text: ("*QuantForge WP agents*\n" + .)}' \
    | curl -s -X POST "$webhook" -H 'Content-type: application/json' -d @- >/dev/null 2>&1 || true
fi
