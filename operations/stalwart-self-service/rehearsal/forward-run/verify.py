"""Fixed, bounded status for the isolated non-final forward run."""
import json
from pathlib import Path
import sys


def verify():
    stage = Path('/state/answered-prepare-v1/forward-run-v1')
    exit_file = stage / 'native-exit'
    target = Path('/var/lib/stalwart-v1/database')
    if not exit_file.is_file() or exit_file.stat().st_size > 8:
        raise ValueError()
    if exit_file.read_text().strip() != '0':
        raise ValueError()
    if not (target / 'CURRENT').is_file():
        raise ValueError()
    if not any(target.glob('MANIFEST-*')):
        raise ValueError()
    return {'forwardRunComplete': True, 'rehearsalOnly': True,
            'nonFinal': True, 'targetCreated': True,
            'fullVerificationComplete': False, 'rollbackVerified': False}


def main():
    try:
        print(json.dumps(verify(), sort_keys=True))
        return 0
    except Exception:
        print('{"forwardRunComplete":false,"reason":"fixed_verification_failure"}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
