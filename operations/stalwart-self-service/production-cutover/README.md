# Stalwart production v1 cutover

This reviewed one-shot Job is the production migration path after the
`mail-system/stalwart-flk` StatefulSet has reached zero replicas. It migrates
the live local RocksDB source directly to the existing overseas-node v1 target
PVC using the six policy answers produced and reviewed by the completed
rehearsal. It does not copy the source into another rehearsal and it does not
run a rollback experiment.

The Job fails closed at the first unsuccessful native phase: answered prepare,
forward run, full verification, final run, post-final full verification, or a
real v1.0.1 startup/readiness/clean-stop check. Native reports remain on the
migration state PVC and are not printed to Actions or Agent logs.

Apply the manifest from its signed, merged commit only through the Cloud
Platform `kubectl.exec` authority. After the Job completes, read only its fixed
status lines and phase/exit state; do not copy native reports or mailbox
content into GitHub logs.
