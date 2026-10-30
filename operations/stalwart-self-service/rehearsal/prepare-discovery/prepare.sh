#!/bin/sh
set -eu
umask 077
unset CONFIG_PATH
stage=/state/prepare-discovery-v1
[ "$(cat /state/startup-v01627-v2/ACCEPTED)" = ready-and-cleanly-stopped ]
[ ! -e "$stage" ]
[ -s /var/lib/stalwart/startup-v2/database/CURRENT ]
[ -n "$(find /var/lib/stalwart/startup-v2/database -maxdepth 1 -type f -name 'MANIFEST-*' -print -quit)" ]
[ -z "$(find /var/lib/stalwart/startup-v2/database -type l -print -quit)" ]
mkdir -m 700 "$stage"
# Source is a read-only PVC and native adapter opens RocksDB ReadOnly.
# A new state directory ensures no supplied answers can approve policies.
set +e
stalwart-migrate prepare --source /config/source.json --state "$stage/native" --non-interactive >"$stage/stdout" 2>"$stage/stderr"
status=$?
set -e
printf '%s\n' "$status" > "$stage/native-exit"
# Neither 0 nor 1 means migration success. The separate projector classifies
# complete evidence; all other codes fail without returning native logs.
case "$status" in
  0|1) ;;
  *) printf '{"discovery":"failed","reason":"native_execution_failed"}\n'; exit 1 ;;
esac
[ -s "$stage/native/answers.toml" ]
[ -s "$stage/native/prepare-report.txt" ]
sync
