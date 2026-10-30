import importlib.util
import json
from pathlib import Path
import sys
import yaml

BASE=Path(__file__).resolve().parents[1]/'operations/stalwart-self-service/rehearsal'
sys.path.insert(0,str(BASE/'policy-diagnostic'))
spec=importlib.util.spec_from_file_location('policy_diagnostic',BASE/'policy-diagnostic/diagnose.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_only_shapes_escape_invalid_context(tmp_path):
    (tmp_path/'answers.toml').write_text('version=1\n# Source requireScopes: null\n# Source issuerUrl: "http://SENTINEL_SECRET"\n# [instance.oidc_directory."x:Directory/SENTINEL_SECRET"]\n')
    (tmp_path/'prepare-report.txt').write_text('SENTINEL_SECRET\n')
    out=m.diagnose(tmp_path,{})
    assert out['reason']=='original_validator_rejected'
    byfield={f['field']:f for f in out['contextFields']}
    assert byfield['requireScopes']['type']=='null'
    assert byfield['requireScopes']['strictValidatorAccepted'] is False
    assert byfield['issuerUrl']['type']=='string'
    assert 'SENTINEL_SECRET' not in json.dumps(out)
    assert out['policyApproved'] is False

def test_types_never_include_keys_values_or_numeric_values():
    for raw in ['{"SECRET":"VALUE"}', '"SENSITIVE"','123456789','true','[]','null','INVALID_SECRET']:
        out=json.dumps(m.shape(raw))
        assert all(v not in out for v in ['SECRET','VALUE','SENSITIVE','123456789','INVALID'])

def test_missing_input_fixed_failure(tmp_path):
    assert m.diagnose(tmp_path,{})['reason']=='bounded_read_failed'

def test_exact_original_validation_and_readonly_boundary():
    for name in ['project.py','vocabulary.json']:
        assert (BASE/'policy-diagnostic'/name).read_bytes()==(BASE/'policy-projection'/name).read_bytes()
    j=yaml.safe_load((BASE/'policy-diagnostic/job.yaml').read_text());p=j['spec']['template']['spec']
    assert j['metadata']['name']=='stalwart-rehearsal-policy-diagnostic-v1'
    assert 'initContainers' not in p and 'fsGroup' not in p['securityContext']
    assert len(p['volumes'])==2 and p['volumes'][0]['persistentVolumeClaim']['readOnly']
    assert all(v['readOnly'] for v in p['containers'][0]['volumeMounts'])


def test_configmap_symlink_allowed_only_for_public_vocabulary(tmp_path):
    revision=tmp_path/'..2026';revision.mkdir()
    (revision/'vocabulary.json').write_text('{"objectTypes":[],"properties":[]}')
    (tmp_path/'..data').symlink_to(revision,target_is_directory=True)
    projected=tmp_path/'vocabulary.json';projected.symlink_to('..data/vocabulary.json')
    assert m.original.read_vocabulary(projected)=={'objectTypes':[],'properties':[]}
    import pytest
    with pytest.raises(m.original.Invalid):m.original.read(projected)
