#!/bin/sh
set -eu
umask 077
unset CONFIG_PATH
stage=/state/answered-prepare-v1
run=$stage/final-run-v1
[ "$(cat /state/startup-v01627-v2/ACCEPTED)" = ready-and-cleanly-stopped ]
[ "$(cat "$stage/native-exit")" = 0 ]
[ "$(cat "$stage/forward-run-v1/native-exit")" = 0 ]
[ "$(cat "$stage/full-verify-v2/native-exit")" = 0 ]
[ -s "$stage/native/answers.toml" ]
[ -s "$stage/native/prepare-report.txt" ]
[ ! -e "$run" ]
[ -s /var/lib/stalwart-v1/database/CURRENT ]
[ -s /var/lib/stalwart/startup-v2/database/CURRENT ]
[ -n "$(find /var/lib/stalwart/startup-v2/database -maxdepth 1 -type f -name 'MANIFEST-*' -print -quit)" ]
[ -z "$(find /var/lib/stalwart/startup-v2/database -type l -print -quit)" ]
mkdir -m 700 "$run"
set +e
stalwart-migrate run --final --yes --source /config/source.json --target /config/target.json --state "$stage/native" >"$run/stdout" 2>"$run/stderr"
status=$?
set -e
printf '%s\n' "$status" > "$run/native-exit"
if [ "$status" -ne 0 ]; then
  printf '{"finalRunComplete":false,"reason":"native_execution_failed"}\n'
  exit 1
fi
sync
