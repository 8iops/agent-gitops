"""Compare a verified accepted release and replay only its drifted, owned objects."""
import json
import os
import subprocess
import time
from pathlib import Path
from uuid import UUID
from ssa_compare import retry_read_conflict, safe_failure_reason, transport_markers, configmap_owned_fields_match

import yaml
from ssa_executor import Executor, Rejected, Store, object_identity


def comparable(obj):
    # Ignore API bookkeeping and asynchronous status. Keep meaningful spec and metadata.
    obj.pop("status", None)
    for key in ("resourceVersion", "generation", "managedFields"):
        obj["metadata"].pop(key, None)
    return obj


def run(report):
    root = Path(os.environ["RUNNER_TEMP"])
    contract = yaml.safe_load(Path(os.environ["CONTRACT"]).read_text())
    operation = json.loads((root / "operation.json").read_text())
    rid = operation["releaseId"]
    digest = operation["bundle"]["digest"]
    report.update(release=rid, digest=digest)
    executor = Executor()
    executor.apply_only = True
    store = Store(root / "executor-state", rid)
    _, objects, _ = executor.validate(contract, operation, root / "pulled/release.bundle", store)
    manager = contract["spec"]["authorization"]["fieldManager"]
    state_ref = json.loads((root / "state-cm.json").read_text())["metadata"]

    def require_accepted():
        result = executor.command(["kubectl", "get", "configmap", state_ref["name"], "-n", state_ref["namespace"], "-o", "json"])
        state = json.loads(json.loads(result.stdout)["data"]["accepted-state.json"])
        if state["releaseId"] != rid or state["appliedDigest"] != digest or state.get("acceptedDigest", state.get("healthyDigest")) != digest or state["blocked"] or state.get("suspended"):
            raise ValueError("accepted state changed")

    def projection_request(phase, argv, stdin, timeout=60):
        started = time.monotonic()
        try:
            return executor.command(argv, stdin, timeout=timeout)
        except (Rejected, subprocess.TimeoutExpired) as error:
            report.setdefault("requestFailures", []).append({
                "object": report["checking"], "phase": phase,
                "elapsedSeconds": round(time.monotonic() - started, 2),
                "transport": transport_markers(error),
                "processDeadline": isinstance(error, subprocess.TimeoutExpired),
            })
            raise

    def project_once(item):
        data = json.dumps(item)
        live = json.loads(projection_request("read", ["kubectl", "get", "-f", "-", "--show-managed-fields=true", "-o", "json"], data).stdout)
        if live.get("kind") == "List":
            live, = live["items"]
        if object_identity(live) != object_identity(item):
            raise ValueError("unexpected readback identity")
        meta = live["metadata"]
        if meta.get("annotations", {}).get("delivery.re8ch.com/release-id") != rid:
            raise ValueError("release ownership differs")
        item["metadata"]["resourceVersion"] = meta["resourceVersion"]
        annotations = item["metadata"].get("annotations", {})
        audit_key = "delivery.re8ch.com/operation-id"
        if audit_key in annotations:
            annotations.pop(audit_key)
            if audit_key in meta["annotations"]:
                annotations[audit_key] = meta["annotations"][audit_key]
        if configmap_owned_fields_match(item, live, manager):
            return False
        argv = ["kubectl", "apply", "--server-side", "--field-manager=" + manager, "-f", "-"]
        predicted = json.loads(projection_request("server-dry-run", argv + ["--dry-run=server", "-o", "json"], json.dumps(item), timeout=120).stdout)
        return comparable(predicted) != comparable(live)

    def project_with_read_retry(item):
        try:
            return project_once(item)
        except (Rejected, subprocess.TimeoutExpired) as error:
            detail = str(error).lower()
            timed_out = isinstance(error, subprocess.TimeoutExpired) or any(
                message in detail for message in ("context deadline exceeded", "i/o timeout", "timed out", "the server was unable to return a response in the time allotted")
            )
            if not timed_out:
                raise
        # Both calls in project_once are read-only. Re-read acceptance and resourceVersion.
        time.sleep(2)
        require_accepted()
        return project_once(item)

    def project(item):
        return retry_read_conflict(lambda: project_with_read_retry(item))

    require_accepted()
    prepared = executor.with_audit(objects, operation)
    changed = []
    for item in prepared:
        identity = object_identity(item)
        report["checking"] = identity
        differs = project(item)
        report["objects"].append({"id": identity, "drift": differs})
        if differs:
            changed.append(item)
    if changed:
        require_accepted()
        result = executor.reconcile(contract, operation, root / "pulled/release.bundle", root / "executor-state")
        (root / "executor-result.json").write_text(json.dumps(result))
        if result["outcome"] not in {"applied", "healthy"}:
            raise ValueError("executor did not complete SSA")
        report["applied"] = [object_identity(item) for item in changed]
    require_accepted()
    for item in prepared:
        report["checking"] = object_identity(item)
        if project(item):
            raise ValueError("readback differs")

    report.pop("checking", None)
    report["outcome"] = "recovered" if changed else "aligned"
    return True


if __name__ == "__main__":
    report = {"delivery": str(UUID(os.environ["DELIVERY_ID"])), "objects": [], "applied": []}
    try:
        success = run(report)
    except Exception as error:
        # API errors can contain decrypted values or command input.
        report.update(outcome="blocked", error=type(error).__name__)
        if type(error) is ValueError and str(error) in {"accepted state changed", "release ownership differs", "readback differs", "executor did not complete SSA"}:
            report["reason"] = str(error)
        if isinstance(error, Rejected):
            detail = str(error).lower()
            if "failed calling webhook" in detail:
                report["reason"] = "admission webhook unavailable"
            elif "conflict" in detail:
                report["reason"] = "SSA field ownership conflict"
            elif "forbidden" in detail:
                report["reason"] = "executor access denied"
            elif "notfound" in detail or "not found" in detail:
                report["reason"] = "object missing"
        if type(error).__name__ == "Rejected":
            report["reason"] = safe_failure_reason(error)
        success = False
    print(json.dumps(report))
    raise SystemExit(0 if success else 1)
