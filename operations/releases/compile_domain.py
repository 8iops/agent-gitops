#!/usr/bin/env python3
"""Compile bounded namespace releases using service-backend's existing SSA format.

No runtime planner: checked-in contracts and exact RBAC are deterministic outputs.
Secrets, encrypted data, Helm and unsupported scopes remain explicit migration work.
"""
import argparse
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path
import yaml
from operation_materialize import state_configmap_name
from restricted_configmap import bind_source, validate_envelope, RestrictedConfigError
from profile import REPOSITORY, ENVIRONMENT, AUDIENCE, GROUP, SIGNER, WORKFLOW
from unified_bundle import canonical, digest, compile_bundle, object_identity
ROOT = Path(__file__).resolve().parents[2]
DOMAIN = ENVIRONMENT.removeprefix('release-executor-')
PREFIX = ('observability' if DOMAIN == 'observability-metering' else DOMAIN) + '-domain-'
PLURALS = {'ServiceAccount':'serviceaccounts','Service':'services','ConfigMap':'configmaps','PersistentVolumeClaim':'persistentvolumeclaims','Deployment':'deployments','StatefulSet':'statefulsets','DaemonSet':'daemonsets','Job':'jobs','CronJob':'cronjobs','HorizontalPodAutoscaler':'horizontalpodautoscalers','PodDisruptionBudget':'poddisruptionbudgets','NetworkPolicy':'networkpolicies','Ingress':'ingresses','EndpointSlice':'endpointslices','HTTPRoute':'httproutes','CiliumNetworkPolicy':'ciliumnetworkpolicies','Role':'roles','RoleBinding':'rolebindings','MCPServer':'mcpservers','ResourceQuota':'resourcequotas'}
CUSTOM_TYPES = json.loads((ROOT/'operations/releases/resource-types.json').read_text())
FLUX_GROUPS = {'source.toolkit.fluxcd.io','helm.toolkit.fluxcd.io','kustomize.toolkit.fluxcd.io','notification.toolkit.fluxcd.io','image.toolkit.fluxcd.io'}

def group(item):
    return item['apiVersion'].split('/')[0] if '/' in item['apiVersion'] else 'core'

def contains_encrypted(value):
    if isinstance(value,dict): return 'sops' in value or any(contains_encrypted(v) for v in value.values())
    if isinstance(value,list): return any(contains_encrypted(v) for v in value)
    return isinstance(value,str) and 'ENC[AES256_GCM,' in value

def mutable_image(value):
    if isinstance(value,dict): return any((k=='image' and isinstance(v,str) and '@sha256:' not in v) or mutable_image(v) for k,v in value.items())
    if isinstance(value,list): return any(mutable_image(v) for v in value)
    return False

def release_name(namespace):
    name=PREFIX+namespace
    return name if len(name)<=63 else name[:52].rstrip('-')+'-'+hashlib.sha256(name.encode()).hexdigest()[:10]

def classify(item,reserved):
    ident=object_identity(item)
    if ident in reserved:return 'existing-release-contract'
    if group(item)=='rbac.authorization.k8s.io':return 'platform-owned-rbac'
    if item['kind']=='Job':return 'one-shot-job-platform-owned'
    if item['kind']=='Secret':return 'secret-provisioning'
    if contains_encrypted(item):
        try:validate_envelope(item)
        except RestrictedConfigError:return 'restricted-cloud-decryption'
    if group(item) in FLUX_GROUPS:return 'helm-render' if item['kind']=='HelmRelease' else 'retired-flux-control-resource'
    if not item['metadata'].get('namespace'):return 'cluster-scoped-bootstrap'
    if mutable_image(item):return 'image-digest-required'
    if item['kind'] not in PLURALS and group(item)+'/'+item['kind'] not in CUSTOM_TYPES:return 'custom-resource-access-required'
    return None

def rendered(path):
    return [d for d in yaml.safe_load_all(subprocess.check_output(['kubectl','kustomize',str(path)],cwd=ROOT,text=True)) if d]

def compile_outputs():
    transfers=json.loads((ROOT/'operations/releases/authority-transfers.json').read_text())
    for namespace, transfer in transfers.items():
        source=(ROOT/transfer['sourcePath']).resolve()
        if ROOT.resolve() not in source.parents or digest(source.read_bytes()) != transfer['sourceDigest']:
            raise ValueError('authority transfer source differs from accepted payload')
        if any(d['metadata'].get('namespace') != namespace for d in yaml.safe_load_all(source.read_text()) if d):
            raise ValueError('authority transfer crosses its reviewed namespace')
    reserved=set()
    for path in sorted((ROOT/'contracts').glob('*.yaml')):
        if path.stem.startswith(PREFIX):continue
        contract=yaml.safe_load(path.read_text()); source=contract['spec']['source']
        if source.get('path'):
            reserved.update(object_identity(d) for d in rendered(ROOT/source['path']))
    originals={object_identity(d):d for path in (ROOT/'clusters/re8ch').glob('*.yaml') for d in yaml.safe_load_all(path.read_text()) if isinstance(d,dict) and 'sops' in d}
    items=rendered(ROOT/'clusters/re8ch')
    items=[bind_source(d, originals[object_identity(d)]) if d.get('kind')=='ConfigMap' and 'sops' in d else d for d in items]
    by_namespace=defaultdict(list); deferred=[]; seen=set()
    for item in items:
        ident=object_identity(item)
        if ident in seen:raise ValueError('duplicate object: '+ident)
        seen.add(ident); reason=classify(item,reserved)
        if reason:deferred.append({'identity':ident,'reason':reason})
        else:by_namespace[item['metadata']['namespace']].append(item)
    files={}; access=[]; releases=[]
    for namespace,objects in sorted(by_namespace.items()):
        objects.sort(key=object_identity);name=release_name(namespace);package=ROOT/'releases'/name
        inventory=sorted(object_identity(d) for d in objects)
        contract={'apiVersion':'delivery.re8ch.com/v1alpha1','kind':'ReleaseContract','metadata':{'name':name},'spec':{
            'authorityDomain':DOMAIN,'target':{'cluster':'re8ch','namespace':namespace},
            'source':{'renderer':'kustomize','revision':'github-main-reviewed','repository':REPOSITORY,'path':'releases/'+name},
            'provenance':{'repository':REPOSITORY,'workflow':WORKFLOW,'ref':'refs/heads/main','environment':ENVIRONMENT,'audience':AUDIENCE,'signer':SIGNER,'issuer':'https://token.actions.githubusercontent.com'},
            'authorization':{'fieldManager':'re8ch-release/'+name,'resources':sorted({group(d)+'/'+d['kind'] for d in objects}),'objectNames':sorted({d['metadata']['name'] for d in objects}),'allowClusterScoped':False,'requireExisting':True,'forceConflictObjects':[object_identity(d) for d in objects if d['kind'] not in {'Namespace','CustomResourceDefinition','PersistentVolume','PersistentVolumeClaim','StorageClass'}]},
            'inventory':{'digest':digest(canonical(inventory))},
            'lifecycle':{'prune':False,'healthTimeoutSeconds':300,'protectedKinds':['Namespace','CustomResourceDefinition','PersistentVolume','PersistentVolumeClaim','StorageClass'],'deletionAllowlist':[]}}}
        body=yaml.safe_dump_all(objects,sort_keys=False,explicit_start=True)
        if namespace in transfers:
            contract['spec']['authorization']['fieldManager']=transfers[namespace]['fieldManager']
            contract['spec']['authorization']['forceConflictObjects']=transfers[namespace].get('forceConflictObjects', [])
        compile_bundle(contract,body.encode()) # use the existing validator, never a weaker parallel format
        files[package/'resources.yaml']=body
        files[package/'kustomization.yaml']=yaml.safe_dump({'apiVersion':'kustomize.config.k8s.io/v1beta1','kind':'Kustomization','resources':['resources.yaml']},sort_keys=False)
        files[ROOT/'contracts'/f'{name}.yaml']=yaml.safe_dump(contract,sort_keys=False)
        state=state_configmap_name(name);rules=defaultdict(set)
        for d in objects:rules[(group(d),PLURALS.get(d['kind']) or CUSTOM_TYPES[group(d)+'/'+d['kind']])].add(d['metadata']['name'])
        rules[('core','configmaps')].add(state)
        role_rules=[]
        for (api,resource),names in sorted(rules.items()):
            verbs=['get','patch','update']
            role_rules.append({'apiGroups':['' if api=='core' else api],'resources':[resource],'resourceNames':sorted(names),'verbs':verbs})
        access += [{'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':state,'namespace':namespace,'labels':{'delivery.re8ch.com/state':'accepted','delivery.re8ch.com/authority-domain':DOMAIN}}},
          {'apiVersion':'rbac.authorization.k8s.io/v1','kind':'Role','metadata':{'name':name,'namespace':namespace},'rules':role_rules},
          {'apiVersion':'rbac.authorization.k8s.io/v1','kind':'RoleBinding','metadata':{'name':name,'namespace':namespace},'roleRef':{'apiGroup':'rbac.authorization.k8s.io','kind':'Role','name':name},'subjects':[{'apiGroup':'rbac.authorization.k8s.io','kind':'Group','name':GROUP}]}]
        releases.append({'name':name,'namespace':namespace,'objects':len(objects),'contract':'contracts/'+name+'.yaml'})
    files[ROOT/'operations/releases/domain-access.yaml']=yaml.safe_dump_all(access,sort_keys=False,explicit_start=True)
    files[ROOT/'operations/releases/domain-cohort.json']=json.dumps({'domain':DOMAIN,'sourceObjects':len(items),'releases':releases,'publishableObjects':sum(len(v) for v in by_namespace.values()),'deferred':sorted(deferred,key=lambda x:x['identity'])},indent=2)+'\n'
    return files

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    files=compile_outputs()
    expected=set(files)
    stale=[p for pattern in ['contracts/'+PREFIX+'*.yaml','releases/'+PREFIX+'*/*'] for p in ROOT.glob(pattern) if p not in expected]
    if args.check:
        stale += [p for p,s in files.items() if not p.exists() or p.read_text()!=s]
        if stale:raise SystemExit('regenerate domain cohort: '+', '.join(str(p.relative_to(ROOT)) for p in stale))
    else:
        for p in stale:p.unlink()
        for p,s in files.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
    print('validated deterministic domain cohort:',DOMAIN)
if __name__=='__main__':main()
