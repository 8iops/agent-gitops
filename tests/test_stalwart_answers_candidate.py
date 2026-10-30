import importlib.util
import json
from pathlib import Path
import sys
import tomllib

import pytest

from test_stalwart_policy_projection import m as projection

BASE = Path(__file__).resolve().parents[1] / 'operations/stalwart-self-service/rehearsal/answers-candidate'
sys.modules['project'] = projection
spec = importlib.util.spec_from_file_location('answers_candidate', BASE / 'candidate.py')
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


def evidence():
    return {
        'unknown': {'contextFields': 0, 'droppedObjects': 0,
                    'warningEntries': 0, 'reportLines': 0},
        'sourceCounts': {'objects': 2927, 'dropped': 12, 'warnings': 63},
        'droppedObjectTypes': {'x:SpamTag': 12},
        'warningGroups': [{'objectType': 'x:Role', 'property': 'enabledPermissions',
                           'changeCode': 'dropped', 'count': 43}],
        'contexts': {
            'oauth_registration': [{
                'anonymousClientRegistration': {'status': 'observed', 'value': True},
                'requireClientRegistration': {'status': 'observed', 'value': True}}],
            'oidc_directory': [{
                'issuerUrl': {'status': 'observed', 'value': 'https://db-rw.re8ch.com/auth/v1'},
                'requireAudience': {'status': 'observed', 'value': 'authenticated'},
                'requireScopes': {'status': 'observed', 'value':
                                  {'email': True, 'openid': True, 'profile': True}}}],
            'oidc_token_lifetimes': [{
                'accessTokenExpiry': {'status': 'unknown'},
                'authCodeExpiry': {'status': 'unknown'},
                'refreshTokenExpiry': {'status': 'observed', 'value': 28800000}}],
        },
    }


def source():
    return '''version = 1
# [global.categories]
# [global.changed_defaults]
# [global.new_permissions]
# [instance.oauth_registration."x:OidcProvider"]
# [instance.oidc_directory."x:Directory/42"]
# secret = "SENTINEL_SECRET"
# [instance.oidc_token_lifetimes."x:OidcProvider"]
'''


def test_candidate_uses_fixed_policy_and_private_instance_key(monkeypatch):
    monkeypatch.setattr(candidate, 'project', lambda *_: evidence())
    monkeypatch.setattr(candidate, 'read_vocabulary', lambda: {})
    monkeypatch.setattr(candidate, 'read', lambda *_: source())
    output = candidate.candidate().decode()
    parsed = tomllib.loads(output)
    assert parsed['global']['new_permissions']['action'] == 'none'
    assert parsed['global']['categories']['include'] == list(candidate.CATEGORIES)
    assert parsed['instance']['oidc_directory']['x:Directory/42']['unscoped_tokens'] == 'interoperable'
    assert 'SENTINEL_SECRET' not in output


def test_changed_role_or_drop_count_fails_closed(monkeypatch):
    bad = evidence()
    bad['warningGroups'][0]['count'] = 42
    monkeypatch.setattr(candidate, 'project', lambda *_: bad)
    monkeypatch.setattr(candidate, 'read_vocabulary', lambda: {})
    with pytest.raises(AssertionError):
        candidate.candidate()
