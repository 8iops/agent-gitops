import json
import shutil
import subprocess
import pytest
import test_ssa_release_executor as base
import observe_runtime


def test_apply_only_does_not_consult_unhealthy_runtime(tmp_path):
    contract, operation, bundle = base.prepare(tmp_path)
    runner = base.Runner(live={'metadata': {'generation': 2}, 'spec': {'replicas': 1}, 'status': {'observedGeneration': 2, 'availableReplicas': 0}})
    ex = base.executor.Executor(runner=runner, now=lambda: base.NOW)
    ex.apply_only = True
    ex.wait_healthy = lambda *args: pytest.fail('SSA must not call Observe')
    result = ex.reconcile(contract, operation, bundle, tmp_path/'state', verify_signature=False)
    assert result['outcome'] == 'applied'
    assert result['health']['status'] == 'unknown'
    state = base.executor.Store(tmp_path/'state', operation['releaseId']).state()
    assert state['acceptedDigest'] == operation['bundle']['digest']
    assert 'healthyDigest' not in state
    assert not state['blocked']


def test_apply_only_still_rejects_ssa_conflicts(tmp_path):
    contract, operation, bundle = base.prepare(tmp_path)
    ex = base.executor.Executor(runner=base.Runner(conflict=True), now=lambda: base.NOW)
    ex.apply_only = True
    with pytest.raises(base.executor.Rejected):
        ex.reconcile(contract, operation, bundle, tmp_path/'state', verify_signature=False)


@pytest.mark.parametrize('outcome', ['applied', 'failed'])
@pytest.mark.parametrize('health', ['healthy', 'degraded', 'unknown'])
def test_observation_never_changes_ssa_outcome_or_state(tmp_path, monkeypatch, health, outcome):
    contract, operation, bundle = base.prepare(tmp_path)
    (tmp_path/'operation.json').write_text(json.dumps(operation))
    (tmp_path/'pulled').mkdir()
    shutil.copyfile(bundle, tmp_path/'pulled/release.bundle')
    (tmp_path/'result.json').write_text(json.dumps({'releaseId': operation['releaseId'], 'outcome': outcome, 'health': {'status': 'unknown', 'reason': 'execution evidence'}}))
    timeouts = []

    class Observer:
        timeout = None

        def wait_healthy(self, *args):
            self.timeout = args[1]
            timeouts.append(args[1])
            if health == 'unknown': raise RuntimeError('unavailable API; never expose raw payload')
            return health == 'healthy', 'observed runtime'

        def command(self, argv, **kwargs):
            assert kwargs['timeout'] == 12
            return subprocess.CompletedProcess(argv, 0, json.dumps({
                'metadata': {'generation': 1},
                'spec': {'replicas': 1},
                'status': {'observedGeneration': 1, 'updatedReplicas': 1,
                           'readyReplicas': 1, 'availableReplicas': 1},
            }), '')
    monkeypatch.setattr(observe_runtime, 'Executor', Observer)
    observe_runtime.observe(tmp_path, contract=contract, require_healthy=True)
    result = json.loads((tmp_path/'result.json').read_text())
    assert result['outcome'] == outcome
    assert result['health']['status'] == (health if outcome == 'applied' else 'unknown')
    if outcome == 'failed':
        assert result['health']['reason'] == 'execution evidence'
    assert not (tmp_path/'state').exists()
    assert timeouts == [contract['spec']['lifecycle']['healthTimeoutSeconds']]


def test_workload_rollout_rejects_fatal_waiting_without_exposing_messages():
    deployment = {
        'apiVersion': 'apps/v1', 'kind': 'Deployment',
        'metadata': {'name': 'catalog', 'namespace': 'tenant-infrastructure'},
    }

    class Fixture:
        def command(self, argv, **kwargs):
            assert kwargs['timeout'] == 12
            if 'events' in argv:
                value = {'items': [{
                    'type': 'Warning', 'reason': 'Failed', 'message': 'DO-NOT-EXPOSE',
                    'involvedObject': {'kind': 'Pod', 'name': 'catalog-pod'}, 'count': 3,
                }]}
            elif 'pods' in argv:
                value = {'items': [{
                    'metadata': {'name': 'catalog-pod'},
                    'status': {'phase': 'Pending', 'containerStatuses': [{
                        'name': 'runtime', 'ready': False, 'restartCount': 0,
                        'state': {'waiting': {'reason': 'ImagePullBackOff',
                                              'message': 'DO-NOT-EXPOSE'}},
                    }]},
                }]}
            else:
                value = {
                    'metadata': {'generation': 3},
                    'spec': {'replicas': 1, 'selector': {'matchLabels': {'app': 'catalog'}}},
                    'status': {'observedGeneration': 3, 'updatedReplicas': 1,
                               'readyReplicas': 0, 'availableReplicas': 0},
                }
            return subprocess.CompletedProcess(argv, 0, json.dumps(value), '')

    rollout = observe_runtime.workload_rollout(Fixture(), [deployment])
    healthy, reason = observe_runtime.rollout_health(rollout)
    assert not healthy
    assert 'ImagePullBackOff' in reason
    assert 'DO-NOT-EXPOSE' not in json.dumps(rollout)


def test_workload_controller_readiness_remains_authoritative_without_pod_list_access():
    deployment = {
        'apiVersion': 'apps/v1', 'kind': 'Deployment',
        'metadata': {'name': 'provider', 'namespace': 'tenant-infrastructure'},
    }

    class Fixture:
        def command(self, argv, **kwargs):
            if 'events' in argv or 'pods' in argv:
                raise RuntimeError('DO-NOT-EXPOSE')
            value = {
                'metadata': {'generation': 4},
                'spec': {'replicas': 1, 'selector': {'matchLabels': {'app': 'provider'}}},
                'status': {'observedGeneration': 4, 'updatedReplicas': 1,
                           'readyReplicas': 1, 'availableReplicas': 1,
                           'unavailableReplicas': 0},
            }
            return subprocess.CompletedProcess(argv, 0, json.dumps(value), '')

    rollout = observe_runtime.workload_rollout(Fixture(), [deployment])
    assert rollout['workloads'][0]['podObservation']['errorType'] == 'RuntimeError'
    assert observe_runtime.rollout_health(rollout)[0]
    assert 'DO-NOT-EXPOSE' not in json.dumps(rollout)


def test_observer_cli_fails_for_degraded_health(monkeypatch, tmp_path):
    monkeypatch.setattr(observe_runtime, 'observe', lambda root, require_healthy=False: {
        'health': {'status': 'degraded', 'reason': 'replicas unavailable'},
    })
    assert observe_runtime.main(['--require-healthy'], tmp_path) == 1
    assert observe_runtime.main([], tmp_path) == 0
