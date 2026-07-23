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


if __name__ == '__main__':
    unittest.main()
