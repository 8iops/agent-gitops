# Isolated Stalwart restore and migration

Status: the encrypted cold backup completed successfully, and root restored the
original service. The first restore attempt never started its container because
RBD MountDevice timed out on overseas-flk. That Job reached Failed/DeadlineExceeded;
no reader remains. Its PVC and diagnostics are retained, not deleted or reused.

The replacement candidate uses **new local-path PVCs and Jobs ending in -local**,
all placed on the user-approved overseas-flk node. No worker mounts the original
stalwart-flk-local-data. All Jobs start suspended, run one at a time and have no
API token. Nothing is included in the production Kustomization.

## Placement, isolation and resources

The existing mail-system namespace is used so the accepted archive and key can
be mounted without cross-namespace transfer or additional credential grants.
No Namespace, ResourceQuota or Pod Security label changes affect existing mail.
Deny-all networking selects only `re8ch.com/stalwart-rehearsal=true` Pods.

Five new local-path claims request 9Gi total: four 2Gi copies (baseline restore,
working v0.16.27, empty v1 target and empty rollback target) and 1Gi migration
state. Together with the accepted 4Gi backup PVC, the requested working set is
13Gi. Old failed RBD claims remain separately allocated for diagnosis; this is
not a storageClass mutation or a destructive cleanup.

Fresh read-only filesystem inspection returned 21895392 KiB available (about
20.9GiB) on 2026-10-30, audit `audit://operations/op_d2c569d3abc043fc8d8b2eac516a87a4`.
Each Job requests 512Mi/100m and is capped at 1536Mi/1CPU. Run **one Job at a time**;
if memory pressure/OOM or low space occurs, stop and reassess instead of squeezing
the online source. Local-path requests are scheduling declarations, not proof of
disk quota enforcement. Check actual free space before each material copy.

Jobs use only the exact dedicated=overseas-edge and
scheduling.re8ch.com/capacity-window=closed Equal/NoSchedule tolerations already
used by the source. No node taints or tenant capacity windows are changed.
The local data copies share a host fault domain; keep the accepted encrypted
archive and key throughout rehearsal and the approved rollback window.

## Restore sequence

1. Apply the reviewed resources as suspended through the authenticated platform
   path. This creates new -local claims and a new restore Job, without retrying
   the failed RBD Job. Verify overseas-flk placement and current node capacity.
2. After the v2 synthetic preflight below passes, resume only
   `stalwart-rehearsal-restore-local-v2`. It mounts the accepted backup
   PVC/key read-only and only the baseline target. It requires ACCEPTED,
   verifies encrypted SHA-256, decrypts in bounded memory, verifies full plaintext
   SHA-256 and only then extracts into its new owned database subdirectory. An existing
   database subdirectory is rejected; earlier partial root files remain untouched.
3. Require Complete and the two full hashes in the safe result line. Verify the
   restored database with the pinned original v0.16.18, using a distinct working
   copy for operations that can modify the store. Never mount the baseline or
   original source in a migration worker.
4. Copy accepted baseline into the new working v0.16.27 claim. Perform the
   separately reviewed copied-store patch upgrade and stop it cleanly before
   migration. Source production stays online and unchanged.

The cold-backup Job completed with full decrypt/compare/hash verification:
`audit://operations/op_f3036c2c4e46458b9067d8f2618c314f` and
`audit://operations/op_21038d9b68da4967a8e074bb7bc403eb`.
Failed first restore evidence: RBD DeadlineExceeded/operation already exists
`audit://operations/op_6ca3bc5bddb94b11b87dac03c6036e53`, terminal failure
`audit://operations/op_9e3537bc8b51462cb96832c9d67f2e35`, no remaining reader
`audit://operations/op_fb29fefa038f41b2b4d1e479d660d0b8`.

## Official migration workers

`upstream-artifacts.json` records official Stalwart v0.16.27/v1.0.1 and
stalwart-migrate 1.0.3 registry manifests whose response bytes were independently
SHA-256 checked. These are immutable digests, not claims of publisher-signature
verification. Apply the existing artifact-trust requirements before admission.
There is an official migration image; no custom build or runtime download is needed.

The [official v1.0.3 README](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/README.md)
requires v0.16.27 and explicitly says earlier versions must be upgraded first.
Do not run the converter directly on v0.16.18. A copied-store rehearsal must prove
whether a later production cutover can use a stopped copied-store upgrade; no
production upgrade or route cutover is part of this restore operation.

`workers.yaml` stays separate from the resource Kustomization. Its five suspended
Jobs use exact configs, copied stores, durable state, no retries and a 30-minute
per-phase deadline. Source mounts are read-only. Execute strictly in order:

1. `stalwart-rehearsal-migrate-prepare-local`: prepare --non-interactive. It fails
   until required conversion policy answers are reviewed and present in state.
   Do not weaken OIDC audience/scope or proxy trust settings to make it pass.
2. `stalwart-rehearsal-migrate-run-local`: incremental copy to empty target-v1.
3. `stalwart-rehearsal-migrate-final-local`: run --final --yes, only after every
   copied-source writer is stopped. This confirmation never applies to production.
4. `stalwart-rehearsal-migrate-verify-local`: verify --full. Review all conversion
   warnings and require no unexplained mismatches before isolated v1 testing.
5. `stalwart-rehearsal-migrate-rollback-local`: rollback --verify-full --yes into
   the empty rollback copy, retaining forward state and with v1 stopped. Compare
   aggregate integrity and documented v1-only losses before calling rollback valid.

Do not use --allow-errors, --allow-mass-removal or --force-after-final as shortcuts.
Retain state after failures and diagnose before any explicit retry. A copy or
mock test is not database acceptance or real scoped-token isolation evidence.

## Retention and next gate

Keep baseline archive/key, original source and migration state through acceptance
and the reviewed rollback window. Proposed rehearsal cleanup is seven days after
acceptance, subject to backup retention review; no automatic deletion is installed.
A future production cutover needs its own concrete plan, fresh final data sync,
real OAuth client/token tests and root-coordinated approval. Logs/PRs contain only
status, aggregate counts and hashes, never account data or secret values.

## Root-owned volume directory correction (v2)

The first local extraction verified ciphertext and plaintext hashes, then failed
only while applying tar's `.` entry metadata to the root-owned PVC mount root:
Cannot utime / Cannot change mode. It is a failed restore, not accepted data.
Audit `audit://operations/op_20c9a475a37149b39c821a014fb11d35`. Preserve its partial
root files for diagnosis; do not overwrite or promote them.

`stalwart-rehearsal-restore-preflight-v2` contains no backup or key mount. It proves
on the actual root-owned PVC that a synthetic archive containing `.` extracts
correctly into a UID-2000-owned child, compares payloads and preserves root owner.
Run this suspended Job first and require Complete plus its safe pass message.
Only then resume the new `stalwart-rehearsal-restore-local-v2` Job. It verifies the
same accepted archive's full hashes again, creates `/restore/database` mode 0700
as UID 2000 and extracts there. It rejects an existing database directory.

Every subsequent baseline copy must read **only source-restore-local/database**.
Working, v1 and rollback store JSON paths likewise end in `/database`. Never use
partial files left at the old PVC root as database input. This change needs no
root container, source permission changes or new PVC. Production remains online.
