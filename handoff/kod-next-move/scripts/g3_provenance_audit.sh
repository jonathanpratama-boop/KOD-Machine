#!/bin/bash
# G3 provenance audit: READ-ONLY. Run on the Mac:  bash g3_provenance_audit.sh
# Changes nothing in KOD-Machine-G3, launchd, cron or the clock. Writes one report to ~/.
# Does not print plist EnvironmentVariables, .env files or shell history.
G3="${G3:-$HOME/Projects/KOD-Machine-G3}"
OUT="$HOME/g3_provenance_$(date -u +%Y%m%dT%H%M%SZ).txt"
W1S="2026-10-12 22:00:00"; W1E="2026-10-13 00:00:00"   # early invocation, 23:04 WIB
W2S="2026-10-13 02:50:00"; W2E="2026-10-13 03:45:00"   # AAPL/MSFT collection, ~03:16 WIB
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "0. Clock and zone now"
date; date -u; readlink /etc/localtime; uptime
sntp -t 2 time.apple.com 2>&1 | tail -2          # query only; no -S, so the clock is not set

sec "1. G3 repo state"
cd "$G3" || exit 1; pwd
git log --all --format='%h %ci %an %s' --since='2026-10-11' 2>&1 | head -40
git status --porcelain 2>&1 | head -40
git stash list 2>&1 | head

sec "2. Files created/modified in the two windows (birth | modified | path)"
for w in "$W1S|$W1E" "$W2S|$W2E"; do
  s=${w%|*}; e=${w#*|}; echo "-- $s .. $e"
  find . -path ./.git -prune -o -type f -newermt "$s" ! -newermt "$e" -print 2>/dev/null |
    while read -r f; do stat -f '%SB | %Sm | %N' -t '%Y-%m-%dT%H:%M:%S%z' "$f"; done
done

sec "3. Attempt log (verbatim)"
cat automation_logs/*.jsonl 2>&1

sec "4. Collector/wrapper hashes and timestamps"
find . -path ./.git -prune -o -type f \( -name '*.py' -o -name '*.sh' -o -name '*.plist' \) -print 2>/dev/null |
  grep -iE 'collect|wrap|sched|once|launch|g3' | while read -r f; do
    stat -f '%SB | %Sm | %N' -t '%Y-%m-%dT%H:%M:%S%z' "$f"; shasum -a 256 "$f"
    git log -1 --format='   last commit %h %ci' -- "$f" 2>/dev/null
  done

sec "5. launchd jobs mentioning G3/KOD (no EnvironmentVariables)"
launchctl list 2>/dev/null | grep -iE 'g3|kod|collect' || echo "(none loaded)"
for d in "$HOME/Library/LaunchAgents" /Library/LaunchAgents /Library/LaunchDaemons; do
  grep -liE 'g3|kod-machine|collect' "$d"/*.plist 2>/dev/null | while read -r p; do
    echo "-- $p"; stat -f '   birth %SB  modified %Sm' -t '%Y-%m-%dT%H:%M:%S%z' "$p"
    for k in Label ProgramArguments Program StartCalendarInterval StartInterval RunAtLoad KeepAlive LaunchOnlyOnce StandardOutPath StandardErrorPath; do
      v=$(plutil -extract "$k" json -o - "$p" 2>/dev/null) && echo "   $k: $v"
    done
    l=$(plutil -extract Label raw -o - "$p" 2>/dev/null)
    launchctl print "gui/$(id -u)/$l" 2>/dev/null | grep -E 'state|runs|last exit|path|program' | sed 's/^/   /'
  done
done
launchctl print-disabled "gui/$(id -u)" 2>/dev/null | grep -iE 'g3|kod'

sec "6. cron and at"
crontab -l 2>&1; atq 2>&1

sec "7. launchd / clock events in the windows (unified log; may have aged out)"
for w in "$W1S|$W1E" "$W2S|$W2E"; do
  s=${w%|*}; e=${w#*|}; echo "-- $s .. $e"
  log show --style compact --start "$s" --end "$e" \
    --predicate '(process == "launchd" AND (eventMessage CONTAINS[c] "g3" OR eventMessage CONTAINS[c] "kod")) OR process == "timed" OR eventMessage CONTAINS[c] "settimeofday"' 2>&1 | tail -60
done

sec "8. Sleep/wake around the windows"
pmset -g log 2>/dev/null | grep -E '^2026-10-1[23] ' | grep -E 'Sleep|Wake|DarkWake|Clock' |
  awk '$1" "$2 >= "2026-10-12 21:30" && $1" "$2 <= "2026-10-13 04:00"' | head -60

sec "9. Agent sessions active in the windows (file names only)"
for d in "$HOME/.claude/projects" "$HOME/.hermes" "$HOME/.codex"; do
  [ -d "$d" ] || continue
  for w in "$W1S|$W1E" "$W2S|$W2E"; do
    s=${w%|*}; e=${w#*|}; echo "-- $d  $s .. $e"
    find "$d" -type f -newermt "$s" ! -newermt "$e" 2>/dev/null | head -20
  done
done
} > "$OUT" 2>&1
echo "Report: $OUT"
