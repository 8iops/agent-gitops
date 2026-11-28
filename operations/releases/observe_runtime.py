"""Read-only health observation, independent of the SSA execution result."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path

import yaml
from ssa_executor import Executor, load_archive
from unified_bundle import canonical, digest


WORKLOAD_KINDS = {'Deployment', 'StatefulSet', 'DaemonSet'}
FATAL_WAITING_REASONS = {
    'CrashLoopBackOff', 'CreateContainerConfigError', 'CreateContainerError',
    'ErrImagePull', 'ImagePullBackOff', 'InvalidImageName', 'RunContainerError',
}


def _container_status(container):
    return {
        'name': container.get('name'),
        'ready': container.get('ready', False),
        'restartCount': container.get('restartCount', 0),
        'state': {
            state: {key: data.get(key) for key in ('reason', 'exitCode') if key in data}
            for state, data in container.get('state', {}).items()
        },
    }


def workload_rollout(executor, objects):
    """Return sanitized rollout evidence for workloads declared by the bundle."""
    workloads = []
    for item in objects:
        if item.get('kind') not in WORKLOAD_KINDS:
            continue
        metadata = item.get('metadata', {})
        name = metadata.get('name')
        namespace = metadata.get('namespace')
        evidence = {'kind': item['kind'], 'name': name, 'namespace': namespace}
        try:
            argv = ['kubectl', '--request-timeout=8s', 'get', item['kind'].lower(), name]
            if namespace:
                argv += ['--namespace', namespace]
            argv += ['-o', 'json']
            live = json.loads(executor.command(argv, timeout=12).stdout)
            status = live.get('status', {})
            spec = live.get('spec', {})
            evidence['generation'] = live.get('metadata', {}).get('generation', 0)
            evidence['observedGeneration'] = status.get('observedGeneration', 0)
            evidence['replicas'] = {
                key: status.get(key, 0) for key in (
                    'replicas', 'updatedReplicas', 'readyReplicas', 'availableReplicas',
                    'unavailableReplicas', 'desiredNumberScheduled', 'updatedNumberScheduled',
                    'numberReady', 'numberAvailable', 'numberUnavailable')
                if key in status
            }
            evidence['conditions'] = [
                {key: condition.get(key) for key in ('type', 'status', 'reason')}
                for condition in status.get('conditions', [])
            ]
            labels = spec.get('selector', {}).get('matchLabels', {})
            if labels:
                selector = ','.join(f'{key}={labels[key]}' for key in sorted(labels))
                try:
                    pod_argv = ['kubectl', '--request-timeout=8s', 'get', 'pods']
                    if namespace:
                        pod_argv += ['--namespace', namespace]
                    pod_argv += ['--selector', selector, '-o', 'json']
                    pods = json.loads(executor.command(pod_argv, timeout=12).stdout)
                    evidence['pods'] = [{
                        'name': pod.get('metadata', {}).get('name'),
                        'phase': pod.get('status', {}).get('phase'),
                        'terminating': bool(pod.get('metadata', {}).get('deletionTimestamp')),
                        'conditions': [
                            {key: condition.get(key) for key in ('type', 'status', 'reason')}
                            for condition in pod.get('status', {}).get('conditions', [])
                        ],
                        'containers': [
                            _container_status(container) for container in (
                                pod.get('status', {}).get('initContainerStatuses', []) +
                                pod.get('status', {}).get('containerStatuses', []))
                        ],
                    } for pod in pods.get('items', [])]
                except Exception as error:
                    # Readiness is still enforced from the controller counters.
                    # Pod evidence is additive because exact release identities
                    # may intentionally lack namespace-wide Pod list access.
                    evidence['podObservation'] = {
                        'observation': 'not-authorized-or-unavailable',
                        'errorType': type(error).__name__,
                    }
        except Exception as error:
            evidence['observation'] = 'not-authorized-or-unavailable'
            evidence['errorType'] = type(error).__name__
        workloads.append(evidence)

    namespaces = sorted({item.get('namespace') for item in workloads if item.get('namespace')})
    for namespace in namespaces:
        try:
            value = json.loads(executor.command([
                'kubectl', '--request-timeout=8s', 'get', 'events', '--namespace', namespace,
                '-o', 'json'], timeout=12).stdout)
            names = {item['name'] for item in workloads if item.get('namespace') == namespace}
            pod_names = {
                pod.get('name') for item in workloads if item.get('namespace') == namespace
                for pod in item.get('pods', [])
            }
            events = [{
                'type': event.get('type'),
                'reason': event.get('reason'),
                'involvedObject': {
                    key: event.get('involvedObject', {}).get(key) for key in ('kind', 'name')
                },
                'count': event.get('count', 0),
            } for event in value.get('items', [])
                if event.get('involvedObject', {}).get('name') in names | pod_names]
            for item in workloads:
                if item.get('namespace') == namespace:
                    item['events'] = events
        except Exception as error:
            for item in workloads:
                if item.get('namespace') == namespace:
                    item['events'] = {
                        'observation': 'not-authorized-or-unavailable',
                        'errorType': type(error).__name__,
                    }
    return {'workloads': workloads}


def rollout_health(rollout):
    failures = []
    for workload in rollout.get('workloads', []):
        identity = f"{workload.get('kind')}/{workload.get('namespace')}/{workload.get('name')}"
        if workload.get('observation'):
            failures.append(f'{identity}: rollout observation unavailable')
            continue
        active = [pod for pod in workload.get('pods', []) if not pod.get('terminating')]
        for pod in active:
            for container in pod.get('containers', []):
                waiting = container.get('state', {}).get('waiting', {})
                if waiting.get('reason') in FATAL_WAITING_REASONS:
                    failures.append(
                        f"{identity}: {pod.get('name')}/{container.get('name')} "
                        f"waiting {waiting['reason']}")
                elif not container.get('ready'):
                    failures.append(
                        f"{identity}: {pod.get('name')}/{container.get('name')} not ready")
    if failures:
        return False, '; '.join(failures)[:512]
    return True, 'workload pods ready without fatal waiting states'


def observe(root, contract=None, require_healthy=False):
    operation_path = root / 'operation.json'
    bundle = root / 'pulled/release.bundle'
    if not operation_path.exists() or not bundle.exists():
        return None
    operation = json.loads(operation_path.read_text())
    observation = {'releaseId': operation['releaseId'], 'digest': operation['bundle']['digest'],
                   'observedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
                   'health': {'status': 'unknown', 'reason': 'Runtime observation unavailable'}}
    try:
        if digest(bundle.read_bytes()) != operation['bundle']['payloadDigest']:
            raise ValueError('bundle mismatch')
        _, objects = load_archive(bundle)
        contracts = Path(__file__).resolve().parents[2] / 'contracts'
        contract = contract or next(v for p in contracts.rglob('*.yaml')
                        if isinstance(v := yaml.safe_load(p.read_text()), dict)
                        and v.get('metadata', {}).get('name') == operation['releaseId']
                        and digest(canonical(v)) == operation['contractDigest'])
        if os.environ.get('ACTIONS_ID_TOKEN_REQUEST_URL'):
            os.environ.setdefault('EXECUTOR_AUDIENCE', operation['github']['audience'])
        executor = Executor()
        timeout = contract['spec']['lifecycle']['healthTimeoutSeconds'] if require_healthy else 0
        healthy, reason = executor.wait_healthy(
            objects, timeout, contract['spec']['lifecycle'].get('healthChecks'))
        observation['rollout'] = workload_rollout(executor, objects)
        rollout_ready, rollout_reason = rollout_health(observation['rollout'])
        if healthy and not rollout_ready:
            healthy, reason = False, rollout_reason
        observation['health'] = {'status': 'healthy' if healthy else 'degraded', 'reason': reason}
    except Exception as error:
        # Never expose command input, decrypted values or raw API error bodies.
        observation['health'] = {'status': 'unknown', 'reason': 'Runtime observation unavailable (' + type(error).__name__ + ')'}
    (root / 'observation.json').write_text(json.dumps(observation, sort_keys=True) + '\n')
    for path in (root / 'result.json', Path('static-release-result.json')):
        if path.exists() and path.stat().st_size:
            result = json.loads(path.read_text())
            if (result.get('releaseId', result.get('release')) == operation['releaseId']
                    and result.get('outcome') in {'applied', 'healthy', 'degraded', 'aligned', 'recovered'}):
                result['health'] = observation['health']
                path.write_text(json.dumps(result, sort_keys=True) + '\n')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as stream:
            stream.write('\nObserve: ' + operation['releaseId'] + ' · ' + observation['health']['status'] + '\n\n' + observation['health']['reason'] + '\n')
    if observation['health']['status'] != 'healthy':
        print('::warning::Runtime observation is ' + observation['health']['status'] + '; SSA execution status is independent. See observation artifact.')
    return observation


def observation_exit_code(observation, require_healthy):
    if not require_healthy:
        return 0
    return 0 if observation and observation['health']['status'] == 'healthy' else 1


def main(argv=None, root=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-healthy', action='store_true')
    args = parser.parse_args(argv)
    observed = observe(
        root or Path(os.environ['RUNNER_TEMP']), require_healthy=args.require_healthy)
    return observation_exit_code(observed, args.require_healthy)


if __name__ == '__main__':
    raise SystemExit(main())
