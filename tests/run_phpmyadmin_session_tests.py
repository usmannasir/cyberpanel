"""Run the shipped vendor authentication path only with private fixture data."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PHP = sys.argv[1] if len(sys.argv) > 1 else 'php'
cases = ['valid', 'repeat', 'legacy', 'missing_panel', 'rotated_panel', 'revoked',
         'malformed_grant', 'bad_db_port', 'transport_failure', 'transport_exception', 'http_failure',
         'redirect', 'invalid_json', 'non_integer_status', 'missing_curl', 'invalid_ip']
receipts = []
with tempfile.TemporaryDirectory(prefix='pma-auth-fixture-') as directory:
    root = Path(directory)
    vendor_hashes = {'AuthenticationPlugin.php': '4c9456b2df4681251dbfcfe1d95670031ccb3fc2a9a64f6420ecc6327c7881b0',
                     'AuthenticationSignon.php': '4930ca9e147cca4282921cc1e0789db47495d7fccd09da1a381502031cf06599'}
    if os.environ.get('PMA_TEST_VENDOR_DIR'):
        for name, expected in vendor_hashes.items():
            data = (Path(os.environ['PMA_TEST_VENDOR_DIR']) / name).read_bytes()
            assert hashlib.sha256(data).hexdigest() == expected, 'Unexpected vendor fixture'
            (root / name).write_bytes(data)
    else:
        with zipfile.ZipFile(ROOT / 'phpmyadmin.zip') as archive:
            for name in ('libraries/classes/Plugins/AuthenticationPlugin.php',
                         'libraries/classes/Plugins/Auth/AuthenticationSignon.php'):
                data = archive.read('phpMyAdmin-5.2.1-all-languages/' + name)
                assert hashlib.sha256(data).hexdigest() == vendor_hashes[Path(name).name]
                (root / Path(name).name).write_bytes(data)
    for mode, selected in [('baseline', ['valid', 'missing_panel', 'revoked', 'legacy']), ('candidate', cases)]:
        for case in selected:
            sessions = root / (mode + '-' + case)
            sessions.mkdir(mode=0o700)
            result = subprocess.run([PHP, '-n', str(ROOT / 'tests/test_phpmyadmin_session_auth.php'),
                                     mode, case, str(root), str(sessions)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=15)
            expected_failure = mode == 'baseline' and case != 'valid'
            passed = (result.returncode != 0 and ('database access expectation: ' + case) in (result.stdout + result.stderr)) if expected_failure else result.returncode == 0
            receipts.append({'mode': mode, 'case': case, 'returncode': result.returncode,
                             'expected_baseline_failure': expected_failure, 'passed': passed,
                             'stdout': result.stdout, 'stderr': result.stderr})
print(json.dumps({'receipts': receipts, 'all_expected_outcomes': all(x['passed'] for x in receipts),
                  'vendor_class_sha256': vendor_hashes}, indent=2))
raise SystemExit(0 if all(x['passed'] for x in receipts) else 1)
