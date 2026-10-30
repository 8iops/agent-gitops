#!/bin/sh
set -eu
stage=/state/startup-v01627
[ ! -e "$stage/ACCEPTED" ]
[ -f "$stage/startup.stdout" ] && [ ! -L "$stage/startup.stdout" ]
[ -f "$stage/startup.stderr" ] && [ ! -L "$stage/startup.stderr" ]
[ ! -L "$stage" ]
# Match fixed diagnostic vocabulary only. Counts are candidate evidence, not
# proof of root cause. Never print a matching line or interpolate native text.
classify() {
  count=$(grep -Eic "$2" "$stage/startup.stdout" "$stage/startup.stderr" | awk -F: '{n += $NF} END {print n+0}')
  printf '"%s":%s' "$1" "$count"
}
printf '{"diagnostic":"startup_log_classification","stdoutBytes":'
wc -c < "$stage/startup.stdout" | tr -d ' \n'
printf ',"stderrBytes":'
wc -c < "$stage/startup.stderr" | tr -d ' \n'
printf ',"matches":{'
classify missingFile 'No such file|not found|does not exist'
printf ','; classify certificate 'certificate|private key|TLS error'
printf ','; classify readonlyFilesystem 'Read-only file system'
printf ','; classify permission 'Permission denied|Operation not permitted'
printf ','; classify bind 'Failed to bind|Address already in use|Cannot assign requested address'
printf ','; classify nodeLease 'node.?id|node lease|lease.*expired|lease.*acquir'
printf ','; classify store 'Failed to open|RocksDB|database.*error|store.*error'
printf ','; classify configuration 'configuration error|config.*invalid|unknown.*config|Failed to.*config'
printf ','; classify migration 'Failed to migrate database'
printf ','; classify network 'Connection refused|Network is unreachable|Connection timed out'
printf ','; classify startup 'server.startup|server-startup|Starting Stalwart'
printf '}}\n'
