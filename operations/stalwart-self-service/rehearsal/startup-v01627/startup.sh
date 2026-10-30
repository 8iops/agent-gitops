#!/bin/sh
set -eu
umask 077
unset CONFIG_PATH
stage=/state/startup-v01627
[ -f /state/native-v01618-v2/ACCEPTED ]
[ ! -e "$stage" ]
[ -s /var/lib/stalwart/database/CURRENT ]
[ -n "$(find /var/lib/stalwart/database -maxdepth 1 -type f -name 'MANIFEST-*' -print -quit)" ]
[ -z "$(find /var/lib/stalwart/database -type l -print -quit)" ]
command -v curl >/dev/null
mkdir -m 700 "$stage"
printf '%s' '{"@type":"RocksDb","path":"/var/lib/stalwart/database"}' > /work/config.json
[ -s /work/config.json ]
# Normal startup reaches main's migration/start_services path. All output may
# contain sensitive values and stays in restricted state; never return it.
/usr/local/bin/stalwart --config /work/config.json > "$stage/startup.stdout" 2> "$stage/startup.stderr" &
server_pid=$!
cleanup() {
  kill -TERM "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
ready=false
attempt=0
while [ "$attempt" -lt 60 ]; do
  kill -0 "$server_pid" 2>/dev/null || break
  # Match the official image's loopback listener fallbacks; only /ready counts.
  # TLS verification is disabled solely for loopback and no response is printed.
  if curl --noproxy '*' -fsSk --connect-timeout 1 --max-time 1 -o /dev/null \
       -H 'X-Forwarded-For: 127.0.0.1' https://127.0.0.1:443/healthz/ready 2>/dev/null || \
     curl --noproxy '*' -fsS --connect-timeout 1 --max-time 1 -o /dev/null \
       -H 'X-Forwarded-For: 127.0.0.1' http://127.0.0.1:8080/healthz/ready 2>/dev/null; then
    ready=true
    break
  fi
  attempt=$((attempt + 1))
  sleep 1
done
if [ "$ready" != true ]; then
  printf '{"normalStartup":"failed","reason":"readiness_not_observed"}\n'
  exit 1
fi
kill -TERM "$server_pid"
set +e
wait "$server_pid"
server_status=$?
set -e
trap - EXIT HUP INT TERM
if [ "$server_status" != 0 ]; then
  printf '{"normalStartup":"failed","reason":"unclean_shutdown","nativeExit":%s}\n' "$server_status"
  exit 1
fi
printf '{"normalStartup":"pass","version":"0.16.27","loopbackReady":true,"nativeExit":0}\n' > "$stage/result.json"
printf 'ready-and-cleanly-stopped\n' > "$stage/ACCEPTED"
sync
cat "$stage/result.json"
