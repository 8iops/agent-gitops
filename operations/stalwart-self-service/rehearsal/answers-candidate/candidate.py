"""Write a rehearsal-only answer candidate from validated private prepare state."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tomllib

from project import project, read, read_vocabulary, TABLE

SOURCE = Path('/state/prepare-discovery-v1/native')
DESTINATION = Path('/state/answers-candidate-v1')
EXPECTED = {
    'categories': None,
    'changed_defaults': None,
    'new_permissions': None,
    'oauth_registration': 'x:OidcProvider',
    'oidc_directory': 'x:Directory/',
    'oidc_token_lifetimes': 'x:OidcProvider',
}
CATEGORIES = ('settings', 'principals', 'mail', 'calendars', 'contacts', 'files',
              'sieve', 'identities', 'push_subscriptions', 'spam_samples',
              'reports', 'archive', 'spam_model', 'queue', 'tasks', 'telemetry')


def candidate():
    evidence = project(SOURCE, read_vocabulary())
    assert evidence['unknown'] == {'contextFields': 0, 'droppedObjects': 0,
                                    'warningEntries': 0, 'reportLines': 0}
    assert evidence['sourceCounts'] == {'objects': 2927, 'dropped': 12, 'warnings': 63}
    assert evidence['droppedObjectTypes'] == {'x:SpamTag': 12}
    warnings = {(x['objectType'], x['property'], x['changeCode']): x['count']
                for x in evidence['warningGroups']}
    assert warnings[('x:Role', 'enabledPermissions', 'dropped')] == 43
    assert evidence['contexts']['oauth_registration'] == [{
        'anonymousClientRegistration': {'status': 'observed', 'value': True},
        'requireClientRegistration': {'status': 'observed', 'value': True}}]
    assert evidence['contexts']['oidc_directory'] == [{
        'issuerUrl': {'status': 'observed', 'value': 'https://db-rw.re8ch.com/auth/v1'},
        'requireAudience': {'status': 'observed', 'value': 'authenticated'},
        'requireScopes': {'status': 'observed', 'value':
                          {'email': True, 'openid': True, 'profile': True}}}]
    assert evidence['contexts']['oidc_token_lifetimes'] == [{
        'accessTokenExpiry': {'status': 'unknown'},
        'authCodeExpiry': {'status': 'unknown'},
        'refreshTokenExpiry': {'status': 'observed', 'value': 28800000}}]

    original = read(SOURCE / 'answers.toml')
    assert tomllib.loads(original) == {'version': 1}
    keys = {}
    for line in original.splitlines():
        match = TABLE.fullmatch(line)
        if match:
            scope, prompt, key = match.groups()
            assert prompt in EXPECTED and prompt not in keys
            assert (scope == 'global') == (EXPECTED[prompt] is None)
            if EXPECTED[prompt] is None:
                assert key is None
            else:
                assert key is not None and key.startswith(EXPECTED[prompt])
            if key is not None:
                assert re.fullmatch(r'x:(?:OidcProvider|Directory/[A-Za-z0-9_-]{1,128})', key)
            keys[prompt] = key
    assert set(keys) == set(EXPECTED)

    categories = ', '.join(json.dumps(v) for v in CATEGORIES)
    # Values are fixed policy. Instance keys are copied only from the validated
    # private source; no object identifier is printed or stored in Git.
    answer = f'''version = 1

[global.categories]
include = [{categories}]

[global.changed_defaults]
policy = "pin"

[global.new_permissions]
action = "none"

[instance.oauth_registration."{keys['oauth_registration']}"]
action = "accept"

[instance.oidc_directory."{keys['oidc_directory']}"]
accepted_audiences = ["authenticated"]
skip_audience_validation = false
opaque_token_validation = "userInfo"
unscoped_tokens = "interoperable"
allow_id_token_claims = false
lenient_issuer_match = false
allow_invalid_certs = false
claim_name = "name"

[instance.oidc_token_lifetimes."{keys['oidc_token_lifetimes']}"]
action = "clamp"
'''
    parsed = tomllib.loads(answer)
    assert parsed['version'] == 1 and len(parsed['global']) == 3 and len(parsed['instance']) == 3
    return answer.encode()


def main():
    try:
        content = candidate()
        DESTINATION.mkdir(mode=0o700)
        fd = os.open(DESTINATION / 'answers.toml', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as target:
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        print(json.dumps({'candidateWritten': True, 'rehearsalOnly': True,
                          'answerSha256': hashlib.sha256(content).hexdigest(),
                          'prompts': 6, 'rolePermissionDrops': 43, 'spamTagDrops': 12},
                         sort_keys=True))
        return 0
    except Exception:
        print('{"candidateWritten":false,"reason":"fixed_evidence_or_write_failure"}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
