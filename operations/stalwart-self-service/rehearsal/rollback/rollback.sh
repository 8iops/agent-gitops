#!/bin/sh
set -eu
umask 077
unset CONFIG_PATH
forward=/state/answered-prepare-v1
stage=/state/rollback-v1
[ "$(cat "$forward/final-run-v1/native-exit")" = 0 ]
[ "$(cat "$forward/post-final-full-verify-v1/native-exit")" = 0 ]
[ "$(cat /state/startup-v1-rehearsal-v1/ACCEPTED)" = ready-and-cleanly-stopped ]
[ -s "$forward/native/final-report.txt" ]
[ ! -e "$stage" ]
[ ! -e /var/lib/stalwart-rollback/database ]
[ -s /var/lib/stalwart-v1/database/CURRENT ]
[ -n "$(find /var/lib/stalwart-v1/database -maxdepth 1 -type f -name 'MANIFEST-*' -print -quit)" ]
[ -z "$(find /var/lib/stalwart-v1/database -type l -print -quit)" ]
mkdir -m 700 "$stage" "$stage/native"
set +e
stalwart-migrate rollback --verify-full --yes \
  --source /config/target.json --target /config/rollback.json \
  --state "$stage/native" --forward-state "$forward/native" \
  >"$stage/stdout" 2>"$stage/stderr"
status=$?
set -e
printf '%s\n' "$status" > "$stage/native-exit"
if [ "$status" -ne 0 ]; then
  printf '{"rollbackComplete":false,"reason":"native_rollback_failed"}\n'
  exit 1
fi
sync
