#!/bin/sh
set -eu
failed() {
  status=$?
  if [ "$status" -ne 0 ]; then
    printf '{"diagnostic":"failed","reason":"log_read_failed"}\n'
  fi
}
trap failed EXIT
stage=/state/startup-v01627
[ ! -e "$stage/ACCEPTED" ]
[ -r "$stage/startup.stdout" ] && [ -f "$stage/startup.stdout" ] && [ ! -L "$stage/startup.stdout" ]
[ -r "$stage/startup.stderr" ] && [ -f "$stage/startup.stderr" ] && [ ! -L "$stage/startup.stderr" ]
[ ! -L "$stage" ]
# Counts are candidates, not root-cause proof. Only grep exit 0/1 is valid;
# read errors must not become zero matches. No native line or error is printed.
classify() {
  out=$(grep -Eic "$2" "$stage/startup.stdout" 2>/dev/null) || {
    status=$?
    [ "$status" = 1 ] || exit 1
  }
  err=$(grep -Eic "$2" "$stage/startup.stderr" 2>/dev/null) || {
    status=$?
    [ "$status" = 1 ] || exit 1
  }
  count=$((out + err))
  matches="$matches$separator\"$1\":$count"
  separator=,
}
stdout_bytes=$(wc -c < "$stage/startup.stdout")
stderr_bytes=$(wc -c < "$stage/startup.stderr")
matches=
separator=
classify missingFile 'No such file|not found|does not exist'
classify certificate 'certificate|private key|TLS error'
classify readonlyFilesystem 'Read-only file system'
classify permission 'Permission denied|Operation not permitted'
classify bind 'Failed to bind|Address already in use|Cannot assign requested address'
classify nodeLease 'node.?id|node lease|lease.*expired|lease.*acquir'
classify store 'Failed to open|RocksDB|database.*error|store.*error'
classify configuration 'configuration error|config.*invalid|unknown.*config|Failed to.*config'
classify migration 'Failed to migrate database'
classify network 'Connection refused|Network is unreachable|Connection timed out'
classify startup 'server.startup|server-startup|Starting Stalwart'
printf '{"diagnostic":"startup_log_classification","stdoutBytes":%s,"stderrBytes":%s,"matches":{%s}}\n' "$stdout_bytes" "$stderr_bytes" "$matches"
