"""Version-pinned native prepare evidence filter; never print source text."""
import json
import os
from pathlib import Path
import re
import stat
import sys
import tomllib

MAX_BYTES = 1024 * 1024
MAX_QUESTIONS = 100
PROMPTS = frozenset('blob_store categories oidc_directory oidc_token_lifetimes oauth_registration counter_read http_forwarded spam_ai ai_model_provider dns_sig0 azure_auth in_memory_cluster enterprise_on_oss new_permissions changed_defaults'.split())
SUMMARY = re.compile(r'Summary: (\d+) objects to write, (\d+) dropped, (\d+) warnings, (\d+) errors, (\d+) questions answered now\.')
TABLE = re.compile(r'# \[(global|instance)\.([a-z_]+)(?:\."([^"\\\r\n]{1,160})")?\]')

class Invalid(Exception):
    pass

def read_bounded(path):
    # No symlink/file-type surprises, even on the read-only state mount.
    for parent in path.parents:
        if parent.is_symlink():
            raise Invalid()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise Invalid()
        data = source.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise Invalid()
    return data.decode('utf-8')

def project(stage):
    code = read_bounded(stage / 'native-exit').strip()
    if code not in ('0', '1'):
        raise Invalid()
    answers = read_bounded(stage / 'native/answers.toml')
    # This discovery uses an empty state: no actual answers may be present.
    if tomllib.loads(answers) != {'version': 1}:
        raise Invalid()
    questions = []
    for line in answers.splitlines():
        if not line.startswith('# ['):
            continue
        match = TABLE.fullmatch(line)
        if not match:
            raise Invalid()
        scope, prompt, key = match.groups()
        if prompt not in PROMPTS or (scope == 'instance') != (key is not None):
            raise Invalid()
        # Keys are compared internally and NEVER emitted. Context/default lines
        # can contain secrets and are ignored, never parsed as approved answers.
        questions.append((prompt, key))
    if not questions or len(questions) > MAX_QUESTIONS or len(set(questions)) != len(questions):
        raise Invalid()
    report = read_bounded(stage / 'native/prepare-report.txt')
    if not report.startswith('stalwart-migrate prepare report\n'):
        raise Invalid()
    parts = report.split('\nChanges:\n')
    if len(parts) != 2:
        raise Invalid()
    header = parts[0]
    summaries = SUMMARY.findall(header)
    if len(summaries) != 1:
        raise Invalid()
    objects, dropped, warnings, errors, answered = map(int, summaries[0])
    if errors or answered or objects == 0 or any(v > 1000000 for v in (objects, dropped, warnings)):
        raise Invalid()
    marker = 'run will refuse to start until these are resolved:\n'
    if header.count(marker) != 1 or 'settings objects are unreadable' in header:
        raise Invalid()
    # The complete problems block must contain ONLY the exact missing answers.
    # Reject aborts, invalid fields and native conversion errors, not just exit 1.
    problems = header.split(marker, 1)[1].split('\nDropped objects:', 1)[0].strip().splitlines()
    expected = {f'  {p}' + (f' for {k}' if k else '') + ': not answered' for p, k in questions}
    # strip above removes indentation of first line; normalize only indentation.
    if {line.strip() for line in problems} != {line.strip() for line in expected} or len(problems) != len(expected) or code != '1':
        raise Invalid()
    counts = {p: sum(prompt == p for prompt, _ in questions) for p in sorted({p for p, _ in questions})}
    return {'schemaVersion': 1, 'discovery': 'questions_pending', 'migrationExecuted': False,
            'nativeExit': 1, 'objectsToConvert': objects, 'droppedCount': dropped,
            'warningCount': warnings, 'questionCount': len(questions), 'promptCounts': counts,
            'policyApproved': False, 'configurationProjectionComplete': False}

def main():
    try:
        result = project(Path('/state/prepare-discovery-v1'))
    except Exception:
        # Do not interpolate exceptions: parsers/paths can include secret input.
        print('{"discovery":"failed","reason":"evidence_not_classifiable"}')
        return 1
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return 0

if __name__ == '__main__':
    sys.exit(main())
