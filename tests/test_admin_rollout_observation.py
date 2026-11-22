import json
from subprocess import CompletedProcess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"operations/releases"))
from observe_runtime import tenant_api_rollout


def test_diagnostics_preserve_failure_state_without_configuration_or_raw_messages():
    class Fixture:
        def command(self, argv, **kwargs):
            assert kwargs['timeout'] == 12
            assert not any(action in argv for action in ['apply', 'patch', 'delete'])
            if 'deployment' in argv:
                return CompletedProcess(argv, 0, json.dumps({'spec': {'env': {'token': 'DO-NOT-EXPOSE'}},
                                   'status': {'readyReplicas': 0, 'conditions': [{'type': 'Available', 'status': 'False', 'reason': 'MinimumReplicasUnavailable', 'message': 'DO-NOT-EXPOSE'}]}}), '')
            return CompletedProcess(argv, 0, json.dumps({'items': [{'metadata': {'name': 'tenant-api-test'},
                'spec': {'env': 'DO-NOT-EXPOSE'}, 'status': {'phase': 'Pending', 'containerStatuses': [
                    {'name': 'runtime', 'ready': False, 'restartCount': 2,
                     'state': {'waiting': {'reason': 'ImagePullBackOff', 'message': 'DO-NOT-EXPOSE'}}}]}}]}), '')
    result = tenant_api_rollout(Fixture())
    assert result['pods'][0]['containers'][0]['state'] == {'waiting': {'reason': 'ImagePullBackOff'}}
    assert 'DO-NOT-EXPOSE' not in json.dumps(result)


def test_diagnostic_denials_stay_explicit_without_exposing_api_errors():
    class Denied:
        def command(self, *args, **kwargs):
            raise RuntimeError('DO-NOT-EXPOSE')
    result = tenant_api_rollout(Denied())
    assert result['pods']['observation'] == 'not-authorized-or-unavailable'
    assert result['deployment']['observation'] == 'not-authorized-or-unavailable'
    assert 'DO-NOT-EXPOSE' not in json.dumps(result)
