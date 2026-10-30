#!/bin/sh
set -eu
umask 077
trap 'rm -f /work/plain /work/cipher /work/restored /work/rejected /backup/.preflight-write-test' EXIT
printf 'synthetic preflight\n' > /work/plain
printf 'write-test\n' > /backup/.preflight-write-test
openssl cms -encrypt -aes-256-gcm -binary -in /work/plain -out /work/cipher \
  -outform DER /keys/certificate.pem
openssl cms -decrypt -binary -inform DER -in /work/cipher \
  -recip /keys/certificate.pem -inkey /keys/privateKey.pem -out /work/restored
cmp /work/plain /work/restored
offset=$(($(stat -c%s /work/cipher) - 1))
last=$(od -An -tu1 -j "$offset" -N1 /work/cipher)
flipped=$((last ^ 1))
printf "\\$(printf '%03o' "$flipped")" | dd of=/work/cipher bs=1 seek="$offset" conv=notrunc status=none
if openssl cms -decrypt -binary -inform DER -in /work/cipher \
  -recip /keys/certificate.pem -inkey /keys/privateKey.pem -out /work/rejected >/dev/null 2>&1; then
  printf 'tamper_rejection=FAIL\n'; exit 1
fi
certificate_hash=$(sha256sum /keys/certificate.pem | cut -d ' ' -f 1)
printf '{"syntheticRoundtrip":"pass","tamperRejection":"pass","certificateSha256":"%s"}\n' \
  "$certificate_hash" > /backup/PREFLIGHT.json
sync
printf 'synthetic_roundtrip=pass tamper_rejection=pass destination_writable=pass\n'
