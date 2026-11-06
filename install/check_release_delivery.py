"""Fail closed before calling a source fix delivered. Does not resolve tickets.

Run after publication and public-path QA, with the sealed release plan and
per-environment acceptance receipts. Output is evidence, never authorization.
"""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.request import urlopen
from urllib.parse import urlsplit

REPOSITORY = 'https://github.com/usmannasir/cyberpanel.git'
RAW = 'https://raw.githubusercontent.com/usmannasir/cyberpanel'


class IncompleteRelease(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise IncompleteRelease(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify_artifact(path, expected, label):
    require(re.fullmatch(r'[0-9a-f]{64}', expected) is not None,
            'Missing evidence digest: ' + label)
    require(Path(path).is_file() and digest(Path(path).read_bytes()) == expected,
            'Evidence artifact is missing or changed: ' + label)


def public_head(ref):
    name = 'refs/heads/' + ref
    result = subprocess.run(['git', 'ls-remote', '--exit-code', REPOSITORY, name],
                            check=True, stdout=subprocess.PIPE,
                            universal_newlines=True, timeout=45)
    match = re.fullmatch(r'([0-9a-f]{40})\s+' + re.escape(name), result.stdout.strip())
    require(match, 'Could not identify official public ref: ' + ref)
    return match.group(1)


def public_file(ref, path):
    return public_artifact('%s/%s/%s' % (RAW, ref, path), maximum=4 * 1024 * 1024)


def public_artifact(url, maximum=128 * 1024 * 1024):
    with urlopen(url, timeout=45) as response:
        require(response.status == 200, 'Public source download was not HTTP 200')
        data = response.read(maximum + 1)
    require(len(data) <= maximum, 'Public download exceeded expected size')
    return data


def validate_acceptance(plan, receipt):
    require(receipt['environment'] in plan['environments'], 'Unexpected QA environment')
    require(receipt['private_source_fixtures_removed'] is True,
            'Private source fixtures remain; public delivery is unproved')
    require(receipt['tls_verified'] is True, 'QA did not use verified TLS')
    for mode in ('cli', 'gui'):
        case = receipt[mode]
        ref = case['ref']
        require(ref in plan['refs'], 'QA used an unpublished ref')
        require(case['source_commit'] == plan['refs'][ref], 'QA used a different commit')
        require(case['source_tree'] == plan['tree'], 'QA used a different source tree')
        require(case['success'] is True and case['preservation_passed'] is True,
                'Upgrade or preservation acceptance failed: ' + mode)
        verify_artifact(case['evidence_file'], case['evidence_sha256'], mode)
    require(receipt['cli']['official_bootstrap'] is True,
            'CLI acceptance did not use the official bootstrap')
    gui = receipt['gui']
    require(gui['terminal_success'] is True and gui['refresh_success'] is True,
            'GUI completion and refreshed session are not verified')
    require(gui['runtime_before'] and gui['runtime_after'] and
            gui['runtime_before'] != gui['runtime_after'],
            'Updated panel runtime was not activated')
    require(gui['version_page_commit'] == gui['source_commit'],
            'Refreshed version page did not identify the delivered source')
    require(gui['browser_verified'] is True and
            re.fullmatch(r'[0-9a-f]{64}', gui['screenshot_sha256']) is not None,
            'Actual browser acceptance is missing')
    verify_artifact(gui['screenshot_file'], gui['screenshot_sha256'], 'browser screenshot')


def verify(plan, receipts, head=public_head, fetch=public_file, artifact_fetch=public_artifact):
    require(plan['schema'] == 1, 'Unsupported release plan schema')
    require(re.fullmatch(r'[0-9a-f]{40}', plan['tree']) is not None, 'Invalid sealed tree')
    require(plan['refs'] and plan['files'] and plan['environments'], 'Incomplete release plan')
    require('artifacts' in plan and isinstance(plan['artifacts'], dict),
            'Declare external release artifacts explicitly, including an empty mapping if none')
    require(len(set(plan['environments'])) == len(plan['environments']), 'Duplicate environments')
    for ref, revision in plan['refs'].items():
        require(re.fullmatch(r'stable|v[0-9]+(?:\.[0-9]+)+', ref) is not None, 'Invalid release ref')
        require(re.fullmatch(r'[0-9a-f]{40}', revision) is not None, 'Invalid published commit')
        require(head(ref) == revision, 'Public ref still differs from tested release: ' + ref)
    results = {}
    for path, expected in sorted(plan['files'].items()):
        parts = PurePosixPath(path)
        require(not parts.is_absolute() and '..' not in parts.parts and str(parts) == path,
                'Invalid sealed source path')
        require(re.fullmatch(r'[0-9a-f]{64}', expected) is not None, 'Invalid sealed source digest')
        for ref in plan['refs']:
            actual = digest(fetch(ref, path))
            require(actual == expected, 'Official public source differs: %s/%s' % (ref, path))
            results[ref + '/' + path] = actual
    artifacts = {}
    for url, expected in sorted(plan['artifacts'].items()):
        parts = urlsplit(url)
        require(parts.scheme == 'https' and parts.netloc == 'cyberpanel.net' and
                not parts.query and not parts.fragment, 'Invalid public artifact URL')
        require(re.fullmatch(r'[0-9a-f]{64}', expected) is not None, 'Invalid public artifact digest')
        actual = digest(artifact_fetch(url))
        require(actual == expected, 'Official release artifact differs: ' + url)
        artifacts[url] = actual
    observed = []
    for receipt in receipts:
        validate_acceptance(plan, receipt)
        observed.append(receipt['environment'])
    require(sorted(observed) == sorted(plan['environments']),
            'Required OS acceptance is missing or duplicated')
    # Recheck after downloads and QA validation to catch a concurrent ref change.
    for ref, revision in plan['refs'].items():
        require(head(ref) == revision, 'Public ref moved during verification: ' + ref)
    return {'state': 'public_delivery_verified', 'verified_utc': datetime.now(timezone.utc).isoformat(),
            'tree': plan['tree'], 'refs': plan['refs'], 'public_file_hashes': results,
            'public_artifact_hashes': artifacts,
            'environments': observed, 'customer_confirmation': 'not established by this gate'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--acceptance', required=True, nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text())
        receipts = [json.loads(path.read_text()) for path in args.acceptance]
        result = verify(plan, receipts)
        result['plan_sha256'] = digest(args.plan.read_bytes())
        result['acceptance_sha256'] = {str(path): digest(path.read_bytes()) for path in args.acceptance}
        code = 0
    except Exception as error:
        result = {'state': 'incomplete', 'reason': str(error),
                  'verified_utc': datetime.now(timezone.utc).isoformat()}
        code = 1
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'state': result['state'], 'output': str(args.output)}))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
