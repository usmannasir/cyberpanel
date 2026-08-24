import unittest

from databases.phpmyadmin_handoff import consume_handoff, create_handoff


class Session(dict):
    modified = False


class PhpMyAdminHandoffTests(unittest.TestCase):
    def test_creates_short_lived_session_handoff(self):
        session = Session()

        create_handoff(
            session, 'database-user', 'unpredictable-token',
            now=1_000, ttl=120,
        )

        self.assertEqual(
            {
                'username': 'database-user',
                'token': 'unpredictable-token',
                'expires': 1_120,
            },
            session['phpmyadmin_handoff'],
        )
        self.assertTrue(session.modified)

    def test_consumes_valid_handoff_only_once(self):
        session = Session()
        create_handoff(session, 'admin', 'token', now=1_000)

        self.assertTrue(
            consume_handoff(session, 'admin', 'token', now=1_001)
        )
        self.assertFalse(
            consume_handoff(session, 'admin', 'token', now=1_002)
        )
        self.assertNotIn('phpmyadmin_handoff', session)

    def test_rejects_and_consumes_mismatched_handoff(self):
        session = Session()
        create_handoff(session, 'admin', 'correct-token', now=1_000)

        self.assertFalse(
            consume_handoff(session, 'admin', 'wrong-token', now=1_001)
        )
        self.assertNotIn('phpmyadmin_handoff', session)

    def test_rejects_expired_handoff(self):
        session = Session()
        create_handoff(
            session, 'admin', 'token', now=1_000, ttl=10,
        )

        self.assertFalse(
            consume_handoff(session, 'admin', 'token', now=1_011)
        )
        self.assertNotIn('phpmyadmin_handoff', session)


if __name__ == '__main__':
    unittest.main()
