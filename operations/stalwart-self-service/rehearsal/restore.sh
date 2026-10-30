#!/bin/sh
set -eu
umask 077
trap 'rm -f /work/restored.tar' EXIT
[ "$(cat /backup/baseline/ACCEPTED)" = verified ]
[ ! -e /restore/database ]
expected_cipher=$(sed -n 's/.*"ciphertextSha256":"\([0-9a-f]*\)".*/\1/p' /backup/baseline/verification.json)
expected_plain=$(sed -n 's/.*"plaintextSha256":"\([0-9a-f]*\)".*/\1/p' /backup/baseline/verification.json)
[ "${#expected_cipher}" = 64 ] && [ "${#expected_plain}" = 64 ]
actual_cipher=$(sha256sum /backup/baseline/stalwart-v01618.tar.cms | cut -d ' ' -f 1)
[ "$actual_cipher" = "$expected_cipher" ]
openssl cms -decrypt -binary -inform DER -in /backup/baseline/stalwart-v01618.tar.cms \
  -recip /keys/certificate.pem -inkey /keys/privateKey.pem -out /work/restored.tar
actual_plain=$(sha256sum /work/restored.tar | cut -d ' ' -f 1)
[ "$actual_plain" = "$expected_plain" ]
mkdir -m 700 /restore/database
tar --no-same-owner -C /restore/database -xf /work/restored.tar
sync
printf 'restored_archive_checksum=pass extraction=complete plaintext_sha256=%s ciphertext_sha256=%s\n' \
  "$actual_plain" "$actual_cipher"
