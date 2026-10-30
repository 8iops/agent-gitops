#!/bin/sh
set -eu
umask 077
unset CONFIG_PATH
stage=/state/startup-v1-rehearsal-v1
forward=/state/answered-prepare-v1
[ "$(cat "$forward/final-run-v1/native-exit")" = 0 ]
[ "$(cat "$forward/post-final-full-verify-v1/native-exit")" = 0 ]
[ -s "$forward/native/final-report.txt" ]
[ ! -e "$stage" ]
[ -s /var/lib/stalwart-v1/database/CURRENT ]
[ -n "$(find /var/lib/stalwart-v1/database -maxdepth 1 -type f -name 'MANIFEST-*' -print -quit)" ]
[ -z "$(find /var/lib/stalwart-v1/database -type l -print -quit)" ]
command -v curl >/dev/null
mkdir -m 700 "$stage"
printf '%s' '{"@type":"RocksDb","path":"/var/lib/stalwart-v1/database"}' > /work/config.json
/usr/local/bin/stalwart --config /work/config.json >"$stage/stdout" 2>"$stage/stderr" &
server_pid=$!
cleanup() {
  kill -TERM "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
probe() {
  code=$(curl --noproxy '*' -sSk --connect-timeout 1 --max-time 1 -o /dev/null -w '%{http_code}' \
    -H 'X-Forwarded-For: 127.0.0.1' "$1" 2>/dev/null) || code=000
  [ "$code" = 200 ]
}
ready=false
deadline=$(($(date +%s) + 180))
while [ "$(date +%s)" -lt "$deadline" ]; do
  kill -0 "$server_pid" 2>/dev/null || break
  if probe https://127.0.0.1:443/healthz/ready || probe http://127.0.0.1:8080/healthz/ready; then
    ready=true
    break
  fi
  sleep 1
done
kill -TERM "$server_pid" 2>/dev/null || true
set +e
wait "$server_pid"
server_status=$?
set -e
trap - EXIT HUP INT TERM
if [ "$ready" != true ]; then
  printf '{"v1Startup":"failed","reason":"loopback_readiness_not_observed"}\n'
  exit 1
fi
if [ "$server_status" -ne 0 ]; then
  printf '{"v1Startup":"failed","reason":"unclean_shutdown"}\n'
  exit 1
fi
printf 'ready-and-cleanly-stopped\n' > "$stage/ACCEPTED"
sync
printf '{"v1Startup":"pass","version":"1.0.1","loopbackReady":true,"cleanShutdown":true,"rehearsalOnly":true,"oauthAccepted":false}\n'
