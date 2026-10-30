#!/bin/sh
set -eu
umask 077
unset CONFIG_PATH
stage=/state/answered-prepare-v1
candidate=/state/answers-candidate-v1/answers.toml
[ "$(cat /state/startup-v01627-v2/ACCEPTED)" = ready-and-cleanly-stopped ]
[ ! -e "$stage" ]
[ -f "$candidate" ] && [ ! -L "$candidate" ]
[ "$(wc -c < "$candidate")" -le 4096 ]
[ -s /var/lib/stalwart/startup-v2/database/CURRENT ]
[ -n "$(find /var/lib/stalwart/startup-v2/database -maxdepth 1 -type f -name 'MANIFEST-*' -print -quit)" ]
[ -z "$(find /var/lib/stalwart/startup-v2/database -type l -print -quit)" ]
mkdir -m 700 "$stage"
mkdir -m 700 "$stage/native"
cp "$candidate" "$stage/native/answers.toml"
chmod 600 "$stage/native/answers.toml"
set +e
stalwart-migrate prepare --source /config/source.json --state "$stage/native" --non-interactive >"$stage/stdout" 2>"$stage/stderr"
status=$?
set -e
printf '%s\n' "$status" > "$stage/native-exit"
if [ "$status" -ne 0 ]; then
  printf '{"answeredPrepare":"failed","reason":"native_execution_failed"}\n'
  exit 1
fi
[ -s "$stage/native/answers.toml" ]
[ -s "$stage/native/prepare-report.txt" ]
sync
