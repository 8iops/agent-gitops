"""Bounded retries for read-only SSA projections racing status updates."""
def retry_read_conflict(read_and_project):
    for attempt in range(3):
        try:
            return read_and_project()
        except RuntimeError as error:
            # Only optimistic resourceVersion races: never ownership conflicts,
            # admission denials, auth failures, timeouts or actual SSA writes.
            if attempt == 2 or 'the object has been modified' not in str(error):
                raise


def safe_failure_reason(error):
    message = str(error).lower()
    if 'the object has been modified' in message:
        return 'concurrent object update after bounded read-only retries'
    if 'conflict with' in message or 'field manager conflict' in message:
        return 'SSA field ownership conflict'
    if 'forbidden' in message or 'unauthorized' in message:
        return 'authorization denied'
    if 'timeout' in message or 'timed out' in message or 'deadline exceeded' in message or 'serviceunavailable' in message:
        return 'API transport or availability failure'
    return 'API request rejected; raw diagnostics withheld'


def transport_markers(error):
    """Return fixed diagnostic labels, never API bodies or command arguments."""
    message = str(error).lower()
    patterns = {
        'apiserver-deadline': 'the server was unable to return a response in the time allotted',
        'tls-handshake': 'tls handshake timeout',
        'io-deadline': 'i/o timeout',
        'context-deadline': 'context deadline exceeded',
        'gateway-deadline': 'gateway timeout',
        'connection-reset': 'connection reset',
        'connection-refused': 'connection refused',
        'unexpected-eof': 'unexpected eof',
        'service-unavailable': 'serviceunavailable',
        'openapi-fetch': 'failed to download openapi',
    }
    return [label for label, pattern in patterns.items() if pattern in message]


def configmap_owned_fields_match(desired, live, manager):
    """Prove an unchanged string-map object without uploading its data again.

    Unknown ownership shapes deliberately fall back to server projection.
    Exact owned paths also detect fields that SSA would remove on omission.
    """
    if desired.get('apiVersion') != 'v1' or desired.get('kind') != 'ConfigMap':
        return False
    if live.get('apiVersion') != 'v1' or live.get('kind') != 'ConfigMap':
        return False
    if set(desired) - {'apiVersion', 'kind', 'metadata', 'data', 'binaryData', 'immutable'}:
        return False
    meta = desired.get('metadata', {})
    actual = live.get('metadata', {})
    if any(meta.get(k) != actual.get(k) for k in ('name', 'namespace')):
        return False
    if set(meta) - {'name', 'namespace', 'resourceVersion', 'labels', 'annotations'}:
        return False
    expected = {}
    for root, values in ((('data',), desired.get('data', {})),
                         (('binaryData',), desired.get('binaryData', {})),
                         (('metadata', 'labels'), meta.get('labels', {})),
                         (('metadata', 'annotations'), meta.get('annotations', {}))):
        if not isinstance(values, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in values.items()):
            return False
        expected.update({root + (k,): v for k, v in values.items()})
    if 'immutable' in desired:
        if not isinstance(desired['immutable'], bool):
            return False
        expected[('immutable',)] = desired['immutable']
    entries = [entry for entry in actual.get('managedFields', [])
               if entry.get('manager') == manager and not entry.get('subresource')]
    if len(entries) != 1 or not expected:
        return False
    entry = entries[0]
    if entry.get('operation') != 'Apply' or entry.get('apiVersion') != 'v1' or entry.get('fieldsType') != 'FieldsV1':
        return False
    owned = set()
    def visit(tree, path=()):
        if not isinstance(tree, dict):
            raise ValueError('unknown ownership shape')
        if not tree:
            owned.add(path)
        for key, child in tree.items():
            if key == '.' and child == {}:
                continue
            if not key.startswith('f:'):
                raise ValueError('non-map ownership')
            visit(child, path + (key[2:],))
    try:
        visit(entry['fieldsV1'])
        if owned != set(expected):
            return False
        for path, value in expected.items():
            observed = live
            for key in path:
                observed = observed[key]
            if observed != value:
                return False
    except (KeyError, TypeError, ValueError):
        return False
    return True
