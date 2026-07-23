#!/usr/bin/env python3
"""Tests for OLS vhost <-> CyberPanel phpSelection sync helpers."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')

import django
django.setup()

from plogical.phpUtilities import phpUtilities


class PHPSelectionFromVhostTests(unittest.TestCase):
    def test_ols_lsphp85_maps_to_php_85(self):
        with tempfile.NamedTemporaryFile('w', suffix='.conf', delete=False) as fh:
            fh.write('extprocessor example {\n'
                     '  path                    /usr/local/lsws/lsphp85/bin/lsphp\n'
                     '}\n')
            path = fh.name
        try:
            self.assertEqual(
                phpUtilities.GetPHPSelectionFromVhostFile(path),
                'PHP 8.5')
        finally:
            os.unlink(path)

    def test_ols_lsphp83_maps_to_php_83(self):
        with tempfile.NamedTemporaryFile('w', suffix='.conf', delete=False) as fh:
            fh.write('path /usr/local/lsws/lsphp83/bin/lsphp\n')
            path = fh.name
        try:
            self.assertEqual(
                phpUtilities.GetPHPSelectionFromVhostFile(path),
                'PHP 8.3')
        finally:
            os.unlink(path)

    def test_missing_file_returns_empty(self):
        self.assertEqual(
            phpUtilities.GetPHPSelectionFromVhostFile('/tmp/no-such-vhost.conf'),
            '')

    def test_live_newstargeted_vhost(self):
        vh = '/usr/local/lsws/conf/vhosts/newstargeted.com/vhost.conf'
        if not os.path.exists(vh):
            self.skipTest('newstargeted.com vhost missing on this host')
        label = phpUtilities.GetPHPSelectionFromVhostFile(vh)
        self.assertTrue(label.startswith('PHP '), label)

    def test_full_version_from_live_lsphp(self):
        vh = '/usr/local/lsws/conf/vhosts/newstargeted.com/vhost.conf'
        phpBin = '/usr/local/lsws/lsphp85/bin/php'
        if not os.path.exists(vh) or not os.path.exists(phpBin):
            self.skipTest('lsphp85 or newstargeted.com vhost missing')
        full = phpUtilities.GetFullPHPVersionFromVhostFile(vh)
        self.assertRegex(full, r'^PHP \d+\.\d+\.\d+', full)
        # Second call should hit cache and still return the same shape
        full2 = phpUtilities.GetFullPHPVersionFromVhostFile(vh)
        self.assertEqual(full, full2)

    def test_full_version_falls_back_to_selection(self):
        with tempfile.NamedTemporaryFile('w', suffix='.conf', delete=False) as fh:
            fh.write('path /usr/local/lsws/lsphp99/bin/lsphp\n')
            path = fh.name
        try:
            # lsphp99 binary unlikely; should fall back to selector label
            self.assertEqual(
                phpUtilities.GetFullPHPVersionFromVhostFile(path),
                'PHP 9.9')
        finally:
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()
