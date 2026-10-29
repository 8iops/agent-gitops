from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_test_route_keeps_oauth_and_private_sandbox_boundary():
    docs = list(yaml.safe_load_all((ROOT/'clusters/re8ch/compocv-cube-test.yaml').read_text()))
    assert all(d['metadata']['namespace'] == 'cube-trial' for d in docs)
    assert not any(d['kind'] in ('Ingress', 'HTTPRoute', 'Secret', 'PersistentVolumeClaim') for d in docs)
    config = next(d['data'] for d in docs if d['kind'] == 'ConfigMap')
    assert '49983' not in str(config)
    assert 'PENDING' not in str(config)
    for area in ('client_body', 'proxy', 'fastcgi', 'uwsgi', 'scgi'):
        assert f'{area}_temp_path /tmp/' in config['nginx.conf']
    assert 'include /run/cube-access/proxy-traffic.conf;' in config['test-upstream.conf']
    for header in ('Cookie', 'X-Forwarded-Access-Token', 'X-Auth-Request-Access-Token'):
        assert f'proxy_set_header {header} "";' in config['test-upstream.conf']
    assert 'proxy_hide_header Set-Cookie;' in config['test-upstream.conf']
    assert 'proxy_set_header Authorization $http_authorization;' in config['nginx.conf']
    deployment = next(d for d in docs if d['kind'] == 'Deployment')
    pod = deployment['spec']['template']['spec']
    assert not pod['automountServiceAccountToken']
    assert pod['securityContext']['runAsNonRoot']
    assert pod['volumes'][1]['secret']['items'] == [{'key': 'proxy-traffic.conf', 'path': 'proxy-traffic.conf'}]
    policy = next(d for d in docs if d['kind'] == 'NetworkPolicy')
    assert policy['spec']['ingress'][0]['from'] == [{'podSelector': {'matchLabels': {'app.kubernetes.io/name': 'oauth2-proxy-cube'}}}]
    runtime = list(yaml.safe_load_all((ROOT/'clusters/re8ch/resources.yaml').read_text()))
    oauth = next(d for d in runtime if d and d['kind'] == 'Deployment' and d['metadata']['name'] == 'oauth2-proxy-cube')
    args = oauth['spec']['template']['spec']['containers'][0]['args']
    assert '--upstream=http://cube-compocv-router:8080' in args
    for flag in ('pass-access-token', 'pass-authorization-header', 'pass-basic-auth', 'pass-user-headers'):
        assert f'--{flag}=false' in args
    assert not any(a.startswith('--skip-auth-route') for a in args)


def test_cube_dns_uses_existing_public_authority():
    docs = list(yaml.safe_load_all((ROOT/'clusters/re8ch/resources.yaml').read_text()))
    record = next(d for d in docs if d and d['kind'] == 'Ingress' and d['metadata']['name'] == 'cube-dns-authority')
    assert record['spec']['ingressClassName'] == 'external-dns-only'
    assert record['metadata']['labels']['networking.re8ch.com/dns-authority'] == 'public-edge'
    assert record['metadata']['annotations']['external-dns.alpha.kubernetes.io/hostname'] == 'cube.re8ch.com'
    assert record['metadata']['annotations']['external-dns.alpha.kubernetes.io/target'] == '223.159.210.222'
