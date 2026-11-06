import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

try:
    from install.check_release_delivery import IncompleteRelease, verify
except ModuleNotFoundError:
    from check_release_delivery import IncompleteRelease, verify


class DeliveryGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.artifact = Path(temporary.name) / 'acceptance-evidence'
        self.artifact.write_bytes(b'acceptance evidence')
        artifact_hash = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.plan = {'schema': 1, 'tree': 'a' * 40,
                     'refs': {'stable': 'b' * 40, 'v3.0.8': 'c' * 40},
                     'files': {'plogical/upgrade.py': hashlib.sha256(b'fixed').hexdigest()},
                     'artifacts': {'https://cyberpanel.net/test-release.sh': hashlib.sha256(b'wrapper').hexdigest()},
                     'environments': ['ubuntu22', 'alma9']}
        self.receipts = []
        for environment in self.plan['environments']:
            case = {'ref': 'stable', 'source_commit': 'b' * 40,
                    'source_tree': 'a' * 40, 'success': True,
                    'preservation_passed': True, 'evidence_sha256': artifact_hash,
                    'evidence_file': str(self.artifact)}
            self.receipts.append({'environment': environment, 'tls_verified': True,
                                 'private_source_fixtures_removed': True,
                                 'cli': dict(case, official_bootstrap=True),
                                 'gui': dict(case, terminal_success=True, refresh_success=True,
                                             runtime_before='123:456', runtime_after='789:900',
                                             version_page_commit='b' * 40, browser_verified=True,
                                             screenshot_sha256=artifact_hash,
                                             screenshot_file=str(self.artifact))})

    def check(self, **kwargs):
        return verify(self.plan, self.receipts,
                      head=kwargs.get('head', lambda ref: self.plan['refs'][ref]),
                      fetch=kwargs.get('fetch', lambda ref, path: b'fixed'),
                      artifact_fetch=kwargs.get('artifact_fetch', lambda url: b'wrapper'))

    def test_candidate_passes_cannot_hide_old_public_heads(self):
        with self.assertRaisesRegex(IncompleteRelease, 'Public ref still differs'):
            self.check(head=lambda ref: '0' * 40)

    def test_raw_public_files_must_match_even_when_refs_match(self):
        with self.assertRaisesRegex(IncompleteRelease, 'Official public source differs'):
            self.check(fetch=lambda ref, path: b'old source')

    def test_recovery_artifact_must_be_delivered_as_well_as_source(self):
        with self.assertRaisesRegex(IncompleteRelease, 'release artifact differs'):
            self.check(artifact_fetch=lambda url: b'old wrapper')

    def test_artifact_dependencies_cannot_be_silently_omitted(self):
        del self.plan['artifacts']
        with self.assertRaisesRegex(IncompleteRelease, 'Declare external release artifacts'):
            self.check()

    def test_artifact_urls_require_the_official_tls_origin(self):
        for url in ('http://cyberpanel.net/test-release.sh', 'https://private.example/test-release.sh'):
            with self.subTest(url=url):
                self.plan['artifacts'] = {url: hashlib.sha256(b'wrapper').hexdigest()}
                with self.assertRaisesRegex(IncompleteRelease, 'Invalid public artifact URL'):
                    self.check()

    def test_both_required_os_receipts_are_required(self):
        self.receipts.pop()
        with self.assertRaisesRegex(IncompleteRelease, 'OS acceptance'):
            self.check()

    def test_private_source_maps_cannot_count_as_public_delivery(self):
        self.receipts[0]['private_source_fixtures_removed'] = False
        with self.assertRaisesRegex(IncompleteRelease, 'Private source fixtures'):
            self.check()

    def test_evidence_must_exist_and_match_its_digest(self):
        self.artifact.write_bytes(b'changed evidence')
        with self.assertRaisesRegex(IncompleteRelease, 'artifact is missing or changed'):
            self.check()

    def test_disk_update_cannot_count_as_runtime_activation(self):
        self.receipts[0]['gui']['runtime_after'] = '123:456'
        with self.assertRaisesRegex(IncompleteRelease, 'runtime was not activated'):
            self.check()

    def test_failed_or_missing_acceptance_fails_closed(self):
        original = copy.deepcopy(self.receipts)
        for mode, field in [('cli', 'official_bootstrap'), ('cli', 'success'),
                            ('gui', 'preservation_passed'), ('gui', 'refresh_success'),
                            ('gui', 'terminal_success'), ('gui', 'browser_verified')]:
            with self.subTest(mode=mode, field=field):
                self.receipts = copy.deepcopy(original)
                self.receipts[0][mode][field] = False
                with self.assertRaises(IncompleteRelease):
                    self.check()

    def test_concurrent_public_ref_change_invalidates_result(self):
        calls = []
        def head(ref):
            calls.append(ref)
            return self.plan['refs'][ref] if len(calls) <= 2 else '0' * 40
        with self.assertRaisesRegex(IncompleteRelease, 'moved during verification'):
            self.check(head=head)

    def test_delivered_state_does_not_establish_customer_resolution(self):
        result = self.check()
        self.assertEqual(result['state'], 'public_delivery_verified')
        self.assertEqual(result['customer_confirmation'], 'not established by this gate')


if __name__ == '__main__':
    unittest.main()
