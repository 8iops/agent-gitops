#!/bin/sh
set -eu
umask 077
unset CONFIG_PATH
# Fail before invoking Stalwart if this is not the accepted restored RocksDB.
[ -s /baseline/database/CURRENT ]
[ -n "$(find /baseline/database -maxdepth 1 -type f -name 'MANIFEST-*' -print -quit)" ]
# Prior failure happened at exec, before native startup. Classify only the
# known OS error and prove the existing working copy still equals the baseline.
[ ! -e /state/native-v01618/ACCEPTED ]
[ -r /state/native-v01618/startup.stderr ]
grep -Fq 'Operation not permitted' /state/native-v01618/startup.stderr
[ -d /var/lib/stalwart/database ]
[ -z "$(find /baseline/database /var/lib/stalwart/database -type l -print -quit)" ]
command -v diff >/dev/null
diff -qr /baseline/database /var/lib/stalwart/database >/dev/null 2>&1
printf 'previous_exec_permission_error=confirmed full_copy_comparison=pass\n'
[ ! -e /state/native-v01618-v2 ]
mkdir -m 700 /state/native-v01618-v2
[ -s /var/lib/stalwart/database/CURRENT ]
[ -n "$(find /var/lib/stalwart/database -maxdepth 1 -type f -name 'MANIFEST-*' -print -quit)" ]
printf '%s' '{"@type":"RocksDb","path":"/var/lib/stalwart/database"}' > /work/config.json
[ -s /work/config.json ]
printf '%s\n' 'get p\x00' 'scan p\x00 p\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff' quit > /work/commands
# Native console can print full values. A FIFO ensures raw stdout is never
# persisted or returned; the filter emits only known scalar aggregate fields.
mkfifo /work/native-output
awk -f /scripts/readability.awk < /work/native-output > /state/native-v01618-v2/result.json &
filter_pid=$!
set +e
timeout 180 /usr/local/bin/stalwart --config /work/config.json --console \
  < /work/commands > /work/native-output 2>/state/native-v01618-v2/startup.stderr
native_status=$?
wait "$filter_pid"
filter_status=$?
set -e
if [ "$native_status" != 0 ] || [ "$filter_status" != 0 ]; then
  printf '{"nativeReadability":"failed","nativeExit":%s,"filterExit":%s}\n' "$native_status" "$filter_status"
  exit 1
fi
printf 'readable\n' > /state/native-v01618-v2/ACCEPTED
sync
cat /state/native-v01618-v2/result.json
