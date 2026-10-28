"""One-shot, cluster-only provisioning of two exact recovery Secrets.

No credential values are accepted from arguments or emitted in diagnostics.
An empty seed is supplied by reviewed platform bootstrap. Existing credentials
are retained; optimistic concurrency prevents two Jobs from rotating passwords.
"""
import base64
import json
import secrets
import ssl
from pathlib import Path
from urllib.request import Request, urlopen

NAMESPACE = 'cube-trial'
BASE = 'cube-recovery-secret'
MASTER = 'cube-recovery-master-config'
KEYS = ('mysql-root-password', 'mysql-password', 'redis-password', 'cube-admin-token')
MARKERS = dict(zip(KEYS, ('__CUBE_MYSQL_ROOT_PASSWORD__', '__CUBE_MYSQL_PASSWORD__', '__CUBE_REDIS_PASSWORD__', '__CUBE_ADMIN_TOKEN__')))


def credential_data(existing):
    data = existing.get('data') or {}
    if not data:
        values = {key: secrets.token_hex(32) for key in KEYS}
        values['redis-auth.conf'] = 'requirepass ' + values['redis-password'] + '\n'
        return {key: base64.b64encode(value.encode()).decode() for key, value in values.items()}
    values = {key: base64.b64decode(data[key], validate=True).decode() for key in KEYS}
    if any(len(value) != 64 or any(c not in '0123456789abcdef' for c in value) for value in values.values()):
        raise ValueError('existing credential format rejected')
    if base64.b64decode(data['redis-auth.conf']).decode() != 'requirepass ' + values['redis-password'] + '\n':
        raise ValueError('existing Redis configuration rejected')
    return data


def master_data(template, data):
    for key, marker in MARKERS.items():
        template = template.replace(marker, base64.b64decode(data[key]).decode())
    if '__CUBE_' in template:
        raise ValueError('unresolved credential marker')
    return {'conf.yaml': base64.b64encode(template.encode()).decode()}


def main():
    service_account = Path('/var/run/secrets/kubernetes.io/serviceaccount')
    token = service_account.joinpath('token').read_text().strip()
    context = ssl.create_default_context(cafile=str(service_account / 'ca.crt'))

    def api(name, payload=None):
        if name not in (BASE, MASTER):
            raise ValueError('undeclared Secret')
        req = Request(f'https://kubernetes.default.svc/api/v1/namespaces/{NAMESPACE}/secrets/{name}',
                      data=json.dumps(payload).encode() if payload is not None else None,
                      method='PATCH' if payload is not None else 'GET',
                      headers={'Authorization': 'Bearer ' + token,
                               'Content-Type': 'application/merge-patch+json'})
        with urlopen(req, context=context, timeout=20) as response:
            return json.load(response)

    current = api(BASE)
    data = credential_data(current)
    if not current.get('data'):
        current = api(BASE, {'metadata': {'resourceVersion': current['metadata']['resourceVersion']}, 'data': data})
        data = credential_data(current)
    target = api(MASTER)
    config = master_data(Path('/templates/conf.yaml').read_text(), data)
    if target.get('data') != config:
        api(MASTER, {'metadata': {'resourceVersion': target['metadata']['resourceVersion']}, 'data': config})
    print('Cube recovery credential references ready; values suppressed.')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never emit HTTP response bodies, headers or rendered configuration.
        raise SystemExit('Cube credential provisioning failed; inspect Job metadata and scoped access.') from None
