#!/usr/local/CyberCP/bin/python
# -*- coding: utf-8 -*-
"""Unit tests for plogical.sieveGuard (no live Dovecot required)."""
from __future__ import print_function

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from plogical import sieveGuard


class SieveGuardStripTests(unittest.TestCase):
    def test_strip_sieve_and_managesieve_tokens(self):
        conf = (
            "protocols = imap pop3 sieve managesieve\n"
            "protocol lda {\n"
            "  mail_plugins = zlib sieve\n"
            "}\n"
            "ssl = yes\n"
        )
        path = None
        try:
            fd, path = tempfile.mkstemp(prefix='dovecot-sieve-', suffix='.conf')
            os.close(fd)
            with open(path, 'w') as fh:
                fh.write(conf)
            changed = sieveGuard.strip_sieve_from_dovecot_conf(conf_path=path, writer=None)
            self.assertTrue(changed)
            with open(path, 'r') as fh:
                out = fh.read()
            self.assertIn('protocols = imap pop3', out)
            self.assertNotIn('sieve', out.split('protocols', 1)[1].split('\n', 1)[0])
            self.assertIn('mail_plugins = zlib', out)
            self.assertIn('ssl = yes', out)
        finally:
            if path and os.path.exists(path):
                os.unlink(path)

    def test_no_change_when_sieve_absent(self):
        conf = "protocols = imap pop3\nmail_plugins = zlib\n"
        path = None
        try:
            fd, path = tempfile.mkstemp(prefix='dovecot-nosieve-', suffix='.conf')
            os.close(fd)
            with open(path, 'w') as fh:
                fh.write(conf)
            changed = sieveGuard.strip_sieve_from_dovecot_conf(conf_path=path, writer=None)
            self.assertFalse(changed)
            with open(path, 'r') as fh:
                self.assertEqual(fh.read(), conf)
        finally:
            if path and os.path.exists(path):
                os.unlink(path)


if __name__ == '__main__':
    unittest.main()
