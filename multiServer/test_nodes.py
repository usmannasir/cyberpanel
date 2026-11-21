import unittest
from types import SimpleNamespace
from unittest.mock import patch

from multiServer import testing

SKIP = testing.unavailable()


@unittest.skipIf(SKIP, SKIP)
class NodePresentationTests(unittest.TestCase):
    def test_older_or_damaged_values_have_safe_fallbacks(self):
        from multiServer import nodes
        row = SimpleNamespace(label='bad<row>', link_id='?', status='invalid', advertised='a,b<',
                              panel_version='bad version', last_seen_at=2**63, last_error='private data',
                              last_error_at=None)
        summary = nodes.summary(row)
        self.assertEqual(('Unnamed node', '', 'unknown', '', '', None, 'Unknown error'),
                         tuple(summary[k] for k in ('label', 'id', 'status', 'version', 'capabilities', 'seen', 'error')))
        row.advertised = ''
        self.assertEqual('', nodes.summary(row)['capabilities'])

    def test_incomplete_enrollment_and_link_sessions_do_not_grant_access(self):
        from multiServer import nodes
        request = SimpleNamespace(session=SimpleNamespace(session_key='local'), META={})
        admin = SimpleNamespace(twoFA=1, secretKey='None')
        with patch.object(nodes.views, 'full_administrator', return_value=admin):
            self.assertIsNone(nodes.administrator(request))
            import pyotp
            admin.secretKey = pyotp.random_base32()
            with patch.object(nodes.models.LinkSession.objects, 'filter') as sessions:
                sessions.return_value.exists.return_value = True
                self.assertIsNone(nodes.administrator(request))
                sessions.return_value.exists.return_value = False
                self.assertIs(admin, nodes.administrator(request))
