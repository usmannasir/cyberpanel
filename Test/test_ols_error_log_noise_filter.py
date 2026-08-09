#!/usr/local/CyberCP/bin/python
# -*- coding: utf-8 -*-
"""Unit checks for OLS error-log noise filtering in Server Logs UI."""
from __future__ import print_function

import os
import sys
import unittest

sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')


class OlsErrorLogNoiseFilterTests(unittest.TestCase):
    def test_drops_content_encoding_warn(self):
        from serverLogs.views import _filter_ols_error_log_noise, _is_ols_content_encoding_noise
        noise = (
            '2026-07-31 19:15:19 [WARN] [CyberPanel-OLS] Restored Content-Encoding: gzip '
            'for compressed response body'
        )
        real = '2026-07-31 19:15:20 [ERROR] [STDERR] PHP Fatal error: test'
        self.assertTrue(_is_ols_content_encoding_noise(noise))
        self.assertFalse(_is_ols_content_encoding_noise(real))
        out = _filter_ols_error_log_noise(noise + '\n' + real, keep_lines=50)
        self.assertNotIn('Restored Content-Encoding', out)
        self.assertIn('PHP Fatal error', out)

    def test_keeps_last_n_after_filter(self):
        from serverLogs.views import _filter_ols_error_log_noise
        lines = []
        for i in range(10):
            lines.append(
                '[WARN] [CyberPanel-OLS] Restored Content-Encoding: gzip for compressed response body'
            )
            lines.append('[NOTICE] real line %s' % i)
        out = _filter_ols_error_log_noise('\n'.join(lines), keep_lines=5)
        kept = [l for l in out.splitlines() if l]
        self.assertEqual(len(kept), 5)
        self.assertTrue(all('real line' in l for l in kept))
        self.assertEqual(kept[-1], '[NOTICE] real line 9')


if __name__ == '__main__':
    unittest.main()
