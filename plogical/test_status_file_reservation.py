import json
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from plogical.statusUtilities import create_status_file
from plogical.test_child_domain_conversion import load_method


class StatusFileReservationTests(unittest.TestCase):
    def test_existing_success_and_symlink_are_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path(directory, '1000')
            old.write_text('Website successfully created. [200]')
            Path(directory, '1001').symlink_to(old)
            with patch('plogical.statusUtilities.secrets.randbits', side_effect=[1000, 1001, 1002]):
                path = Path(create_status_file(directory))
            self.assertEqual('1002', path.name)
            self.assertEqual('Starting..,0', path.read_text())
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
            self.assertEqual('Website successfully created. [200]', old.read_text())

    def test_conversion_reserves_pending_status_before_starting_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            reserved = []
            def start_worker(kind, args):
                self.assertEqual('convertDomainToSite', kind)
                path = Path(args['tempStatusPath'])
                self.assertEqual('Starting..,0', path.read_text())
                self.assertTrue(path.name.isdigit())
                reserved.append(path)
                return Mock()
            launch = load_method('websiteFunctions/website.py', 'WebsiteManager',
                                 'convertDomainToSite', dict(
                json=json, ApplicationInstaller=start_worker,
                HttpResponse=lambda content: SimpleNamespace(content=content.encode())))
            with patch('plogical.statusUtilities.create_status_file',
                       side_effect=lambda: create_status_file(directory)):
                first = json.loads(launch(None, request=Mock()).content)
                second = json.loads(launch(None, request=Mock()).content)
            self.assertNotEqual(first['tempStatusPath'], second['tempStatusPath'])
            self.assertEqual(2, len(reserved))
