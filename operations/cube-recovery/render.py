"""Compile the pinned upstream chart into existing release/seed boundaries.

Helm has no write-only random-credential provisioning primitive, and upstream
assumes fixed guest paths. This build-time adapter only splits its render,
fixes host/guest mappings and pins images; it is not a runtime controller.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NS = 'cube-trial'


def resource(kind, name, spec=None, api='v1'):
    result = {'apiVersion': api, 'kind': kind, 'metadata': {'name': name, 'namespace': NS}}
    if spec is not None:
        result['spec'] = spec
    return result


def compile_outputs():
    images = json.loads((HERE / 'images.lock.json').read_text())
    locks = {v['repository'] + ':' + v['tag']: v['repository'] + ':' + v['tag'] + '@' + v['digest'] for v in images.values()}
    def pin(value):
        if isinstance(value, dict): return {k: pin(v) for k, v in value.items()}
        if isinstance(value, list): return [pin(v) for v in value]
        if isinstance(value, str):
            for old, new in locks.items(): value = value.replace(old, new)
        return value
    rendered = subprocess.check_output(['helm', 'template', 'cube-recovery', str(HERE / 'vendor/chart'), '-n', NS, '-f', str(HERE / 'values.yaml'), '--skip-tests'], text=True)
    objects = [pin(d) for d in yaml.safe_load_all(rendered) if d]
    runtime, seed = [], []
    config = None
    fixed = {'data-cubelet': '/data/cubelet', 'data-log': '/data/log', 'data-cube-shim': '/data/cube-shim', 'data-snapshot-pack': '/data/snapshot_pack', 'data-cube-shared': '/data/cube-shared', 'data-shared': '/data/shared', 'tmp-cube': '/tmp/cube'}
    # Reuse the previously qualified route-aware startup commands, vendored as
    # non-secret patches. They only run inside the Cube Pod network namespace.
    patches = yaml.safe_load((HERE / 'node-patch.yaml').read_text())
    for obj in objects:
        obj['metadata'].setdefault('namespace', NS)
        kind = obj['kind']; name = obj['metadata']['name']
        if kind.startswith('Cluster'):
            obj['metadata'].pop('namespace', None)
        if kind == 'Secret':
            if name == 'cube-recovery-master-config': config = obj['stringData']['conf.yaml']
            if name not in ('cube-recovery-master-config', 'cube-recovery-secret'):
                raise ValueError('unexpected chart-generated Secret')
            seed.append(resource('Secret', name)); continue
        # Preserve CIDR preflight as a platform Job, not a replayed release hook.
        annotations = obj['metadata'].get('annotations', {})
        for key in list(annotations):
            if key.startswith('helm.sh/'): del annotations[key]
        if kind in ('Deployment', 'StatefulSet', 'DaemonSet', 'Job'):
            pod = obj['spec']['template']['spec']
            if name == 'cube-recovery-node':
                obj['spec']['updateStrategy'].pop('rollingUpdate', None)
                for container in pod['containers']:
                    for mount in container.get('volumeMounts', []):
                        if mount['name'] in fixed: mount['mountPath'] = fixed[mount['name']]
                    if container['name'] == 'cubelet':
                        container['resources'] = {'requests': {'cpu': '250m', 'memory': '512Mi'}, 'limits': {'cpu': '4', 'memory': '8Gi'}}
                    patch = patches.get(container['name'])
                    if patch:
                        for key, value in patch.items():
                            if key == 'env':
                                names = {v['name'] for v in value}
                                container[key] = [v for v in container.get(key, []) if v['name'] not in names] + value
                            else: container[key] = value
            for container in pod.get('containers', []) + pod.get('initContainers', []):
                if '@sha256:' not in container['image']: raise ValueError('mutable image')
                container.setdefault('resources', {'requests': {'cpu': '50m', 'memory': '64Mi'}, 'limits': {'cpu': '2', 'memory': '2Gi'}})
            if name.endswith('-node-installer'):
                pod['automountServiceAccountToken'] = False
        (seed if kind in ('ClusterRole','ClusterRoleBinding','Role','RoleBinding','Job','ServiceAccount','Certificate') else runtime).append(obj)
    assert config and '__CUBE_MYSQL_PASSWORD__' in config
    seed += [resource('Issuer', 'cube-recovery-selfsigned', {'selfSigned': {}}, 'cert-manager.io/v1')]
    template = resource('ConfigMap', 'cube-recovery-credential-template'); template['data'] = {'conf.yaml': config, 'provision.py': (HERE / 'provision_credentials.py').read_text()};seed.append(template)
    seed.append(resource('ServiceAccount', 'cube-recovery-credentials'))
    role = resource('Role','cube-recovery-credentials',api='rbac.authorization.k8s.io/v1');role['rules']=[{'apiGroups':[''],'resources':['secrets'],'resourceNames':['cube-recovery-secret','cube-recovery-master-config'],'verbs':['get','patch']}];seed.append(role)
    binding=resource('RoleBinding','cube-recovery-credentials',api='rbac.authorization.k8s.io/v1');binding.update(roleRef={'apiGroup':'rbac.authorization.k8s.io','kind':'Role','name':'cube-recovery-credentials'},subjects=[{'kind':'ServiceAccount','name':'cube-recovery-credentials','namespace':NS}]);seed.append(binding)
    seed.append(resource('Job','cube-recovery-credentials-v1',{'backoffLimit':2,'activeDeadlineSeconds':180,'template':{'spec':{'restartPolicy':'Never','serviceAccountName':'cube-recovery-credentials','nodeSelector':{'kubernetes.io/hostname':'r640'},'securityContext':{'runAsNonRoot':True,'runAsUser':65534,'seccompProfile':{'type':'RuntimeDefault'}},'containers':[{'name':'provision','image':locks['python:3.13-alpine'],'command':['python','-B','/templates/provision.py'],'securityContext':{'allowPrivilegeEscalation':False,'readOnlyRootFilesystem':True,'capabilities':{'drop':['ALL']}},'resources':{'requests':{'cpu':'10m','memory':'32Mi'},'limits':{'cpu':'200m','memory':'128Mi'}},'volumeMounts':[{'name':'template','mountPath':'/templates','readOnly':True}]}],'volumes':[{'name':'template','configMap':{'name':'cube-recovery-credential-template'}}]}}},'batch/v1'))
    # Native node discovery with mutation restricted to R640. No cluster-wide leases.
    cr={'apiVersion':'rbac.authorization.k8s.io/v1','kind':'ClusterRole','metadata':{'name':'cube-recovery-node'},'rules':[{'apiGroups':[''],'resources':['nodes'],'verbs':['get','list']},{'apiGroups':[''],'resources':['nodes'],'resourceNames':['r640'],'verbs':['patch','update']}]};seed.append(cr)
    seed.append({'apiVersion':'rbac.authorization.k8s.io/v1','kind':'ClusterRoleBinding','metadata':{'name':'cube-recovery-node'},'roleRef':{'apiGroup':'rbac.authorization.k8s.io','kind':'ClusterRole','name':'cube-recovery-node'},'subjects':[{'kind':'ServiceAccount','name':'cube-recovery-node','namespace':NS}]})
    role=resource('Role','cube-recovery-node',api='rbac.authorization.k8s.io/v1');role['rules']=[{'apiGroups':['coordination.k8s.io'],'resources':['leases'],'verbs':['get','list','create','update','patch']}];seed.append(role)
    binding=resource('RoleBinding','cube-recovery-node',api='rbac.authorization.k8s.io/v1');binding.update(roleRef={'apiGroup':'rbac.authorization.k8s.io','kind':'Role','name':'cube-recovery-node'},subjects=[{'kind':'ServiceAccount','name':'cube-recovery-node','namespace':NS}]);seed.append(binding)
    # Only same-namespace peers can reach the new unauthenticated control plane.
    runtime.append(resource('NetworkPolicy','cube-recovery-internal',{'podSelector':{'matchLabels':{'app.kubernetes.io/instance':'cube-recovery'}},'policyTypes':['Ingress'],'ingress':[{'from':[{'podSelector':{}}]}]},'networking.k8s.io/v1'))
    return {ROOT/'clusters/re8ch/cube-recovery-resources.yaml':yaml.safe_dump_all(runtime,sort_keys=False,explicit_start=True),HERE/'platform-seed.yaml':yaml.safe_dump_all(seed,sort_keys=False,explicit_start=True)}


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    for path, body in compile_outputs().items():
        if args.check:
            if not path.exists() or path.read_text()!=body:raise SystemExit('stale Cube recovery render: '+str(path.relative_to(ROOT)))
        else:path.write_text(body)
