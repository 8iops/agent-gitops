"""Restricted projection of native migrate 1.0.3 evidence, never policy approval."""
import collections
import json
import os
from pathlib import Path
import re
import stat
import sys
import tomllib
import urllib.parse

MAX_BYTES = 1048576
PROMPTS = {'categories', 'changed_defaults', 'new_permissions', 'oauth_registration', 'oidc_directory', 'oidc_token_lifetimes'}
FIELDS = {
    'oidc_directory': {'issuerUrl', 'requireAudience', 'requireScopes'},
    'oauth_registration': {'anonymousClientRegistration', 'requireClientRegistration'},
    'oidc_token_lifetimes': {'authCodeExpiry', 'accessTokenExpiry', 'refreshTokenExpiry'},
}
SUMMARY = re.compile(r'Summary: (\d+) objects to write, (\d+) dropped, (\d+) warnings, (\d+) errors, (\d+) questions answered now\.')
TABLE = re.compile(r'# \[(global|instance)\.([a-z_]+)(?:\."([^"\\\r\n]{1,160})")?\]')
KEY = r'(?P<object>(?:x:)?[A-Za-z][A-Za-z0-9]*)(?:/[^\s:]{1,160})?'
ENTRY = re.compile(r'  (?P<level>info|warning|error): ' + KEY + r'(?: (?P<path>[^:\r\n]{1,256}))?: (?P<detail>.*)')

class Invalid(Exception): pass

def read(path):
    if any(p.is_symlink() for p in (path, *path.parents)): raise Invalid()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES: raise Invalid()
        raw = source.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES: raise Invalid()
    return raw.decode('utf-8')

def value(field, raw):
    v = json.loads(raw)
    if field in ('anonymousClientRegistration', 'requireClientRegistration'):
        if type(v) is not bool: raise Invalid()
    elif field.endswith('Expiry'):
        if type(v) is not int or not 0 <= v <= 315360000000: raise Invalid()
    elif field == 'issuerUrl':
        if not isinstance(v, str) or len(v) > 512: raise Invalid()
        u = urllib.parse.urlsplit(v)
        if (u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment
                or not re.fullmatch(r'[A-Za-z0-9.-]+', u.hostname)
                or not re.fullmatch(r'/[A-Za-z0-9_./~-]*|', u.path)): raise Invalid()
        if u.port not in (None, 443): raise Invalid()
    elif field == 'requireAudience':
        if v is not None and (not isinstance(v, str) or not re.fullmatch(r'[A-Za-z0-9:/_-]{0,128}', v)): raise Invalid()
    elif field == 'requireScopes':
        if not isinstance(v, dict) or len(v) > 32: raise Invalid()
        if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9:._/-]{0,100}', k) or type(b) is not bool for k, b in v.items()): raise Invalid()
    else: raise Invalid()
    return v

def change_code(detail):
    # Return fixed vocabulary only; never retain reasons, original values or IDs.
    for prefix, code in [('dropped (', 'dropped'), ('clamped ', 'clamped'),
                         ('unknown in the source schema, kept as is', 'unknown_source'),
                         ('counter_read:', 'counter_read'), ('webui_custom_bundle:', 'webui_custom_bundle')]:
        if detail.startswith(prefix): return code
    if detail.startswith('reference to ') and detail.endswith(' removed (target not migrated)'): return 'reference_cleared'
    if detail.startswith('reference to ') and detail.endswith(' removed (it is not in the same tenant, which v1 requires)'): return 'reference_outside_tenant'
    return None

def project(directory, vocabulary):
    answers = read(directory / 'answers.toml')
    if tomllib.loads(answers) != {'version': 1}: raise Invalid()
    pending = {}
    contexts = {}
    questions = []
    unknown_context = 0
    for line in answers.splitlines():
        if line.startswith('# Source '):
            if len(pending) >= 32: raise Invalid()
            label, separator, raw = line[len('# Source '):].partition(': ')
            if not separator or label in pending: raise Invalid()
            pending[label] = raw
        elif line.startswith('# ['):
            m = TABLE.fullmatch(line)
            if not m: raise Invalid()
            scope, prompt, key = m.groups()
            if prompt not in PROMPTS or (scope == 'instance') != (key is not None): raise Invalid()
            if (prompt, key) in questions or len(questions) >= 100: raise Invalid()
            questions.append((prompt, key))
            if prompt in FIELDS:
                output = {field: {'status': 'unknown'} for field in sorted(FIELDS[prompt])}
                for field, raw in pending.items():
                    if field in FIELDS[prompt]:
                        output[field] = {'status': 'observed', 'value': value(field, raw)}
                    elif not (prompt == 'oidc_directory' and field == 'claimName'):
                        unknown_context += 1
                contexts.setdefault(prompt, []).append(output)
            pending = {}
    if pending or collections.Counter(p for p, _ in questions) != {p: 1 for p in PROMPTS}: raise Invalid()
    report = read(directory / 'prepare-report.txt')
    if not report.startswith('stalwart-migrate prepare report\n'): raise Invalid()
    sections = report.split('\nChanges:\n')
    if len(sections) != 2: raise Invalid()
    header, changes = sections
    summaries = SUMMARY.findall(header)
    if len(summaries) != 1: raise Invalid()
    objects, drops, warnings, errors, answered = map(int, summaries[0])
    if (objects, drops, warnings, errors, answered) != (2927, 12, 63, 0, 0): raise Invalid()
    marker = 'run will refuse to start until these are resolved:\n'
    if header.count(marker) != 1 or 'settings objects are unreadable' in header: raise Invalid()
    problems = header.split(marker)[1].split('\nDropped objects:', 1)[0].strip().splitlines()
    expected = {f'{p}' + (f' for {k}' if k else '') + ': not answered' for p, k in questions}
    if {p.strip() for p in problems} != expected or len(problems) != len(expected): raise Invalid()
    types, properties = set(vocabulary['objectTypes']), set(vocabulary['properties'])
    drop_counts = collections.Counter()
    unknown_drops = 0
    dropped = header.split('\nDropped objects:\n')
    if len(dropped) != 2: raise Invalid()
    for line in dropped[1].splitlines():
        if not line: continue
        m = re.fullmatch('  ' + KEY, line)
        if not m or m['object'] not in types: unknown_drops += 1
        else: drop_counts[m['object']] += 1
    if sum(drop_counts.values()) + unknown_drops != drops: raise Invalid()
    warning_counts = collections.Counter()
    warning_seen = unknown_warnings = unknown_lines = 0
    for line in changes.splitlines():
        if not line: continue
        m = ENTRY.fullmatch(line)
        if not m:
            unknown_lines += 1
            continue
        if m['level'] == 'error': raise Invalid()
        if m['level'] != 'warning': continue
        warning_seen += 1
        # Only the schema property name, never map keys/IDs/array subscripts.
        prop = re.split(r'[.\[/]', m['path'] or '')[0]
        code = change_code(m['detail'])
        if m['object'] not in types or (prop and prop not in properties) or code is None:
            unknown_warnings += 1
            continue
        warning_counts[(m['object'], prop or '(object)', code)] += 1
    if warning_seen > warnings: raise Invalid()
    return {'schemaVersion': 1, 'policyApproved': False, 'migrationExecuted': False,
        'decisionStatus': 'blocked_pending_review', 'sourceCounts': {'objects': objects, 'dropped': drops, 'warnings': warnings},
        'contexts': contexts,
        'tokenType': {'status': 'unknown', 'reason': 'not_recorded_in_native_source_context'},
        'durationContext': 'only_values_below_v1_minimum_are_recorded',
        'droppedObjectTypes': dict(sorted(drop_counts.items())),
        'warningGroups': [{'objectType': k[0], 'property': k[1], 'changeCode': k[2], 'count': n} for k, n in sorted(warning_counts.items())],
        'unknown': {'contextFields': unknown_context, 'droppedObjects': unknown_drops,
                    'warningEntries': unknown_warnings + warnings - warning_seen, 'reportLines': unknown_lines}}

def main():
    try:
        vocab = json.loads(read(Path('/scripts/vocabulary.json')))
        output = project(Path('/state/prepare-discovery-v1/native'), vocab)
        print(json.dumps(output, sort_keys=True, separators=(',', ':')))
    except Exception:
        print('{"projection":"failed","reason":"evidence_not_classifiable","policyApproved":false}')
        return 1
    return 0

if __name__ == '__main__': sys.exit(main())
