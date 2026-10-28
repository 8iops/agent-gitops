# Cube recovery and qualification

The active runtime authority is this repository. Upstream source is pinned to
CubeSandbox commit `8721dd151971ce3c2966482bbd32904ad98f378e` and vendored with its
license under `vendor/chart`. `images.lock.json` pins every deployed image.

`render.py` compiles the reviewed values into `clusters/re8ch/cube-recovery-resources.yaml`
and `platform-seed.yaml`. The existing domain compiler packages runtime objects
into `agent-runtime-domain-cube-trial`. The existing static-release workflow
builds/signs one immutable bundle and the bounded executor adopts/reconciles it.
No new runtime controller or polling service is introduced.

## Native capability gap

Upstream Helm renders plaintext credentials and random test certificates; GitHub
Secrets cannot provision an in-cluster Secret without transporting those values.
A one-shot platform Job instead generates credentials inside the cluster. Its
Role can only get/patch the two pre-created, exact Secret names. No create/list,
other Secrets, GitHub credential sync, or secret logging is granted. Replay
preserves credentials; partial/malformed state fails closed. Managed certificates
use a namespace-local cert-manager Issuer. Credentials must be rotated with the
corresponding databases, never by clearing the credential seed.

## Isolation

Recovery uses new PVC names on `cephfs-r640` and host storage under
`/data/cube-recovery`; it does not reuse old database or guest state. Fixed guest
paths are mapped to the isolated host paths. The host containerd socket is never
mounted. KVM was verified by the merged service-backend PR #2493 preflight.
PVM host installation, module loading, KVM chmod, udev changes, cluster DNS
rewrites, public Ingress and node eviction are disabled. Node initialization
creates a dedicated XFS loopback mount and fstab entry; it does not reformat an
existing device. Kernel/runtime images stay at the qualified v0.6.0 version.
The prior route-aware Cube startup patch is reused within the Pod network namespace.

The node identity can read node inventory and patch only R640; leases are limited
to cube-trial. The recovery control plane accepts ingress only from its namespace.
Existing public OAuth and route resources remain unchanged during qualification.

## Reviewed deployment order

1. Pass render/credential/isolation tests, server dry-run, signed PR and Actions.
2. Through Cloud Platform, apply the reviewed platform seed (excluding its Jobs)
   and the recovery ConfigMaps. Do not reapply empty Secret seeds after provisioning.
3. Run the credential and CIDR preflight Jobs. Require both to complete and the
   proxy Certificate to be Ready before starting runtime workloads.
4. Apply the exact reviewed recovery runtime through Cloud Platform for initial
   bootstrap. Apply only the cube-trial slice of generated domain-access.yaml.
5. Run the existing static-release workflow for the cube-trial contract. Reuse
   its signed digest for any retry. Runtime acceptance requires healthy control
   plane plus a real sandbox create/exec/write/pause/resume/read/delete test.
6. Deploy the persistent CompoCV test runtime and separate database only after
   that acceptance. Run synthetic mail -> private Issue/Project -> improvement
   PR verification and check production endpoints/configurations are unchanged.

Old Cube volumes may be retired under the owner's authorization after replacement
acceptance. Do not delete unrelated Secrets, storage or namespace resources.
