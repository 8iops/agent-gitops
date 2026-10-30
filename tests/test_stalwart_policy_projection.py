import importlib.util
import json
from pathlib import Path
import pytest
import yaml

BASE = Path(__file__).resolve().parents[1] / 'operations/stalwart-self-service/rehearsal/policy-projection'
spec = importlib.util.spec_from_file_location('policy_projection', BASE / 'project.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
VOCAB = json.loads((BASE / 'vocabulary.json').read_text())

def fixture(path):
    contexts = {
        'oidc_directory': {'issuerUrl': 'https://auth.example.test/auth/v1', 'requireAudience': 'authenticated', 'requireScopes': {'openid': True}, 'claimName': 'SENTINEL_SECRET'},
        'oauth_registration': {'requireClientRegistration': True, 'anonymousClientRegistration': False},
        'oidc_token_lifetimes': {'authCodeExpiry': 300000},
    }
    text = 'version = 1\n'
    problems = []
    for prompt in sorted(m.PROMPTS):
        if prompt in contexts:
            text += ''.join('# Source ' + k + ': ' + json.dumps(v) + '\n' for k,v in contexts[prompt].items())
            key = 'x:Directory/42' if prompt == 'oidc_directory' else 'x:OidcProvider'
            text += f'# [instance.{prompt}."{key}"]\n# secret="SENTINEL_SECRET"\n'
            problems.append(f'  {prompt} for {key}: not answered')
        else:
            text += f'# [global.{prompt}]\n'; problems.append(f'  {prompt}: not answered')
    (path/'answers.toml').write_text(text)
    report = 'stalwart-migrate prepare report\n\nSummary: 2927 objects to write, 12 dropped, 63 warnings, 0 errors, 0 questions answered now.\nrun will refuse to start until these are resolved:\n'+'\n'.join(problems)+'\n\nDropped objects:\n'+''.join(f'  x:OAuthClient/{i}\n' for i in range(12))+'\nChanges:\n'+('  warning: x:OidcProvider anonymousClientRegistration: dropped (no equivalent), was "SENTINEL_SECRET"\n'*63)
    (path/'prepare-report.txt').write_text(report)
    return path

def test_exact_context_and_counts_without_values_from_reports(tmp_path):
    result=m.project(fixture(tmp_path),VOCAB)
    assert result['contexts']['oidc_directory'][0]['requireAudience']['value']=='authenticated'
    assert result['contexts']['oidc_token_lifetimes'][0]['accessTokenExpiry']=={'status':'unknown'}
    assert result['warningGroups'][0]['count']==63
    assert result['droppedObjectTypes']=={'x:OAuthClient':12}
    assert result['tokenType']['status']=='unknown'
    assert result['policyApproved'] is False
    assert 'SENTINEL' not in json.dumps(result) and '/42' not in json.dumps(result)

@pytest.mark.parametrize('field,bad', [('issuerUrl','https://user:secret@example.test'),('issuerUrl','https://example.test/?secret=x'),('issuerUrl','http://example.test'),('requireAudience','a.b.c'),('requireScopes',{'secret': 'VALUE'}),('authCodeExpiry',True),('requireClientRegistration','secret')])
def test_context_shapes_reject_unexpected_values(field,bad):
    with pytest.raises(m.Invalid):m.value(field,json.dumps(bad))

def test_unknown_warning_and_drop_names_never_escape(tmp_path):
    fixture(tmp_path);p=tmp_path/'prepare-report.txt';p.write_text(p.read_text().replace('x:OAuthClient/0','x:SecretValue/0').replace('anonymousClientRegistration: dropped (no equivalent)', 'secretPath: arbitrary_change: secret'))
    out=m.project(tmp_path,VOCAB)
    assert out['unknown']['droppedObjects']==1 and out['unknown']['warningEntries']==63
    assert 'SecretValue' not in json.dumps(out) and 'secretPath' not in json.dumps(out)

def test_no_native_no_db_no_write_mount():
    j=yaml.safe_load((BASE/'job.yaml').read_text());p=j['spec']['template']['spec']
    assert j['spec']['suspend'] and p['automountServiceAccountToken'] is False
    assert 'initContainers' not in p and 'fsGroup' not in p['securityContext']
    assert len(p['volumes'])==2
    assert p['volumes'][0]['persistentVolumeClaim']['readOnly'] is True
    assert all(v['readOnly'] for v in p['containers'][0]['volumeMounts'])
