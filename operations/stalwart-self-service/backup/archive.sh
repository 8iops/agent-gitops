#!/bin/sh
set -eu
umask 077
# Root must confirm all source writers have stopped before unsuspending this Job.
# No network/API credentials are mounted. Plaintext lives only in tmpfs.
trap 'rm -f /work/source.tar /work/restored.tar' EXIT
[ -d /source ] && [ -f /keys/privateKey.pem ] && [ -f /keys/certificate.pem ]
[ ! -e /backup/baseline ]
mkdir -m 700 /backup/baseline
archive=/backup/baseline/stalwart-v01618.tar.cms
# Exclude no database files; preserve numeric owners in the archive.
tar --numeric-owner -C /source -cf /work/source.tar .
plain_hash=$(sha256sum /work/source.tar | cut -d ' ' -f 1)
plain_bytes=$(stat -c%s /work/source.tar)
openssl cms -encrypt -aes-256-gcm -binary -in /work/source.tar \
  -out "$archive" -outform DER /keys/certificate.pem
openssl cms -decrypt -binary -inform DER -in "$archive" \
  -recip /keys/certificate.pem -inkey /keys/privateKey.pem -out /work/restored.tar
cmp /work/source.tar /work/restored.tar
restored_hash=$(sha256sum /work/restored.tar | cut -d ' ' -f 1)
[ "$plain_hash" = "$restored_hash" ]
cipher_hash=$(sha256sum "$archive" | cut -d ' ' -f 1)
printf '{"status":"verified","plaintextBytes":%s,"plaintextSha256":"%s","ciphertextSha256":"%s","keySecretRef":"mail-system/stalwart-migration-backup-key","algorithm":"CMS AES-256-GCM RSA-3072"}\n' \
  "$plain_bytes" "$plain_hash" "$cipher_hash" > /backup/baseline/verification.json
sync
# Marker is written only after successful full decryption, comparison and sync.
printf 'verified\n' > /backup/baseline/ACCEPTED
sync
printf 'encrypted_archive_full_roundtrip=pass\n'
