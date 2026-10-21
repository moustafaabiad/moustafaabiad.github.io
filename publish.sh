#!/usr/bin/env bash
# Sync the guest list from the Google Sheet export, rebuild index.html and push – only when something changed.
#
#   bash publish.sh [<export-file>] [--force]
#
# <export-file>: the Drive export of "Invitation - guest list (live)" (see src/sync_guests.py for the accepted
#                forms). Without it, the newest Drive export saved by the assistant harness is used.
# --force      : publish even if the list shrank by more than 30 %.
# Environment  : PUBLISH_NO_PUSH=1 → commit locally but do not push;  COMMIT_TRAILER="…" → appended to the message.
#
# Exit codes: 0 published, 3 nothing to publish, 1 failed / refused (nothing committed).
set -uo pipefail
cd "$(dirname "$0")"

GIT=(git -c user.name="Moustafa Abiad" -c user.email="moustafaabiad@abiadgroup.com")

if [ -n "$("${GIT[@]}" status --porcelain)" ]; then
  echo "error: the working tree has uncommitted changes – commit or discard them first"; exit 1
fi
"${GIT[@]}" pull --ff-only --quiet || { echo "error: could not fast-forward from origin"; exit 1; }

log="$(mktemp)"
python3 src/sync_guests.py "$@" | tee "$log"
rc=${PIPESTATUS[0]}
if [ "$rc" -eq 3 ]; then echo "nothing to publish"; rm -f "$log"; exit 3; fi
if [ "$rc" -ne 0 ]; then echo "not published"; rm -f "$log"; exit 1; fi

python3 src/build.py || { echo "error: build failed"; "${GIT[@]}" checkout -- src/data/guests.json; exit 1; }

summary="$(grep -E '^guest list:' "$log" | sed 's/^guest list: //; s/ (was .*//')"
changes="$(grep -E '^changes:' "$log" | sed 's/^changes: //')"
details="$(grep -E '^  [^ ]' "$log")"
msg="Guest list: ${summary} – ${changes}"$'\n\n'"${details}"
[ -n "${COMMIT_TRAILER:-}" ] && msg="${msg}"$'\n\n'"${COMMIT_TRAILER}"
rm -f "$log"

"${GIT[@]}" add index.html src/data/guests.json
"${GIT[@]}" commit --quiet -m "$msg" || { echo "error: commit failed"; exit 1; }
if [ "${PUBLISH_NO_PUSH:-0}" = "1" ]; then echo "committed locally (push skipped)"; exit 0; fi
"${GIT[@]}" push --quiet origin HEAD || { echo "error: push failed – the commit is local only"; exit 1; }
echo "published: ${summary} – ${changes}"
