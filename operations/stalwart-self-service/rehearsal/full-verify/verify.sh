#!/bin/sh
set -eu
umask 077
unset CONFIG_PATH
stage=/state/answered-prepare-v1
run=$stage/forward-run-v1
verify=$stage/full-verify-v2
[ "$(cat "$stage/native-exit")" = 0 ]
[ "$(cat "$run/native-exit")" = 0 ]
[ ! -e "$verify" ]
[ -s /var/lib/stalwart/startup-v2/database/CURRENT ]
[ -s /var/lib/stalwart-v1/database/CURRENT ]
mkdir -m 700 "$verify"
set +e
stalwart-migrate verify --full --source /config/source.json --target /config/target.json --state "$stage/native" >"$verify/stdout" 2>"$verify/stderr"
status=$?
set -e
printf '%s\n' "$status" > "$verify/native-exit"
if [ "$status" -ne 0 ]; then
  printf '{"fullVerificationComplete":false,"reason":"native_verification_failed"}\n'
  exit 1
fi
sync
printf '{"fullVerificationComplete":true,"rehearsalOnly":true,"rollbackVerified":false}\n'
