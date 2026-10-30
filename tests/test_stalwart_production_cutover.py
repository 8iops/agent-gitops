from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def test_production_cutover_is_single_node_bounded_and_uses_existing_local_pvcs():
    job = yaml.safe_load(
        (ROOT / "operations/stalwart-self-service/production-cutover/job.yaml").read_text()
    )
    spec = job["spec"]
    pod = spec["template"]["spec"]

    assert job["metadata"] == {
        "name": "stalwart-production-v1-migrate",
        "namespace": "mail-system",
        "labels": {
            "app.kubernetes.io/name": "stalwart-production-migration",
            "app.kubernetes.io/component": "production-migration",
        },
        "annotations": {"governance.re8ch.com/reviewed-source": "8iops/agent-gitops"},
    }
    assert spec["backoffLimit"] == 0
    assert 0 < spec["activeDeadlineSeconds"] <= 1800
    assert pod["nodeSelector"] == {"kubernetes.io/hostname": "overseas-flk"}
    claims = {
        volume["name"]: volume["persistentVolumeClaim"]["claimName"]
        for volume in pod["volumes"]
        if "persistentVolumeClaim" in volume
    }
    assert claims == {
        "source": "stalwart-flk-local-data",
        "target": "stalwart-rehearsal-target-v1-local",
        "state": "stalwart-rehearsal-migration-state-local",
    }


def test_production_cutover_runs_the_native_final_chain_without_exposing_reports():
    job = yaml.safe_load(
        (ROOT / "operations/stalwart-self-service/production-cutover/job.yaml").read_text()
    )
    containers = job["spec"]["template"]["spec"]["initContainers"]
    migration = next(item for item in containers if item["name"] == "migrate-production")
    startup = next(item for item in containers if item["name"] == "verify-v1-startup")
    script = migration["args"][0]

    assert '"path":"/source"' in script
    assert '"path":"/source/database"' not in script
    assert migration["image"].endswith(
        "@sha256:1e936a872424bb8856ac2186129266f5179e516d9dbf58853c73364e6e0fc563"
    )
    assert startup["image"].endswith(
        "@sha256:b9da4df8b4efc06bc926dd6e990bdeb0ad7b9261a7c3893d74b0461a00bb389b"
    )
    result = next(
        item
        for item in job["spec"]["template"]["spec"]["containers"]
        if item["name"] == "result"
    )
    assert "/target/.r640-migration-v2-complete" in result["args"][0]
    for command in (
        "stalwart-migrate prepare",
        "stalwart-migrate run --source",
        "stalwart-migrate verify --full",
        "stalwart-migrate run --final --yes",
    ):
        assert command in script
    assert "stdout" in script and "stderr" in script
    assert "cat $state" not in script
    assert "secret" not in str(job).lower()
