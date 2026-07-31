#!/usr/local/CyberCP/bin/python
# -*- coding: utf-8 -*-
"""Unit checks for SPF deployment-type helpers (no live DNS writes)."""
from __future__ import print_function

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')


class BuildSpfRecordTests(unittest.TestCase):
    def setUp(self):
        from plogical.dnsUtilities import DNS
        self.DNS = DNS
        self._orig_file = DNS.DEPLOYMENT_TYPE_FILE

    def tearDown(self):
        self.DNS.DEPLOYMENT_TYPE_FILE = self._orig_file

    def test_default_selfhosted_uses_ip(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
            path = tf.name
        try:
            os.unlink(path)
        except OSError:
            pass
        self.DNS.DEPLOYMENT_TYPE_FILE = path
        with mock.patch.object(self.DNS, 'getDeploymentType', return_value='selfhosted'):
            spf = self.DNS.buildSpfRecord('203.0.113.10')
        self.assertEqual(spf, 'v=spf1 a mx ip4:203.0.113.10 ~all')

    def test_cyberpersons_include(self):
        with mock.patch.object(self.DNS, 'getDeploymentType', return_value='cyberpersons'):
            spf = self.DNS.buildSpfRecord('203.0.113.10')
        self.assertEqual(spf, 'v=spf1 include:spf.cyberpersons.com ~all')

    def test_get_deployment_type_from_file(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        try:
            with open(path, 'w') as fh:
                fh.write('cyberpersons\n')
            self.DNS.DEPLOYMENT_TYPE_FILE = path
            self.assertEqual(self.DNS.getDeploymentType(), 'cyberpersons')
            with open(path, 'w') as fh:
                fh.write('selfhosted\n')
            self.assertEqual(self.DNS.getDeploymentType(), 'selfhosted')
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_get_deployment_type_default(self):
        missing = '/tmp/cyberpanel-deployment-type-missing-%s' % os.getpid()
        self.DNS.DEPLOYMENT_TYPE_FILE = missing
        with mock.patch('loginSystem.models.Administrator') as Admin:
            Admin.objects.get.side_effect = Exception('no admin')
            self.assertEqual(self.DNS.getDeploymentType(), 'selfhosted')


if __name__ == '__main__':
    unittest.main()
