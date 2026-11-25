import json
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from baseTemplate import views


LAST_OUTPUT = """ubuntu   pts/0        206.84.168.7     Sun Jun  1 19:41   still logged in
ubuntu   pts/1        206.84.169.36    Tue May 27 11:34 - 13:47  (02:13)
root     tty1                          Tue May 27 09:02 - 09:10  (00:08)
reboot   system boot  6.8.0-31-generic Tue May 27 09:00   still running

wtmp begins Sun May  4 10:00:01 2025
"""

JOURNAL_OUTPUT = """2026-11-25T14:01:02+00:00 host sshd-session[811]: Failed password for root from 198.51.100.4 port 4444 ssh2
2026-11-25T14:02:09+00:00 host sshd-session[812]: Accepted publickey for root from 203.0.113.7 port 50122 ssh2: ED25519 SHA256:x
2026-11-25T14:05:00+00:00 host sshd[900]: Accepted password for ubuntu from 2001:db8::5 port 2222 ssh2
2026-11-25T14:06:00+00:00 host sshd-session[901]: Invalid user admin from 198.51.100.9 port 1
"""


class LastOutputTests(SimpleTestCase):

    def test_login_records_are_read(self):
        logins = views.parse_last_logins(LAST_OUTPUT)

        self.assertEqual(
            [('ubuntu', '206.84.168.7', 'Sun Jun  1 19:41', 'still logged in'),
             ('ubuntu', '206.84.169.36', 'Tue May 27 11:34', '13:47  (02:13)'),
             ('root', '', 'Tue May 27 09:02', '09:10  (00:08)')],
            [(row['user'], row['ip'], row['date'], row['session']) for row in logins])
        self.assertIn('pts/0', logins[0]['raw'])

    def test_error_messages_are_not_logins(self):
        for text in ('sudo: last: command not found',
                     'sh: 1: last: not found',
                     'last: cannot open /var/log/wtmp: No such file or directory'):
            self.assertEqual([], views.parse_last_logins(text), text)


class SshdJournalTests(SimpleTestCase):

    def test_only_accepted_logins_newest_first(self):
        logins = views.parse_sshd_accepted(JOURNAL_OUTPUT)

        self.assertEqual(
            [('ubuntu', '2001:db8::5', 'Wed Nov 25 14:05'),
             ('root', '203.0.113.7', 'Wed Nov 25 14:02')],
            [(row['user'], row['ip'], row['date']) for row in logins])

    def test_entries_out_of_order_are_sorted(self):
        lines = ('2026-11-25T15:43:27+00:00 host sshd-session[1757]: Accepted publickey for root from 136.243.211.211 port 51718 ssh2\n'
                 '2026-11-25T15:43:24+00:00 host sshd-session[1725]: Accepted publickey for alice from 136.243.211.211 port 43528 ssh2\n'
                 '2026-11-25T15:44:00+00:00 host sshd-session[1800]: Accepted password for bob from 203.0.113.8 port 1 ssh2\n')

        self.assertEqual(['bob', 'root', 'alice'], [row['user'] for row in views.parse_sshd_accepted(lines)])

    def test_limit(self):
        lines = '\n'.join(
            '2026-11-25T10:%02d:00+00:00 host sshd[1]: Accepted publickey for root from 203.0.113.%d port 1 ssh2'
            % (minute, minute) for minute in range(30))

        logins = views.parse_sshd_accepted(lines)

        self.assertEqual(20, len(logins))
        self.assertEqual('203.0.113.29', logins[0]['ip'])


class RecentSshLoginsSourceTests(SimpleTestCase):

    def test_last_is_used_when_it_works(self):
        with mock.patch.object(views.ProcessUtilities, 'outputExecutioner',
                               return_value=(1, LAST_OUTPUT)) as run:
            logins = views.recent_ssh_logins()

        self.assertEqual(3, len(logins))
        self.assertEqual(['last -n 20'], [call.args[0] for call in run.call_args_list])

    def test_journal_is_used_when_last_is_missing(self):
        answers = [(0, 'sudo: last: command not found'), (1, JOURNAL_OUTPUT)]
        with mock.patch.object(views.ProcessUtilities, 'outputExecutioner', side_effect=answers) as run:
            logins = views.recent_ssh_logins()

        self.assertEqual(['ubuntu', 'root'], [row['user'] for row in logins])
        self.assertTrue(run.call_args_list[1].args[0].startswith('journalctl '))

    def test_journal_is_used_when_the_helper_reports_success_for_a_missing_last(self):
        # The panel's root helper returned status 0 for "sudo last -n 20" on Ubuntu 26.04.
        answers = [(1, 'sudo: last: command not found\n'), (1, JOURNAL_OUTPUT)]
        with mock.patch.object(views.ProcessUtilities, 'outputExecutioner', side_effect=answers):
            logins = views.recent_ssh_logins()

        self.assertEqual(['ubuntu', 'root'], [row['user'] for row in logins])

    def test_empty_wtmp_is_not_a_reason_to_read_the_journal(self):
        with mock.patch.object(views.ProcessUtilities, 'outputExecutioner',
                               return_value=(1, '\nwtmp begins Tue May 26 15:23:39 2026\n')) as run:
            self.assertEqual([], views.recent_ssh_logins())

        self.assertEqual(1, run.call_count)

    def test_journal_without_grep_support(self):
        answers = [(0, 'sudo: last: command not found'),
                   (0, 'journalctl: Compiled without pattern matching support'),
                   (1, JOURNAL_OUTPUT)]
        with mock.patch.object(views.ProcessUtilities, 'outputExecutioner', side_effect=answers):
            logins = views.recent_ssh_logins()

        self.assertEqual(2, len(logins))

    def test_nothing_readable_gives_no_rows(self):
        with mock.patch.object(views.ProcessUtilities, 'outputExecutioner',
                               return_value=(0, 'sudo: journalctl: command not found')):
            self.assertEqual([], views.recent_ssh_logins())


class RecentSshLoginsViewTests(SimpleTestCase):

    def get(self):
        request = RequestFactory().get('/base/getRecentSSHLogins')
        request.session = {'userID': 1}
        return request

    @mock.patch('baseTemplate.views.ACLManager.loadedACL', return_value={'admin': 1})
    @mock.patch('baseTemplate.views.requests.get')
    def test_missing_last_shows_no_error_row(self, geo, unused_acl):
        geo.return_value.json.return_value = {'countryCode': 'US'}
        answers = [(0, 'sudo: last: command not found'), (1, JOURNAL_OUTPUT)]
        with mock.patch.object(views.ProcessUtilities, 'outputExecutioner', side_effect=answers):
            response = views.getRecentSSHLogins(self.get())

        logins = json.loads(response.content)['logins']
        self.assertEqual(200, response.status_code)
        self.assertNotIn('sudo:', [row['user'] for row in logins])
        self.assertEqual(['ubuntu', 'root'], [row['user'] for row in logins])
        self.assertEqual('US', logins[1]['country'])

    @mock.patch('baseTemplate.views.ACLManager.loadedACL', return_value={'admin': 0})
    def test_admin_only(self, unused_acl):
        with mock.patch.object(views.ProcessUtilities, 'outputExecutioner') as run:
            response = views.getRecentSSHLogins(self.get())

        self.assertEqual(403, response.status_code)
        run.assert_not_called()
