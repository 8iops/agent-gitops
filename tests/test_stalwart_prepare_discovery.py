import importlib.util
import json
from pathlib import Path
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / 'operations/stalwart-self-service/rehearsal/prepare-discovery'
spec = importlib.util.spec_from_file_location('projection', PROBE / 'project.py')
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)


def evidence(tmp_path):
    (tmp_path / 'native').mkdir()
    (tmp_path / 'native-exit').write_text('1\n')
    (tmp_path / 'native/answers.toml').write_text('version = 1\n# Source secret: SENTINEL_PASSWORD\n# [global.categories]\n# include = ["mail"]\n# [instance.oidc_directory."x:Directory/42"]\n# secret = "SENTINEL_PASSWORD"\n')
    (tmp_path / 'native/prepare-report.txt').write_text('stalwart-migrate prepare report\n\nSummary: 20 objects to write, 0 dropped, 2 warnings, 0 errors, 0 questions answered now.\nrun will refuse to start until these are resolved:\n  categories: not answered\n  oidc_directory for x:Directory/42: not answered\n\nChanges:\n  secret SENTINEL_PASSWORD\n')
    return tmp_path


def test_only_counts_and_known_prompt_names_escape(tmp_path):
    output = projection.project(evidence(tmp_path))
    assert output['discovery'] == 'questions_pending'
    assert output['promptCounts'] == {'categories': 1, 'oidc_directory': 1}
    assert output['migrationExecuted'] is False
    assert output['policyApproved'] is False
    serialized = json.dumps(output)
    assert 'SENTINEL' not in serialized
    assert 'Directory/42' not in serialized


@pytest.mark.parametrize('change', ['native_failure', 'invalid_problem', 'conversion_error', 'unreadable', 'answered', 'oversize', 'symlink', 'duplicate', 'unknown_prompt', 'missing_problem', 'unexpected_success'])
def test_rejects_incomplete_or_non_question_failures(tmp_path, change):
    stage = evidence(tmp_path)
    answers = stage / 'native/answers.toml'
    report = stage / 'native/prepare-report.txt'
    if change == 'native_failure': (stage / 'native-exit').write_text('2')
    elif change == 'unexpected_success': (stage / 'native-exit').write_text('0')
    elif change == 'invalid_problem': report.write_text(report.read_text().replace('categories: not answered', 'categories: secret SENTINEL_PASSWORD invalid'))
    elif change == 'conversion_error': report.write_text(report.read_text().replace('0 errors', '1 errors'))
    elif change == 'unreadable': report.write_text(report.read_text().replace('run will', 'Warning: 1 settings objects are unreadable\nrun will'))
    elif change == 'answered': answers.write_text(answers.read_text() + '\n[global.categories]\ninclude=["mail"]\n')
    elif change == 'oversize': answers.write_text('#' * (projection.MAX_BYTES + 1))
    elif change == 'symlink':
        other = stage / 'raw'; answers.rename(other); answers.symlink_to(other)
    elif change == 'duplicate': answers.write_text(answers.read_text() + '# [global.categories]\n')
    elif change == 'unknown_prompt': answers.write_text(answers.read_text() + '# [global.SENTINEL_PASSWORD]\n')
    elif change == 'missing_problem': report.write_text(report.read_text().replace('  categories: not answered\n', ''))
    with pytest.raises((projection.Invalid, OSError)):
        projection.project(stage)


def test_container_boundary():
    job = yaml.safe_load((PROBE / 'job.yaml').read_text())
    pod = job['spec']['template']['spec']
    assert job['spec']['suspend'] and job['spec']['backoffLimit'] == 0
    assert pod['automountServiceAccountToken'] is False
    assert len(pod['initContainers']) == 1
    source = next(v for v in pod['volumes'] if v['name'] == 'source')
    assert source['persistentVolumeClaim'] == {'claimName': 'stalwart-rehearsal-source-v01627-local', 'readOnly': True}
    assert {v['name'] for v in pod['volumes']} == {'source', 'state', 'config', 'tmp', 'scripts'}
    assert all(m['readOnly'] for m in pod['containers'][0]['volumeMounts'])
    script = (PROBE / 'prepare.sh').read_text()
    assert 'startup-v01627-v2/ACCEPTED' in script
    assert 'stalwart-migrate prepare ' in script
    assert '--target' not in script and ' run ' not in script
