import copy
import unittest

from databases.phpmyadmin_session import GRANT_KEY, issue_grant, panel_ip_allowed, validate_grant


class Session(dict):
    session_key = 'originalpanelsessionkey'
    modified = False


class PhpMyAdminSessionTests(unittest.TestCase):
    def setUp(self):
        self.session = Session(userID=7, ipAddr='203.0.113.10')
        self.grant = issue_grant(self.session, 7, 'database-user', 'authorization-token', False)
        self.session.modified = False

    def valid(self, **changes):
        values = dict(user_id=7, username='database-user', grant=self.grant,
                      token='authorization-token', is_admin=False)
        values.update(changes)
        return validate_grant(self.session, **values)

    def test_valid_grant_does_not_write_or_renew_session(self):
        before = copy.deepcopy(self.session)
        self.assertTrue(self.valid())
        self.assertEqual(before, self.session)
        self.assertFalse(self.session.modified)

    def test_expired_or_deleted_panel_session_rejects(self):
        self.session.clear()
        self.assertFalse(self.valid())

    def test_logout_rejects(self):
        del self.session['userID']
        self.assertFalse(self.valid())

    def test_rotated_session_key_rejects_same_user(self):
        self.session.session_key = 'laterpanelsessionkey'
        self.assertFalse(self.valid())

    def test_other_principal_rejects(self):
        self.session['userID'] = 8
        self.assertFalse(self.valid(user_id=8))

    def test_wrong_grant_or_database_user_rejects(self):
        for kwargs in ({'grant': 'b' * 64}, {'grant': None}, {'username': 'other'}, {'grant': []}):
            self.assertFalse(self.valid(**kwargs))

    def test_changed_database_authorization_or_role_rejects(self):
        self.assertFalse(self.valid(token='new-authorization-token'))
        self.assertFalse(self.valid(is_admin=True))

    def test_new_handoff_revokes_prior_grant(self):
        next_grant = issue_grant(self.session, 7, 'database-user', 'authorization-token', False)
        self.assertNotEqual(self.grant, next_grant)
        self.assertFalse(self.valid())
        self.assertTrue(self.valid(grant=next_grant))

    def test_unbound_or_malformed_legacy_state_rejects(self):
        for state in (None, {}, 'legacy', {'grant': self.grant}):
            self.session[GRANT_KEY] = state
            self.assertFalse(self.valid())

    def test_grant_requires_authenticated_session_and_username(self):
        for session, uid, username in ((Session(), 7, 'user'), (self.session, 7, ''), (self.session, 8, 'user')):
            with self.assertRaises(ValueError):
                issue_grant(session, uid, username, 'token', False)

    def test_high_ipv4_matches_exactly(self):
        self.assertTrue(panel_ip_allowed(self.session, '203.0.113.10', 0))
        self.assertFalse(panel_ip_allowed(self.session, '203.0.113.11', 0))

    def test_high_ipv6_preserves_existing_three_group_rule(self):
        self.session['ipAddr'] = '2001:db8:1'
        self.assertTrue(panel_ip_allowed(self.session, '2001:db8:1::a', 0))
        self.assertTrue(panel_ip_allowed(self.session, '2001:db8:1::b', 0))
        self.assertFalse(panel_ip_allowed(self.session, '2001:db8:2::a', 0))

    def test_low_accepts_valid_network_changes(self):
        self.assertTrue(panel_ip_allowed(self.session, '203.0.113.11', 1))
        self.assertTrue(panel_ip_allowed(self.session, '2001:db8:2::a', 1))

    def test_missing_invalid_ip_or_policy_rejects(self):
        for ip in (None, '', 'invalid', ['203.0.113.10']):
            self.assertFalse(panel_ip_allowed(self.session, ip, 0))
            self.assertFalse(panel_ip_allowed(self.session, ip, 1))
        self.assertFalse(panel_ip_allowed(self.session, '203.0.113.10', 9))


if __name__ == '__main__':
    unittest.main()
