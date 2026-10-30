"""Bounded classification of the official answered prepare result."""
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path('/state/answered-prepare-v1')
CANDIDATE = Path('/state/answers-candidate-v1/answers.toml')
SUMMARY = re.compile(r'Summary: (\d+) objects to write, (\d+) dropped, (\d+) warnings, (\d+) errors, (\d+) questions answered now\.')


def read(path, limit=1048576):
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError()
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError()
    data = path.read_bytes()
    if len(data) > limit:
        raise ValueError()
    return data.decode('utf-8')


def verify():
    if read(ROOT / 'native-exit', 8).strip() != '0':
        raise ValueError()
    candidate = tomllib.loads(read(CANDIDATE, 4096))
    answered = tomllib.loads(read(ROOT / 'native/answers.toml'))
    if candidate != answered or set(answered) != {'version', 'global', 'instance'}:
        raise ValueError()
    report = read(ROOT / 'native/prepare-report.txt')
    if not report.startswith('stalwart-migrate prepare report\n'):
        raise ValueError()
    matches = SUMMARY.findall(report)
    if len(matches) != 1:
        raise ValueError()
    objects, drops, warnings, errors, questions = map(int, matches[0])
    if objects < 2927 or drops != 12 or warnings > 63 or errors != 0 or questions != 6:
        raise ValueError()
    if 'run will refuse to start until these are resolved:' in report:
        raise ValueError()
    return {'answeredPrepareComplete': True, 'rehearsalOnly': True,
            'objectsToWrite': objects, 'droppedObjects': drops,
            'warnings': warnings, 'questionsAnswered': questions}


def main():
    try:
        print(json.dumps(verify(), sort_keys=True))
        return 0
    except Exception:
        print('{"answeredPrepareComplete":false,"reason":"fixed_verification_failure"}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
