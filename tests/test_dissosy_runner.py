import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dissosy_runner', ROOT / 'operations/dissosy/runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_read_hosts_are_allowlisted():
    assert runner.check_read_url('https://www.re8ch.com/en/')
    for url in ('http://re8ch.com/', 'https://evil.example/', 'https://re8ch.com.evil.example/'):
        with pytest.raises(runner.ToolError):
            runner.check_read_url(url)


def test_github_writes_only_to_state_repo_issues():
    assert runner.check_github('GET', '/repos/re8ch/service-backend/actions/runs') == ('GET', '/repos/re8ch/service-backend/actions/runs')
    assert runner.check_github('post', f'/repos/{runner.STATE_REPO}/issues/8/comments')[0] == 'POST'
    for method, path in (('POST', '/repos/biziops/re8ch-corporate-site/pulls'),
                         ('PUT', f'/repos/{runner.STATE_REPO}/pulls/6/merge'),
                         ('DELETE', f'/repos/{runner.STATE_REPO}/issues/8'),
                         ('PATCH', f'/repos/{runner.STATE_REPO}/issues/../../x'),
                         ('GET', '/user')):
        with pytest.raises(runner.ToolError):
            runner.check_github(method, path)



def test_rendered_manifests_are_current_and_safe():
    subprocess.run([sys.executable, 'operations/dissosy/render.py', '--check'], cwd=ROOT, check=True)
    docs = list(yaml.safe_load_all((ROOT / 'clusters/re8ch/dissosy-resources.yaml').read_text()))
    cm = next(d for d in docs if d['kind'] == 'ConfigMap')
    assert cm['data']['runner.py'] == (ROOT / 'operations/dissosy/runner.py').read_text()
    for cj in (d for d in docs if d['kind'] == 'CronJob'):
        spec = cj['spec']
        assert spec['suspend'] is True and spec['startingDeadlineSeconds'] > 0
        pod = spec['jobTemplate']['spec']['template']['spec']
        container = pod['containers'][0]
        assert '@sha256:' in container['image']
        assert 'envFrom' not in container
        key_ref = next(e for e in container['env'] if e['name'] == 'LITELLM_API_KEY')['valueFrom']['secretKeyRef']
        assert key_ref['name'] == f"{cj['metadata']['name']}-litellm"
        assert pod['automountServiceAccountToken'] is False
