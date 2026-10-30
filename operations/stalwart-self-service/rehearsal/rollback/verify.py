"""Fixed status for a private, isolated, full-verified rollback."""
import json
from pathlib import Path
import sys


def verify():
    stage = Path('/state/rollback-v1')
    target = Path('/var/lib/stalwart-rollback/database')
    marker = stage / 'native-exit'
    if not marker.is_file() or marker.stat().st_size > 8 or marker.read_text().strip() != '0':
        raise ValueError()
    if not (target / 'CURRENT').is_file() or not any(target.glob('MANIFEST-*')):
        raise ValueError()
    return {'rollbackComplete': True, 'rehearsalOnly': True,
            'fullVerificationRequested': True, 'rollbackTargetCreated': True,
            'rollbackServerStartupVerified': False, 'productionRollbackConfigured': False}


def main():
    try:
        print(json.dumps(verify(), sort_keys=True))
        return 0
    except Exception:
        print('{"rollbackComplete":false,"reason":"fixed_verification_failure"}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
