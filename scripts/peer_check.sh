#!/usr/bin/env bash
# Peer-collision check for an autonomous session sharing this working tree with another live
# Claude session (AUTONOMY_CHARTER.md's standing warning). Answers, in one cheap call, the three
# questions sessions #95-98 kept re-deriving by hand before touching any file:
#   1. Is another `claude` process actually running right now, and since when?
#   2. Which files (backend/app/research, backend/app/validation, backend/app/data,
#      backend/app/api, .claude/context) has recent history touched — discovered from the last
#      20 commits, not a hardcoded list, so it tracks a peer's scope automatically as it grows
#      instead of going stale (see session #99's retro). Session #107 widened this list a second
#      time after finding the peer had been touching backend/app/data/quality,
#      backend/app/data/storage, and backend/app/api for at least a day with zero visibility in
#      this report — git log's `-- <pathspec>` restricts BOTH which commits are shown AND which
#      files --name-only lists, so a peer commit mixing a scanned file with an unscanned one only
#      ever shows the scanned half. There is no fully future-proof version of this list short of
#      scanning all of backend/app — re-widen again if a future session finds another blind spot.
#   3. Has the single highest-stakes gated workflow (panel-null calibration) been dispatched yet?
# Read-only: no git state is modified. Safe to run from anywhere inside the repo.
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO="$HOME/claude-work/quantforge"
cd "$REPO" || exit 1

echo "=== quantforge peer-check $(date '+%F %T') ==="

echo
echo "-- claude processes --"
ps -axo pid,ppid,etime,lstart,command 2>/dev/null | awk 'NR==1 || /[c]laude/'

echo
echo "-- files touched in the last 20 commits (peer-hot territory, discovered not hardcoded) --"
# A fixed file list goes stale the moment a peer's scope grows (this happened between
# session #98 and #99 — the peer expanded from panel_null.py into pbo.py, search.py,
# experiment.py, none of which were on the old hardcoded list; session #107 found it had grown
# again into backend/app/data/{quality,storage} and backend/app/api with zero visibility here).
# Deriving the list from recent history instead means it tracks the peer automatically WITHIN
# these directories — it is still not a full-repo scan, so a git log -3 on the specific file
# you're about to edit remains the real safety check, not just a clean report from this script.
git log --oneline -20 --name-only --pretty=format: -- \
    backend/app/research backend/app/validation backend/app/data backend/app/api \
    .claude/context \
  2>/dev/null | sort -u | while read -r f; do
  [ -n "$f" ] && [ -f "$f" ] || continue
  line=$(git log -1 --format='%h %ad %s' --date=short -- "$f" 2>/dev/null)
  printf '  %-55s %s\n' "$f" "${line:-(no history)}"
done

echo
echo "-- panel-null-calibration.yml dispatch status --"
if command -v gh >/dev/null 2>&1; then
  runs=$(gh run list --workflow="panel-null-calibration.yml" --limit 5 2>/dev/null)
  if [ -z "$runs" ]; then
    echo "  zero runs (still undispatched)"
  else
    echo "$runs" | sed 's/^/  /'
  fi
else
  echo "  gh not available"
fi

echo
echo "-- local vs origin/master --"
git fetch origin master -q 2>/dev/null
git status --porcelain=v2 --branch 2>/dev/null | awk '/^# branch.ab/ {print "  " $0}'
git log --oneline -3 2>/dev/null | sed 's/^/  /'
