import importlib.util
from pathlib import Path

import pytest
import yaml

BASE = Path(__file__).resolve().parents[1] / 'operations/stalwart-self-service/rehearsal/answered-prepare'
spec = importlib.util.spec_from_file_location('answered_prepare_verify', BASE / 'verify.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(tmp_path, *, questions=0):
    state = tmp_path / 'answered-prepare-v1'
    native = state / 'native'
    native.mkdir(parents=True)
    candidate = tmp_path / 'answers-candidate-v1'
    candidate.mkdir()
    answer = '''version = 1
[global.categories]
include = ["settings"]
[global.new_permissions]
action = "none"
[global.changed_defaults]
policy = "pin"
[instance.oidc_directory."x:Directory/42"]
unscoped_tokens = "interoperable"
[instance.oauth_registration."x:OidcProvider"]
action = "accept"
[instance.oidc_token_lifetimes."x:OidcProvider"]
action = "clamp"
'''
    (candidate / 'answers.toml').write_text(answer)
    (native / 'answers.toml').write_text('# secret=SENTINEL_SECRET\n' + answer)
    (state / 'native-exit').write_text('0\n')
    (native / 'prepare-report.txt').write_text(
        'stalwart-migrate prepare report\n\n'
        f'Summary: 2927 objects to write, 12 dropped, 63 warnings, 0 errors, {questions} questions answered now.\n'
        'private details SENTINEL_SECRET\n')
    module.ROOT = state
    module.CANDIDATE = candidate / 'answers.toml'
    return state


def test_bounded_success_does_not_emit_private_values(tmp_path):
    fixture(tmp_path)
    result = module.verify()
    assert result['answeredPrepareComplete'] is True
    assert 'SENTINEL_SECRET' not in str(result)


def test_unanswered_or_changed_answer_fails_closed(tmp_path):
    fixture(tmp_path, questions=1)
    with pytest.raises(ValueError):
        module.verify()
    fixture(tmp_path / 'another')
    (module.ROOT / 'native/answers.toml').write_text('version = 1\n')
    with pytest.raises(ValueError):
        module.verify()


def test_job_is_suspended_and_uses_isolated_source():
    job = yaml.safe_load((BASE / 'job.yaml').read_text())
    pod = job['spec']['template']['spec']
    assert job['spec']['suspend'] is True
    assert pod['automountServiceAccountToken'] is False
    claims = {v['name']: v['persistentVolumeClaim'] for v in pod['volumes'] if 'persistentVolumeClaim' in v}
    assert claims['source']['claimName'] == 'stalwart-rehearsal-source-v01627-local'
    assert claims['source']['readOnly'] is True
    assert claims['state']['claimName'] == 'stalwart-rehearsal-migration-state-local'
