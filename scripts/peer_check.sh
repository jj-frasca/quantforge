#!/usr/bin/env bash
# Peer-collision check for an autonomous session sharing this working tree with another live
# Claude session (AUTONOMY_CHARTER.md's standing warning). Answers, in one cheap call, the three
# questions sessions #95-98 kept re-deriving by hand before touching any file:
#   1. Is another `claude` process actually running right now, and since when?
#   2. Which "hot" files (the areas peers have repeatedly iterated on) has it touched recently?
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
echo "-- recent activity on peer-hot files (last commit each) --"
for f in \
  backend/app/research/lab/panel_null.py \
  backend/app/research/lab/calibration.py \
  backend/app/research/lab/probability_dsr.py \
  backend/app/research/lab/gate.py \
  backend/app/research/lab/pool_report.py \
  .claude/context/validation-methodology.md \
  .claude/context/data-contracts.md \
  .claude/context/backtesting-spec.md \
  .claude/context/api-contracts.md \
; do
  [ -f "$f" ] || continue
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
