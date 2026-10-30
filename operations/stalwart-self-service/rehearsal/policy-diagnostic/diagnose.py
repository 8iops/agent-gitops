"""Shape-only diagnosis; never print input values, keys, paths or raw lines."""
import collections
import json
from pathlib import Path
import sys
import tomllib
import project as original


def shape(raw):
    try:
        v = json.loads(raw)
    except Exception:
        return {'jsonValid': False}
    kind = {type(None): 'null', bool: 'boolean', int: 'integer', float: 'number', str: 'string', list: 'array', dict: 'object'}[type(v)]
    result = {'jsonValid': True, 'type': kind, 'isNull': v is None}
    if isinstance(v, (str, list, dict)):
        result['length'] = len(v)
    if isinstance(v, dict):
        result['allValuesBoolean'] = all(type(x) is bool for x in v.values())
    return result


def diagnose(directory, vocabulary):
    result = {'diagnostic': 'shape_only', 'policyApproved': False, 'migrationExecuted': False}
    try:
        answers = original.read(directory / 'answers.toml')
        report = original.read(directory / 'prepare-report.txt')
    except Exception:
        return {**result, 'stage': 'input', 'reason': 'bounded_read_failed'}
    try:
        document = tomllib.loads(answers)
        result['answersUnapproved'] = document == {'version': 1}
    except Exception:
        return {**result, 'stage': 'answers', 'reason': 'toml_invalid'}
    pending = {}
    fields = []
    counts = collections.Counter()
    malformed = unknown = duplicate = 0
    for line in answers.splitlines():
        if line.startswith('# Source '):
            label, sep, raw = line[9:].partition(': ')
            if not sep or len(pending) >= 32:
                return {**result, 'stage': 'context', 'reason': 'source_context_shape_invalid'}
            if label in pending: duplicate += 1
            pending[label] = raw
        elif line.startswith('# ['):
            match = original.TABLE.fullmatch(line)
            if not match:
                malformed += 1
                pending = {}
                continue
            scope, prompt, key = match.groups()
            if prompt not in original.PROMPTS:
                unknown += 1
                pending = {}
                continue
            counts[prompt] += 1
            for field in sorted(original.FIELDS.get(prompt, set())):
                entry = {'prompt': prompt, 'field': field, 'present': field in pending}
                if field in pending:
                    entry.update(shape(pending[field]))
                    try:
                        original.value(field, pending[field])
                        entry['strictValidatorAccepted'] = True
                    except Exception:
                        entry['strictValidatorAccepted'] = False
                fields.append(entry)
            pending = {}
        if len(fields) > 100 or sum(counts.values()) > 100:
            return {**result, 'stage': 'context', 'reason': 'context_limit_exceeded'}
    result.update(contextFields=fields, promptCounts=dict(sorted(counts.items())),
                  malformedTableCount=malformed, unknownTableCount=unknown, duplicateContextCount=duplicate,
                  trailingContextPresent=bool(pending))
    sections = report.split('\nChanges:\n')
    summary = original.SUMMARY.findall(sections[0])
    report_shape = {'headerMatched': report.startswith('stalwart-migrate prepare report\n'),
                    'changesSectionCount': len(sections)-1, 'summaryMatchCount': len(summary),
                    'expectedSummaryMatched': len(summary)==1 and tuple(map(int,summary[0]))==(2927,12,63,0,0),
                    'problemsMarkerCount': sections[0].count('run will refuse to start until these are resolved:\n'),
                    'dropSectionCount': sections[0].count('\nDropped objects:\n')}
    if len(sections)==2:
        lines = [line for line in sections[1].splitlines() if line]
        report_shape['changeLineCount'] = len(lines)
        report_shape['entryPatternMatches'] = sum(original.ENTRY.fullmatch(line) is not None for line in lines)
    result['reportShape'] = report_shape
    try:
        original.project(directory, vocabulary)
        result.update(stage='complete', reason='original_validator_accepted')
    except Exception:
        result.update(stage='original_validation', reason='original_validator_rejected')
    return result


def main():
    try:
        vocabulary = original.read_vocabulary()
        result = diagnose(Path('/state/prepare-discovery-v1/native'), vocabulary)
        print(json.dumps(result, sort_keys=True, separators=(',', ':')))
        return 0
    except Exception:
        print('{"diagnostic":"failed","stage":"internal","reason":"diagnosis_unavailable","policyApproved":false}')
        return 1

if __name__ == '__main__': sys.exit(main())
