#!/bin/sh
set -eu
umask 077
unset CONFIG_PATH
stage=/state/startup-v01627-v2
database=/var/lib/stalwart/startup-v2/database
[ -f /state/native-v01618-v2/ACCEPTED ]
[ ! -e "$stage" ]
[ ! -e /var/lib/stalwart/startup-v2 ]
[ -s /baseline/database/CURRENT ]
[ -n "$(find /baseline/database -maxdepth 1 -type f -name 'MANIFEST-*' -print -quit)" ]
[ -z "$(find /baseline/database -type l -print -quit)" ]
command -v curl >/dev/null
command -v diff >/dev/null
mkdir -m 700 "$stage" /var/lib/stalwart/startup-v2
cp -a /baseline/database "$database"
diff -qr /baseline/database "$database" >/dev/null 2>&1
printf 'fresh_copy_full_comparison=pass\n'
printf '%s' '{"@type":"RocksDb","path":"/var/lib/stalwart/startup-v2/database"}' > /work/config.json
[ -s /work/config.json ]
: > /work/http-codes
/usr/local/bin/stalwart --config /work/config.json > "$stage/startup.stdout" 2> "$stage/startup.stderr" &
server_pid=$!
cleanup() {
  kill -TERM "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
observe() {
  alive=false
  if kill -0 "$server_pid" 2>/dev/null; then alive=true; fi
  printf '{"observation":"startup","processAlive":%s,"network":' "$alive"
  awk -f /scripts/network.awk /proc/net/tcp /proc/net/tcp6
  printf ',"httpStatusCounts":'
  awk -f /scripts/http.awk /work/http-codes
  printf '}\n'
}
probe() {
  code=$(curl --noproxy '*' -sSk --connect-timeout 1 --max-time 1 \
    -o /dev/null -w '%{http_code}' -H 'X-Forwarded-For: 127.0.0.1' \
    "$1" 2>/dev/null) || code=000
  case "$code" in [0-5][0-9][0-9]) ;; *) code=000 ;; esac
  printf '%s\n' "$code" >> /work/http-codes
  [ "$code" = 200 ]
}
ready=false
start=$(date +%s)
deadline=$((start + 180))
next_observation=$start
while [ "$(date +%s)" -lt "$deadline" ]; do
  kill -0 "$server_pid" 2>/dev/null || break
  if probe https://127.0.0.1:443/healthz/ready || probe http://127.0.0.1:8080/healthz/ready; then
    ready=true
    break
  fi
  now=$(date +%s)
  if [ "$now" -ge "$next_observation" ]; then
    observe
    next_observation=$((now + 30))
  fi
  sleep 1
done
observe
kill -TERM "$server_pid" 2>/dev/null || true
set +e
wait "$server_pid"
server_status=$?
set -e
trap - EXIT HUP INT TERM
if [ "$ready" != true ]; then
  printf '{"normalStartup":"failed","reason":"readiness_not_observed","nativeExit":%s}\n' "$server_status"
  exit 1
fi
if [ "$server_status" != 0 ]; then
  printf '{"normalStartup":"failed","reason":"unclean_shutdown","nativeExit":%s}\n' "$server_status"
  exit 1
fi
printf '{"normalStartup":"pass","version":"0.16.27","loopbackReady":true,"nativeExit":0}\n' > "$stage/result.json"
printf 'ready-and-cleanly-stopped\n' > "$stage/ACCEPTED"
sync
cat "$stage/result.json"
