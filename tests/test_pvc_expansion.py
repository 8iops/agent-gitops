"""Protected existing PVC expansion never transfers SSA ownership or data."""
import copy
import json
import subprocess

import pytest
from test_ssa_release_executor import executor


def pvc(storage='4Gi'):
    return {'apiVersion': 'v1', 'kind': 'PersistentVolumeClaim',
            'metadata': {'name': 'state', 'namespace': 'tenant-infrastructure',
                         'annotations': {'helm.sh/resource-policy': 'keep',
                                         'delivery.re8ch.com/release-id': 'exact-state',
                                         'delivery.re8ch.com/operation-id': 'approved-operation'}},
            'spec': {'accessModes': ['ReadWriteOnce'], 'storageClassName': 'rbd-r640',
                     'resources': {'requests': {'storage': storage}}}}


class PvcRunner:
    def __init__(self):
        self.live = pvc('1Gi')
        self.live['metadata'].update(uid='original', resourceVersion='17')
        self.live['spec'].update(volumeName='bound-data-volume', volumeMode='Filesystem')
        self.calls = []
        self.fault = None
        self.patches = 0

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs.get('input')))
        if argv[:2] == ['kubectl', 'get']:
            if self.fault == 'missing':
                return subprocess.CompletedProcess(argv, 1, '', 'NotFound')
            if any(arg.startswith('jsonpath=') for arg in argv):
                return subprocess.CompletedProcess(argv, 0, 'original 17', '')
            live = copy.deepcopy(self.live)
            if self.fault == 'replaced':
                live['metadata']['uid'] = 'replacement'
            return subprocess.CompletedProcess(argv, 0, json.dumps(live), '')
        assert argv[:2] == ['kubectl', 'patch']
        assert '--type=merge' in argv and '--patch-file=-' in argv
        assert '--field-manager=bounded-release' in argv
        assert not any('force' in arg or 'server-side' in arg for arg in argv)
        self.patches += 1
        if self.fault == 'conflict':
            return subprocess.CompletedProcess(argv, 1, '', 'error: Operation cannot be fulfilled on persistentvolumeclaims "state": the object has been modified; please apply your changes to the latest version and try again')
        return subprocess.CompletedProcess(argv, 0, '', '')


def apply(runner, item, dry_run=False, **kwargs):
    executor.Executor(runner=runner, sleeper=lambda _: None).apply(
        [item], 'bounded-release', dry_run=dry_run, require_existing=True, **kwargs)


def test_expansion_dry_run_and_write_only_patch_capacity_and_audit():
    runner = PvcRunner()
    item = pvc()
    apply(runner, item, dry_run=True)
    apply(runner, item)
    patches = [(args, json.loads(data)) for args, data in runner.calls if args[:2] == ['kubectl', 'patch']]
    assert len(patches) == 2
    assert '--dry-run=server' in patches[0][0]
    assert '--dry-run=server' not in patches[1][0]
    assert patches[0][1] == patches[1][1] == {
        'metadata': {'uid': 'original', 'resourceVersion': '17', 'annotations': {key: value for key, value in item['metadata']['annotations'].items() if key.startswith('delivery.re8ch.com/')}},
        'spec': {'resources': {'requests': {'storage': '4Gi'}}}}
    assert 'uid' not in item['metadata']


@pytest.mark.parametrize('storage', ['1Gi', '1024Mi', '1073741824'])
def test_equal_capacity_replay_is_idempotent(storage):
    runner = PvcRunner()
    apply(runner, pvc(storage))
    assert runner.patches == 1


@pytest.mark.parametrize('storage', ['512Mi', '0', '-1Gi', 'NaN', '4garbage', '1e999', '9223372036854775808'])
def test_shrink_and_invalid_capacity_are_rejected_before_patch(storage):
    runner = PvcRunner()
    with pytest.raises(executor.Rejected):
        apply(runner, pvc(storage))
    assert runner.patches == 0


@pytest.mark.parametrize('field,value', [('storageClassName', 'other'), ('accessModes', ['ReadWriteMany']),
                                        ('volumeName', 'replacement'), ('volumeMode', 'Block')])
def test_expansion_cannot_change_other_spec_fields(field, value):
    runner = PvcRunner()
    item = pvc()
    item['spec'][field] = value
    with pytest.raises(executor.Rejected, match='other spec'):
        apply(runner, item)
    assert runner.patches == 0


def test_unrelated_metadata_cannot_be_silently_changed():
    runner = PvcRunner()
    item = pvc()
    item['metadata']['annotations']['other.example/policy'] = 'changed'
    with pytest.raises(executor.Rejected, match='other metadata'):
        apply(runner, item)
    assert runner.patches == 0


@pytest.mark.parametrize('fault', ['missing', 'replaced'])
def test_missing_or_replaced_pvc_never_recreated(fault):
    runner = PvcRunner()
    runner.fault = fault
    with pytest.raises(executor.Rejected):
        apply(runner, pvc())
    assert runner.patches == 0


def test_resource_version_conflict_fails_after_bounded_revalidation():
    runner = PvcRunner()
    runner.fault = 'conflict'
    with pytest.raises(executor.Rejected):
        apply(runner, pvc())
    assert runner.patches == 3
    assert sum(args[-1] == 'json' for args, _ in runner.calls if args[:2] == ['kubectl', 'get']) == 3


def test_protected_force_guard_remains_in_effect():
    runner = PvcRunner()
    item = pvc()
    with pytest.raises(executor.Rejected, match='cannot use force'):
        apply(runner, item, force_objects={executor.object_identity(item)})
    assert runner.patches == 0
