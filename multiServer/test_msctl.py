"""The root command line (msctl.py) and what only it does: the role of a server, and ending a link for good.

The cases with real rows, real sessions and a controller's signed requests run
on a server marked as a disposable test server (multiServer/testing.py).
"""
import ast
import os
from pathlib import Path
import secrets
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from install import multiserver_identity as provision
from multiServer import crypto, keys, msctl, test_gateway, testing
from multiServer.test_keys import MY_GROUP, Directory

SKIP = testing.unavailable()
if SKIP is None:
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.sessions.models import Session
    from multiServer import controllers, models
    Base = test_gateway.Panel
else:
    Base = unittest.TestCase

LINK, OTHER_LINK, THIRD_LINK = test_gateway.LINK, test_gateway.OTHER_LINK, 'c3' * 16
NOW = test_gateway.NOW
IN_THE_WAY = msctl._in_the_way  # the real one; the command-line tests stand in for it


class CommandLine(Directory):
    """msctl.py run by root, with a key directory of the test's own in the place of root's."""

    def setUp(self):
        super().setUp()
        self.said = []
        self.in_the_way = None
        for target, name, stand_in in ((os, 'geteuid', lambda: 0), (provision, '_gid', lambda group: MY_GROUP),
                                       (msctl, '_in_the_way', lambda role: self.asked(role))):
            patcher = patch.object(target, name, stand_in)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.checked = []
        provision.ensure_key_directory(group=MY_GROUP)

    def asked(self, role):
        self.checked.append(role)
        return self.in_the_way

    def run_it(self, *arguments):
        del self.said[:]
        return msctl.main(list(arguments), self.said.append)


class RoleTests(CommandLine):
    def test_a_server_is_given_each_role_and_the_keys_of_that_role(self):
        self.assertEqual((0, ['This server is now: node.']), (self.run_it('role', 'node'), self.said))
        self.assertEqual(('node', 1), (keys.role(), keys.generation()))
        self.assertEqual(32, len(keys.identity_key()))
        self.assertEqual((0, ['This server is now: off.']), (self.run_it('role', 'off'), self.said))
        self.assertEqual('off', keys.role())
        self.assertEqual((0, ['This server is now: controller.']), (self.run_it('role', 'controller'), self.said))
        self.assertEqual('controller', keys.role())
        self.assertIsNotNone(keys.master_key())
        self.assertEqual((0, ['This server is now: off.']), (self.run_it('disable'), self.said))
        self.assertEqual('off', keys.role())
        # The same state the installer's own provisioning leaves: private files, nothing replaced.
        self.assertEqual(['generation', 'identity.key', 'master.key', 'revoked', 'role'],
                         sorted(os.listdir(str(self.directory))))
        for name in ('generation', 'identity.key', 'master.key', 'role'):
            self.assertEqual(0o640, (self.directory / name).stat().st_mode & 0o777, name)

    def test_the_role_that_is_there_is_left_as_it_is(self):
        self.run_it('role', 'node')
        before = keys.role_revision('node')
        self.assertEqual((0, ['This server already is: node.']), (self.run_it('role', 'node'), self.said))
        self.assertEqual(before, keys.role_revision('node'), 'the file was not written again')
        self.assertEqual(['node'], self.checked)

    def test_switching_off_asks_nothing_and_is_never_refused(self):
        self.run_it('role', 'controller')
        del self.checked[:]
        self.in_the_way = msctl.HAS_SERVERS
        with patch.object(msctl, '_start_django', side_effect=RuntimeError('no database')) as started:
            self.assertEqual(0, self.run_it('role', 'off'))
            self.assertEqual(0, self.run_it('disable'))
            started.assert_not_called()
        self.assertEqual(([], 'off'), (self.checked, keys.role()))

    def test_a_role_is_refused_while_links_of_the_other_kind_exist_and_the_file_is_not_touched(self):
        self.run_it('role', 'controller')
        before = keys.role_revision('controller')
        for refusal in (msctl.HAS_SERVERS, msctl.CANNOT_CHECK):
            self.in_the_way = refusal
            self.assertEqual((1, [refusal]), (self.run_it('role', 'node'), self.said))
            self.assertEqual(before, keys.role_revision('controller'))
        self.run_it('role', 'off')
        self.in_the_way = msctl.HAS_CONTROLLERS
        self.assertEqual((1, [msctl.HAS_CONTROLLERS]), (self.run_it('role', 'controller'), self.said))
        self.assertEqual('off', keys.role())
        self.assertEqual(['node', 'node', 'controller'], self.checked[1:])

    def test_whatever_cannot_be_checked_is_in_the_way(self):
        with patch.object(msctl, '_start_django', side_effect=RuntimeError('no database')):
            for role in ('controller', 'node'):
                self.assertEqual(msctl.CANNOT_CHECK, IN_THE_WAY(role))

    def test_only_the_three_words_are_a_role_and_nothing_else_is_a_command(self):
        with patch.object(provision, 'set_role') as written:
            for arguments in ((), ('role',), ('role', 'Node'), ('role', 'node '), ('role', 'both'), ('role', 'node;id'),
                              ('role', 'node', 'off'), ('role', '../role'), ('role', ''), ('node',), ('status', 'x'),
                              ('disable', 'now'), ('revoke',), ('revoke', 'a1' * 15), ('revoke', 'A1' * 16),
                              ('revoke', 'a1' * 16 + ';id'), ('revoke', 'a1' * 16, 'admin'),
                              ('revoke', 'a1' * 16, '0'), ('revoke', 'a1' * 16, '1', '2'), ('--help',)):
                self.assertEqual((2, [msctl.USAGE]), (self.run_it(*arguments), self.said), arguments)
            self.assertEqual(2, msctl.set_role('both', self.said.append))
            written.assert_not_called()
        self.assertEqual('off', keys.role())

    def test_only_root_runs_it(self):
        with patch.object(os, 'geteuid', return_value=1000), patch.object(provision, 'set_role') as written:
            for arguments in (('status',), ('role', 'node'), ('disable',), ('revoke', 'a1' * 16)):
                self.assertEqual((1, [msctl.NOT_ROOT]), (self.run_it(*arguments), self.said))
            written.assert_not_called()

    def test_the_panel_has_three_fixed_command_lines_for_the_role_and_one_form_for_ending_a_link(self):
        self.assertEqual({
            'off': '/usr/local/CyberCP/bin/python /usr/local/CyberCP/multiServer/msctl.py role off',
            'controller': '/usr/local/CyberCP/bin/python /usr/local/CyberCP/multiServer/msctl.py role controller',
            'node': '/usr/local/CyberCP/bin/python /usr/local/CyberCP/multiServer/msctl.py role node',
        }, msctl.ROLE_COMMANDS)
        self.assertEqual('/usr/local/CyberCP/bin/python /usr/local/CyberCP/multiServer/msctl.py revoke %s 7'
                         % ('a1' * 16), msctl.revoke_command('a1' * 16, 7))
        for link_id, admin_id in (('a1' * 16 + ';id', 7), ('A1' * 16, 7), ('a1' * 15, 7), (None, 7), ('a1' * 16, '7'),
                                  ('a1' * 16, 0), ('a1' * 16, -1), ('a1' * 16, True), ('a1' * 16, 7.0),
                                  ('a1' * 16, 10 ** 9), ('a1' * 16 + '\n', 7)):
            with self.assertRaises(ValueError, msg=(link_id, admin_id)):
                msctl.revoke_command(link_id, admin_id)
        # Each of them is a command this program takes.
        with patch.object(msctl, 'set_role', return_value=0) as role, \
                patch.object(msctl, 'revoke', return_value=0) as revoke:
            for command in sorted(msctl.ROLE_COMMANDS.values()):
                self.assertEqual(0, self.run_it(*command.split(' ')[2:]))
            self.assertEqual(0, self.run_it(*msctl.revoke_command('a1' * 16, 7).split(' ')[2:]))
        self.assertEqual(['controller', 'node', 'off'], [call[0][0] for call in role.call_args_list])
        self.assertEqual(('a1' * 16, 7), revoke.call_args[0][:2])

    def test_a_link_is_ended_only_on_a_managed_server(self):
        for role in ('off', 'controller'):
            self.run_it('role', role)
            with patch.object(msctl, '_start_django') as started:
                self.assertEqual((1, [msctl.NOT_A_NODE]), (self.run_it('revoke', 'a1' * 16), self.said))
                started.assert_not_called()

    def test_a_failure_while_ending_a_link_is_said_in_fixed_words(self):
        self.run_it('role', 'node')
        with patch.object(msctl, '_start_django', side_effect=RuntimeError('secret detail')):
            self.assertEqual((1, [msctl.FAILED]), (self.run_it('revoke', 'a1' * 16, '7'), self.said))

    def test_the_role_is_shown(self):
        self.assertEqual((0, ['Role: off']), (self.run_it('status'), self.said))


class CompatibilityTests(unittest.TestCase):
    DIRECTORY = Path(__file__).resolve().parent

    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check an older grammar before Python 3.8')
    def test_sources_parse_as_python_3_6(self):
        for name in ('msctl.py', 'controllers.py', 'role.py', 'nodes.py', 'test_msctl.py', 'test_pages.py'):
            ast.parse((self.DIRECTORY / name).read_text(), feature_version=(3, 6))

    def test_the_program_takes_nothing_from_the_environment_or_standard_input_and_runs_no_shell(self):
        source = (self.DIRECTORY / 'msctl.py').read_text()
        for word in ('environ.get', 'os.getenv', 'input(', 'sys.stdin', 'subprocess', 'os.system', 'shell', 'eval(',
                     'exec('):
            self.assertNotIn(word, source, word)
        # Loaded by the panel for its command lines: nothing but the standard library is imported at that moment.
        tree = ast.parse(source)
        at_load = set(alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual({'os', 're', 'sys'}, at_load)
        self.assertEqual([], [node for node in tree.body if isinstance(node, ast.ImportFrom)])

    def test_run_as_a_program_it_imports_the_panel_and_not_its_own_directory(self):
        source = (self.DIRECTORY / 'msctl.py').read_text()
        self.assertIn("sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))", source)


@unittest.skipIf(SKIP, SKIP)
class EndTests(Base):
    """A managed server with two controllers; the first one's link is ended on the server itself."""
    OTHER = crypto.generate_private_key()

    def setUp(self):
        super().setUp()
        self.directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.directory)
        os.mkdir(os.path.join(self.directory, 'revoked'))
        self.start(patch.object(keys, 'KEY_DIRECTORY', self.directory))
        self.other = models.Link.objects.create(
            link_id=OTHER_LINK, controller_key=crypto.public_key(self.OTHER).hex(), pairing_key='d2' * 32,
            allowed_ips='127.0.0.1', admin_id=self.administrator.pk, status=models.ACTIVE, generation=1,
            created_at=NOW - 5000, updated_at=NOW - 5000, activated_at=NOW - 4000, expires_at=NOW + 86400)
        self.raised = []

    def raise_counter(self):
        self.generation.return_value += 1
        self.raised.append(self.generation.return_value)
        return self.generation.return_value

    def end(self, link_id=LINK, actor='admin'):
        return controllers.end(link_id, actor, self.raise_counter)

    def asks(self, link_id=LINK):
        """The status of the answer to a signed request of that link's controller."""
        key = test_gateway.CONTROLLER if link_id == LINK else self.OTHER
        return self.call(key=key, link_id=link_id)[0].status_code

    def rows(self):
        return dict((link.link_id, (link.status, link.generation)) for link in models.Link.objects.all())

    def managed_session(self, link):
        session = SessionStore()
        session['userID'] = self.administrator.pk
        session.save()
        models.LinkSession.objects.create(session_key=session.session_key, link=link, created_at=NOW)
        models.SsoTicket.objects.create(ticket_hash=secrets.token_hex(32), link=link, admin_id=self.administrator.pk,
                                        actor='admin', landing='index|x', created_at=NOW, expires_at=NOW + 30)
        return session.session_key

    def test_an_ended_link_fails_at_its_next_signed_request_and_every_other_link_goes_on(self):
        self.assertEqual((200, 200), (self.asks(), self.asks(OTHER_LINK)))
        ended, kept = self.managed_session(self.link), self.managed_session(self.other)
        own = self.sign_in()
        before = models.AuditEntry.objects.count()
        self.assertIs(True, self.end())
        self.assertEqual({LINK: ('revoked', 1), OTHER_LINK: ('active', 2)}, self.rows())
        self.assertEqual(([2], True, False), (self.raised, keys.revoked(LINK), keys.revoked(OTHER_LINK)))
        # The controller of the ended link gets nothing any more, signed as before; the other one does.
        self.assertNotEqual(200, self.asks())
        self.assertEqual(200, self.asks(OTHER_LINK))
        self.assertEqual('revoked', models.Link.objects.get(pk=LINK).status)
        # The sessions and tickets that came through the ended link are gone, and only those.
        self.assertEqual(sorted([kept, own]), sorted(Session.objects.values_list('session_key', flat=True)))
        self.assertEqual([kept], list(models.LinkSession.objects.values_list('session_key', flat=True)))
        self.assertEqual([OTHER_LINK], list(models.SsoTicket.objects.values_list('link_id', flat=True)))
        self.assertNotIn(ended, Session.objects.values_list('session_key', flat=True))
        # One audit row for it.
        rows = models.AuditEntry.objects.filter(event='link_revoke')
        self.assertEqual([('link_revoke', 'ok', '', LINK, 'admin')],
                         [(row.event, row.outcome, row.reason, row.link_id, row.actor) for row in rows])
        self.assertEqual(before + 1, models.AuditEntry.objects.filter(pk__lte=rows[0].pk).count())

    def test_neither_a_restored_database_nor_a_removed_marker_brings_it_back(self):
        self.assertIs(True, self.end())
        # The row as an older copy of the database has it.
        models.Link.objects.filter(pk=LINK).update(status=models.ACTIVE)
        self.assertNotEqual(200, self.asks())
        os.unlink(os.path.join(self.directory, 'revoked', LINK))
        self.assertNotEqual(200, self.asks())
        self.assertEqual('generation', models.AuditEntry.objects.order_by('-id').first().reason)
        # And the marker alone is enough, should the counter ever be set back.
        models.Link.objects.filter(pk=LINK).update(generation=2)
        self.assertEqual(200, self.asks())
        keys.mark_revoked(LINK)
        self.assertNotEqual(200, self.asks())

    def test_waiting_and_paused_links_of_other_controllers_are_carried_on_and_closed_ones_are_not(self):
        for link_id, status in ((THIRD_LINK, models.PENDING), ('d4' * 16, models.PAUSED), ('e5' * 16, models.REVOKED)):
            models.Link.objects.create(
                link_id=link_id, controller_key='c1' * 32, pairing_key=link_id * 2, allowed_ips='127.0.0.1',
                admin_id=self.administrator.pk, status=status, generation=1, created_at=NOW, updated_at=NOW,
                expires_at=NOW + 600)
        models.Link.objects.create(
            link_id='f6' * 16, controller_key='c1' * 32, pairing_key='f6' * 32, allowed_ips='127.0.0.1',
            admin_id=self.administrator.pk, status=models.ACTIVE, generation=0, created_at=NOW, updated_at=NOW,
            expires_at=NOW + 600)
        self.assertIs(True, self.end())
        self.assertEqual({LINK: ('revoked', 1), OTHER_LINK: ('active', 2), THIRD_LINK: ('pending', 2),
                          'd4' * 16: ('paused', 2), 'e5' * 16: ('revoked', 1), 'f6' * 16: ('active', 0)}, self.rows())

    def test_ending_twice_or_ending_what_is_not_there_changes_nothing_more(self):
        self.assertIs(True, self.end())
        before = (self.rows(), models.AuditEntry.objects.count())
        self.assertIsNone(self.end())
        self.assertIs(False, self.end(THIRD_LINK))
        self.assertEqual(before, (self.rows(), models.AuditEntry.objects.count()))
        self.assertEqual(([2], False), (self.raised, keys.revoked(THIRD_LINK)))
        # A link that was closed without a marker, as a rejected one is, gets its marker and nothing else.
        models.Link.objects.filter(pk=OTHER_LINK).update(status=models.REVOKED)
        self.assertIsNone(self.end(OTHER_LINK))
        self.assertEqual(([2], True), (self.raised, keys.revoked(OTHER_LINK)))
        for not_a_link in ('', 'a1' * 15, 'A1' * 16, None, 'a1' * 16 + '\n'):
            with self.assertRaises(ValueError):
                self.end(not_a_link)

    def test_an_ending_that_stopped_after_the_counter_was_raised_is_finished_by_the_next_one(self):
        # The counter in the key directory moved on and the rows did not (the database went away at
        # that moment). Until the link is ended again, every controller of this server is refused.
        self.generation.return_value = 2
        keys.mark_revoked(LINK)
        self.assertNotEqual(200, self.asks(OTHER_LINK))
        self.assertTrue(self.end())
        self.assertEqual({LINK: ('revoked', 1), OTHER_LINK: ('active', 3)}, self.rows())
        self.assertEqual([3], self.raised)
        self.assertEqual(200, self.asks(OTHER_LINK))
        self.assertNotEqual(200, self.asks())

    def test_catching_up_never_brings_back_a_link_that_was_ended(self):
        # Both links one behind the counter, the other one ended by its marker alone: it stays behind.
        self.generation.return_value = 2
        keys.mark_revoked(OTHER_LINK)
        self.assertTrue(self.end())
        self.assertEqual({LINK: ('revoked', 2), OTHER_LINK: ('active', 1)}, self.rows())
        self.assertNotEqual(200, self.asks(OTHER_LINK))

    def test_when_the_counter_cannot_be_raised_no_row_changes_and_the_link_is_stopped_all_the_same(self):
        def fails():
            raise OSError('read-only file system')
        for raise_counter in (fails, lambda: 1, lambda: 3, lambda: None):
            with self.assertRaises(Exception):
                controllers.end(LINK, 'admin', raise_counter)
            self.assertEqual({LINK: ('active', 1), OTHER_LINK: ('active', 1)}, self.rows())
            self.assertEqual(0, models.AuditEntry.objects.filter(event='link_revoke').count())
        self.assertTrue(keys.revoked(LINK))
        self.assertNotEqual(200, self.asks())
        self.assertEqual(200, self.asks(OTHER_LINK))
        self.generation.return_value = 0
        with self.assertRaises(RuntimeError):
            self.end(OTHER_LINK)

    def test_run_by_root_the_command_ends_the_link_and_names_the_administrator_who_asked(self):
        said = []
        with patch.object(provision, 'bump_generation', side_effect=self.raise_counter), \
                patch.object(provision, 'ensure_key_directory') as ensured, \
                patch.object(msctl, '_start_django'), patch.object(os, 'geteuid', return_value=0):
            self.assertEqual(0, msctl.main(['revoke', LINK, str(self.administrator.pk)], said.append))
            ensured.assert_called_once_with()
            self.assertEqual(1, msctl.main(['revoke', LINK], said.append))
            self.assertEqual(1, msctl.main(['revoke', THIRD_LINK], said.append))
            self.assertEqual(0, msctl.main(['revoke', OTHER_LINK], said.append))
        self.assertEqual([msctl.ENDED, msctl.ALREADY_ENDED, msctl.NO_SUCH_LINK, msctl.ENDED], said)
        self.assertEqual({LINK: ('revoked', 1), OTHER_LINK: ('revoked', 2)}, self.rows())
        self.assertEqual([(LINK, 'admin'), (OTHER_LINK, '')], [
            (row.link_id, row.actor) for row in models.AuditEntry.objects.filter(event='link_revoke').order_by('id')])
        self.assertNotEqual(200, self.asks(OTHER_LINK))

    def test_links_of_the_other_kind_are_in_the_way_of_a_role_and_closed_ones_are_not(self):
        with patch.object(msctl, '_start_django'):
            self.assertEqual(msctl.HAS_CONTROLLERS, msctl._in_the_way('controller'))
            self.assertIsNone(msctl._in_the_way('node'))
            models.Link.objects.update(status=models.REVOKED)
            self.assertIsNone(msctl._in_the_way('controller'))
            # A request that waits for approval is in the way; one that nobody approved in time is not
            # (the Controllers page does not show it either).
            import time
            models.Link.objects.filter(pk=LINK).update(status=models.PENDING, expires_at=int(time.time()) - 1)
            self.assertIsNone(msctl._in_the_way('controller'))
            models.Link.objects.filter(pk=LINK).update(expires_at=int(time.time()) + 600)
            self.assertEqual(msctl.HAS_CONTROLLERS, msctl._in_the_way('controller'))
            models.Node.objects.create(link_id=LINK, label='Frankfurt 1', sealed='x', created_at=NOW, updated_at=NOW)
            self.assertEqual(msctl.HAS_SERVERS, msctl._in_the_way('node'))


if __name__ == '__main__':
    unittest.main()
