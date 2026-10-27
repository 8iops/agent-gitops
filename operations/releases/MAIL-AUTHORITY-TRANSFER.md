# Mail authority transfer

Stalwart belongs to agent-runtime. The imported 45 objects are the exact
rendered source of the healthy identity release accepted by run 40568937380.
`authority-transfers.json` pins that source, the previous accepted digest and
the existing field manager. No image/chart build, namespace move, credential
change, route change or PVC change is part of this transfer.

The new contract needs a newly signed envelope because the repository and
authority change. It must not pretend that the previous repository's signature
is an agent signature. The previous accepted state remains an audit record;
the target uses its own initially empty state and must earn healthy acceptance.

Platform cutover order (reviewed platform operations, never a local kubeconfig):

1. Stop new identity Mail dispatches and ensure no old execute job is running.
2. Verify the old accepted digest against `authority-transfers.json`; capture
   and recheck the UID of every one of the 45 existing objects. Abort on missing
   or replaced objects. Verify all three workloads remain healthy.
3. Reduce the old `identity-access-domain-mail-system` Role to `get` only,
   retaining its exact resource names and old state audit access. Check effective
   authorization for the old group against every transferred object, including
   any other matching bindings; deny patch/update/create/delete.
4. Install the target exact Role/Binding and empty state from `domain-access.yaml`.
   Never overwrite an existing target accepted state with bootstrap data.
5. Publish and execute the target contract with force disabled. Existing-only
   UID/RV guards apply; prune is disabled, and the old field manager is retained.
6. Independently verify healthy accepted state, unchanged workload UIDs, and old
   group write denial before recording transfer complete.

On a failed first target attempt, retain both result and old accepted evidence.
Before resuming the old authority, revoke target object writes and verify denial;
only then restore the old reviewed Role. Do not allow simultaneous writers.
The first target attempt has no target accepted predecessor to roll back to;
it must not silently trust a cross-repository rollback artifact.

All imported ConfigMaps are reviewed configuration or provisioning plans/scripts;
none is a controller-generated status/output ConfigMap. Their contents remain
unchanged. This transfer does not retire or rerun historical bootstrap Jobs.
