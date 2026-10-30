"""Project only fixed numeric evidence from a private native verify run."""
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path('/state/answered-prepare-v1/full-verify-v1')
SUMMARY = re.compile(r'verify: (\d+) accounts checked, (\d+) mismatches, (\d+) not explained by earlier reports \([^\r\n]{1,60}\)')
MAX_BYTES = 1048576


def read(path):
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValueError()
        raw = source.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError()
    return raw.decode('utf-8')


def diagnose():
    exit_text = read(ROOT / 'native-exit')
    if not re.fullmatch(r'\d{1,3}\n?', exit_text):
        raise ValueError()
    exit_code = int(exit_text)
    if exit_code == 0 or exit_code > 255:
        raise ValueError()
    stdout = read(ROOT / 'stdout')
    # Do not inspect stderr contents: it may include credentials or object IDs.
    stderr_path = ROOT / 'stderr'
    if any(part.is_symlink() for part in (stderr_path, *stderr_path.parents)) or not stderr_path.is_file():
        raise ValueError()
    stderr_size = stderr_path.stat().st_size
    if stderr_size > MAX_BYTES:
        raise ValueError()
    matches = SUMMARY.findall(stdout)
    if len(matches) > 1:
        raise ValueError()
    result = {'schemaVersion': 1, 'rehearsalOnly': True,
              'nativeExitNonzero': True, 'nativeSummaryPresent': bool(matches),
              'stderrNonempty': stderr_size > 0,
              'fullVerificationAccepted': False}
    if matches:
        accounts, mismatches, unexplained = map(int, matches[0])
        if accounts > 10000000 or mismatches > 10000000 or unexplained > mismatches:
            raise ValueError()
        result['numericSummary'] = {'accountsChecked': accounts,
                                    'mismatches': mismatches, 'unexplained': unexplained}
    return result


def main():
    try:
        print(json.dumps(diagnose(), sort_keys=True))
        return 0
    except Exception:
        print('{"diagnostic":"failed","reason":"fixed_evidence_not_classifiable","fullVerificationAccepted":false}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
