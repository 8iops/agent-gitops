#!/bin/sh
set -eu
umask 077
# Scratch is tmpfs. Never enable shell tracing or print the request/key.
trap 'rm -f /work/key.pem /work/cert.pem /work/request.json /work/headers' EXIT
openssl req -x509 -newkey rsa:3072 -nodes -keyout /work/key.pem \
  -out /work/cert.pem -subj /CN=stalwart-migration-backup -days 3650 >/dev/null 2>&1
printf '[{"op":"test","path":"/metadata/annotations/re8ch.com~1backup-key-state","value":"pending"},{"op":"add","path":"/data","value":{"privateKey.pem":"%s","certificate.pem":"%s"}},{"op":"replace","path":"/metadata/annotations/re8ch.com~1backup-key-state","value":"ready"},{"op":"add","path":"/immutable","value":true}]' \
  "$(base64 -w0 /work/key.pem)" "$(base64 -w0 /work/cert.pem)" > /work/request.json
printf 'Authorization: Bearer %s\nContent-Type: application/json-patch+json\n' \
  "$(cat /var/run/backup-api/token)" > /work/headers
curl --silent --show-error --fail --connect-timeout 10 --max-time 30 \
  --cacert /var/run/backup-api/ca.crt --header @/work/headers \
  --request PATCH --data-binary @/work/request.json --output /dev/null \
  "https://${KUBERNETES_SERVICE_HOST}:${KUBERNETES_SERVICE_PORT}/api/v1/namespaces/mail-system/secrets/stalwart-migration-backup-key"
printf 'backup_key_initialization=complete\n'
