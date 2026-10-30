# Cold backup on the approved overseas-flk node

The user approved overseas-flk backup placement and a source pause. These
reviewable resources use the existing authenticated platform kubectl path,
because platform SSH alias resolution is broken. No workstation credentials,
public addresses, hostPath mounts or node SSH changes are required.

This directory is outside the production Kustomization. All three Jobs start
suspended. Root is the single owner of pause/resume and freezes competing mail
release reconciliations during the window. No source writes are authorized by
creating the resources alone.

## Exact storage and key custody

- Existing source: mail-system/stalwart-flk-local-data, mounted **read-only** only
  by stalwart-cold-backup. No fsGroup is set on that Job, avoiding source chown.
- New destination: mail-system/stalwart-migration-backup-overseas, local-path,
  4Gi requested, selected through the Jobs' overseas-flk hostname nodeSelector.
  Resolve the bound PV's actual local path after scheduling; never guess it.
- Final encrypted archive: `/backup/baseline/stalwart-v01618.tar.cms` on that PVC;
  full hashes and byte count in `verification.json`, completion marker `ACCEPTED`.
  Plaintext archive and decrypted comparison exist only in bounded memory emptyDir.
- Key: mail-system/stalwart-migration-backup-key Secret, initially empty with a
  pending marker. Dedicated key-init SA can only PATCH this exact Secret. Its
  atomic JSON Patch tests pending, writes RSA-3072 key/certificate, sets ready and
  immutable=true. It cannot list/get/delete/create Secrets. Failed/repeated init
  must not reset the Secret. Keys stay server-side; no API response body is logged.
- The archive/preflight Jobs have no API token, no ServiceAccount authority and
  deny-all networking. Secret projection is read-only. The image is the exact
  observed official Stalwart v0.16.18 digest; no new binary build is needed.

The source and backup share the overseas-flk fault domain. Retain both source and
backup; this is migration recovery, not host-loss disaster recovery. Preserve the
key Secret through the backup lifetime; deleting it destroys recovery. Do not
prune the initialized Secret or backup PVC through the normal release lifecycle.
The key-init API token expires after 600 seconds and has only named patch access.

## Prepare while service remains online

1. Review/render `kustomize build operations/stalwart-self-service/backup`.
   Use the platform plan and reviewed apply flow, not local cluster credentials.
   Retain exact resource metadata and audit references. No key value is in Git.
2. Start only stalwart-backup-key-init. It uses memory scratch and file-based
   curl request/header inputs; no credential in process argv. API response is
   discarded. Verify Job success and Secret metadata ready/immutable, never data.
   It is intentionally single-shot: do not delete or reset its accepted Secret.
3. Start only stalwart-backup-preflight. It mounts the destination and key, **no
   source PVC**. Require destination write success, synthetic encrypt/decrypt
   comparison and tampered GCM tag rejection. Its certificate hash is written to
   PREFLIGHT.json; private material is never logged. Resolve destination PV/node,
   inspect capacity and confirm enough memory before starting the outage.
4. Root confirms no active mail-domain apply run or competing rollout, fresh
   StatefulSet UID/resourceVersion, replicas=1, and each CronJob's suspension state.
   Current graceful termination is 120 seconds. Confirm no active writer Jobs.

Real synthetic probing in the existing official container already passed
CMS AES-256-GCM roundtrip and flipped-tag rejection on 2026-10-30:
`audit://operations/op_0ffb0389ab804acbaf2bc9e0f7346738`.
The dedicated preflight repeats this using the actual retained key and destination.

## One bounded production pause

Root suspends the three recorded Stalwart writer/reloader CronJobs, waits for
active writers to finish, scales only stalwart-flk to 0 and waits for clean Pod
termination (respecting 120 seconds). No other owner may resume it concurrently.
Confirm no source process remains before starting stalwart-cold-backup.

The Job has zero retries and a 300-second deadline. It makes a whole numeric-owner
tar archive, hashes it, encrypts using CMS AES-256-GCM, decrypts, performs a full
byte comparison, records both full hashes, syncs and writes ACCEPTED last. It
refuses to overwrite an existing baseline directory. A failed directory is kept
for diagnosis; do not remove or call it accepted automatically.

After Complete and verified marker/hash metadata, root immediately restores
recorded replicas and CronJob states, checks original imageID/Ready endpoint and
OAuth/mail/DAV health. On failure/timeout, first stop the backup reader, then
restore the unchanged source. Do not spend outage time building images, changing
source version or running a long rehearsal. The source PVC is never deleted.

## Restore and retention

After source recovery, decrypt the accepted archive into an isolated restored
copy, verify its plaintext SHA-256 against verification.json, then validate
v0.16.18 data before the reviewed v0.16.27/v1 worker sequence. No archive, key or
personal contents may be returned in tool output. Only audit refs, hashes, byte
counts and status are evidence. Keep the source untouched and retain key/backup
until the user accepts migration and its rollback window has ended.

The key-init Job may be removed after successful initialization and its named
patch Role/RoleBinding/SA retired; never delete the key Secret during that cleanup.

## Maintenance placement and recovery scheduling

The overseas node has exact NoSchedule taints dedicated=overseas-edge and
scheduling.re8ch.com/capacity-window=closed. These one-shot maintenance Jobs copy
the existing Stalwart StatefulSet's two Equal tolerations; they do not clear
node taints, open tenant capacity windows or use wildcard tolerations. Production
stalwart-flk already has both tolerations, verified before the pause
(`audit://operations/op_bbd93f469bb04b07b06c844da192238e`).

Observed node allocatable memory is 3906236Ki, CPU 2. Actual usage was 1838Mi and
1008m; the source used 190Mi and 2m. Cold-backup requests 1Gi and is capped at
1536Mi/1CPU; key/preflight are capped at 128Mi/1CPU and run sequentially. At that
snapshot, stopping the source leaves headroom for the bounded backup. Recheck
fresh node pressure and scheduling before pause; a changed workload/metric may
invalidate this estimate. Audits `audit://operations/op_f07e8c01f3d944f19aa32396ddcc0313`,
`audit://operations/op_efee11a1b55c4558ad382cf5fe69dd82`,
`audit://operations/op_8f6bedcf8d35499eb01bfb725db3a7e5`.
