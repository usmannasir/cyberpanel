"""The tables, the audit trail and the stored licence answer on a real MariaDB.

Runs only as root on a server marked as a disposable test server (see
multiServer/testing.py) and is skipped everywhere else. Each class works in a
database of its own that is dropped afterwards.
"""
import threading
import unittest
from unittest.mock import patch

from multiServer import audit, entitlement, keys, schema, switch, testing

SKIP = testing.unavailable()
if SKIP is None:
    testing.start_django()
    from django.db import IntegrityError, connection, transaction
    from multiServer import models

LINK, OTHER_LINK = 'a1' * 16, 'b2' * 16
NAMES = [table.name for table in schema.TABLES]


@unittest.skipIf(SKIP, SKIP)
class OwnDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = testing.ScratchDatabase()

    @classmethod
    def tearDownClass(cls):
        cls.database.drop()

    def ensure(self):
        server = self.database.connect()
        try:
            schema.ensure_tables(server, server.cursor())
        finally:
            server.close()

    def description(self):
        return {name: self.database.run('SHOW CREATE TABLE `%s`' % name)[0][1] for name in NAMES}


class TableTests(OwnDatabase):
    """ensure_tables with the plain driver connection an installer or upgrader would hand it."""

    def test_1_creates_every_table_and_a_second_run_changes_nothing(self):
        self.assertEqual((), self.database.run('SHOW TABLES'))
        self.ensure()
        self.assertEqual(sorted(NAMES), sorted(row[0] for row in self.database.run('SHOW TABLES')))
        for name, engine, collation in self.database.run(
                'SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES '
                'WHERE TABLE_SCHEMA = DATABASE()'):
            self.assertEqual(('InnoDB', 'utf8mb4_bin'), (engine, collation), name)
        first = self.description()
        self.database.run("INSERT INTO ms_entitlement (id, server_ip) VALUES (1, '203.0.113.20')")
        self.ensure()
        self.ensure()
        self.assertEqual(first, self.description())
        self.assertEqual(((1,),), self.database.run('SELECT COUNT(*) FROM ms_entitlement'))
        self.database.run('DELETE FROM ms_entitlement')

    def test_2_a_table_without_a_required_unique_index_stops_it(self):
        self.ensure()
        for table, columns, remove, restore in (
                ('ms_links', 'pairing_key', 'DROP INDEX ms_links_pairing',
                 'ADD UNIQUE KEY ms_links_pairing (pairing_key)'),
                ('ms_nonces', 'link_id, nonce',
                 'DROP INDEX ms_nonces_link_nonce, ADD INDEX not_unique (link_id, nonce)',
                 'DROP INDEX not_unique, ADD UNIQUE KEY ms_nonces_link_nonce (link_id, nonce)'),
                ('ms_nonces', 'link_id, nonce',
                 'DROP INDEX ms_nonces_link_nonce, ADD UNIQUE KEY wider (link_id, nonce, seen_at)',
                 'DROP INDEX wider, ADD UNIQUE KEY ms_nonces_link_nonce (link_id, nonce)'),
                ('ms_nonces', 'link_id, nonce',
                 'DROP INDEX ms_nonces_link_nonce, ADD UNIQUE KEY shorter (link_id, nonce(8))',
                 'DROP INDEX shorter, ADD UNIQUE KEY ms_nonces_link_nonce (link_id, nonce)')):
            self.database.run('ALTER TABLE %s %s' % (table, remove))
            with self.assertRaises(RuntimeError) as refused:
                self.ensure()
            self.assertEqual('Multi-Server Manager tables are not usable: %s: no unique index on exactly (%s)'
                             % (table, columns), str(refused.exception))
            self.database.run('ALTER TABLE %s %s' % (table, restore))
            self.ensure()

    def test_3_a_table_from_somewhere_else_is_reported_not_replaced(self):
        self.database.run('ALTER TABLE ms_audit DROP COLUMN dropped')
        with self.assertRaisesRegex(RuntimeError, 'ms_audit: column dropped is missing'):
            self.ensure()
        self.database.run('ALTER TABLE ms_audit ADD dropped smallint NOT NULL DEFAULT 0')
        self.ensure()
        self.database.run('DROP TABLE ms_sessions')
        connection_ = self.database.connect()
        try:
            self.assertEqual(['ms_sessions: the table is missing'], schema.problems(connection_.cursor()))
        finally:
            connection_.close()
        self.ensure()

    def test_4_the_server_itself_refuses_a_replayed_nonce_and_a_second_link_for_one_code(self):
        self.ensure()
        duplicate = self.database.driver.IntegrityError
        link = ("INSERT INTO ms_links (link_id, controller_key, pairing_key, allowed_ips, admin_id, generation, "
                "created_at, updated_at, expires_at) VALUES ('%s', '%s', '%s', '203.0.113.9', 1, 1, 1, 1, 2)")
        nonce = "INSERT INTO ms_nonces (link_id, nonce, seen_at) VALUES ('%s', '%s', 1)"
        self.database.run(link % (LINK, 'c1' * 32, 'd1' * 32))
        with self.assertRaises(duplicate):
            self.database.run(link % (OTHER_LINK, 'c2' * 32, 'd1' * 32))
        with self.assertRaises(duplicate):
            self.database.run(link % (LINK, 'c2' * 32, 'd2' * 32))
        self.database.run(link % (OTHER_LINK, 'c2' * 32, 'd2' * 32))
        self.database.run(nonce % (LINK, 'e1' * 16))
        with self.assertRaises(duplicate):
            self.database.run(nonce % (LINK, 'e1' * 16))
        self.database.run(nonce % (OTHER_LINK, 'e1' * 16))
        self.database.run(nonce % (LINK, 'e2' * 16))
        with self.assertRaises(duplicate):
            self.database.run(nonce % ('f9' * 16, 'e3' * 16))
        self.assertEqual(((3,),), self.database.run('SELECT COUNT(*) FROM ms_nonces'))
        self.database.run("DELETE FROM ms_links WHERE link_id = '%s'" % LINK)
        self.assertEqual(((OTHER_LINK, 'e1' * 16),), self.database.run('SELECT link_id, nonce FROM ms_nonces'))
        self.database.run('DELETE FROM ms_links')

    def test_5_identifiers_that_differ_only_in_case_are_different(self):
        self.ensure()
        row = "INSERT INTO ms_pairing_codes (public_key, controller_ip, admin_id, created_at, expires_at) " \
              "VALUES ('%s', '203.0.113.9', 1, 1, 2)"
        self.database.run(row % ('ab' * 32))
        self.database.run(row % ('AB' * 32))
        self.assertEqual(((0,),), self.database.run(
            "SELECT COUNT(*) FROM ms_pairing_codes WHERE public_key = '%s'" % ('Ab' * 32)))
        self.database.run('DELETE FROM ms_pairing_codes')


class DjangoDatabase(OwnDatabase):
    """The same tables, created and used through Django's connection as the panel does."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.database.give_to_django()
        cls.ready_patch = patch.object(schema, '_READY', False)
        cls.ready_patch.start()
        with connection.cursor() as cursor:
            schema.ensure_tables(connection, cursor)

    @classmethod
    def tearDownClass(cls):
        cls.ready_patch.stop()
        super().tearDownClass()

    def setUp(self):
        for name in reversed(NAMES):
            self.database.run('DELETE FROM `%s`' % name)


class ModelTests(DjangoDatabase):
    def link(self, link_id=LINK, pairing_key='d1' * 32):
        return models.Link.objects.create(
            link_id=link_id, controller_key='c1' * 32, pairing_key=pairing_key, allowed_ips='203.0.113.9',
            admin_id=1, generation=1, created_at=10, updated_at=10, expires_at=20)

    def node(self, link_id=LINK):
        return models.Node.objects.create(link_id=link_id, label='Frankfurt 1', sealed='gAAAAAB' + 'x' * 900,
                                          created_at=10, updated_at=10)

    def test_every_model_reads_and_writes_its_table(self):
        link, node = self.link(), self.node()
        models.InventoryCache.objects.create(node=node, snapshot='{"websites": []}', fetched_at=11)
        models.Capability.objects.create(token_hash='e1' * 32, node=node, admin_id=1, session_hash='e2' * 32,
                                         created_at=10, expires_at=20)
        models.Entitlement.objects.create(id=1, server_ip='203.0.113.20')
        models.PairingCode.objects.create(public_key='d1' * 32, controller_ip='2001:db8::9', admin_id=1,
                                          created_at=10, expires_at=20)
        models.Nonce.objects.create(link=link, nonce='e3' * 16, seen_at=12)
        models.SsoTicket.objects.create(ticket_hash='e4' * 32, link=link, admin_id=1, actor='admin',
                                        landing='/websites/listWebsites', created_at=10, expires_at=11)
        models.LinkSession.objects.create(session_key='s' * 32, link=link, created_at=10)
        models.AuditEntry.objects.create(at=10, event='link_approve', outcome='ok')
        for model in (models.Node, models.InventoryCache, models.Capability, models.Entitlement, models.Link,
                      models.PairingCode, models.Nonce, models.SsoTicket, models.LinkSession, models.AuditEntry):
            self.assertEqual(1, len(list(model.objects.all())), model.__name__)
        stored = models.Link.objects.get(pk=LINK)
        self.assertEqual(('pending', None, 0), (stored.status, stored.activated_at, stored.last_request_at))
        stored = models.Node.objects.get(pk=LINK)
        self.assertEqual(('pending', '', None, '', None), (stored.status, stored.panel_version, stored.last_seen_at,
                                                           stored.last_error, stored.last_error_at))
        code = models.PairingCode.objects.get()
        self.assertEqual((0, False), (code.failures, code.consumed))
        self.assertIs(False, models.SsoTicket.objects.get().used)

    def test_a_nonce_is_accepted_once_per_link(self):
        link, other = self.link(), self.link(OTHER_LINK, 'd2' * 32)
        models.Nonce.objects.create(link=link, nonce='e3' * 16, seen_at=12)
        with self.assertRaises(IntegrityError):
            models.Nonce.objects.create(link=link, nonce='e3' * 16, seen_at=13)
        models.Nonce.objects.create(link=other, nonce='e3' * 16, seen_at=12)
        self.assertEqual(2, models.Nonce.objects.count())

    def test_one_pairing_code_gives_one_link(self):
        self.link()
        with self.assertRaises(IntegrityError):
            self.link(OTHER_LINK)
        self.assertEqual([LINK], list(models.Link.objects.values_list('link_id', flat=True)))

    def test_a_pairing_code_is_consumed_by_exactly_one_of_many_workers(self):
        models.PairingCode.objects.create(public_key='d1' * 32, controller_ip='203.0.113.9', admin_id=1,
                                          created_at=10, expires_at=20)
        won = []

        def consume():
            try:
                won.append(models.PairingCode.objects.filter(pk='d1' * 32, consumed=False).update(consumed=True))
            finally:
                connection.close()
        workers = [threading.Thread(target=consume) for _ in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertEqual([0] * 7 + [1], sorted(won))

    def test_removing_a_link_or_a_node_removes_what_hangs_on_it(self):
        link, node = self.link(), self.node()
        models.Nonce.objects.create(link=link, nonce='e3' * 16, seen_at=12)
        models.SsoTicket.objects.create(ticket_hash='e4' * 32, link=link, admin_id=1, actor='admin',
                                        landing='/base/', created_at=10, expires_at=11)
        models.LinkSession.objects.create(session_key='s' * 32, link=link, created_at=10)
        models.InventoryCache.objects.create(node=node, snapshot='{}')
        models.Capability.objects.create(token_hash='e1' * 32, node=node, admin_id=1, session_hash='e2' * 32,
                                         created_at=10, expires_at=20)
        # Removed with plain statements, as a command-line tool would: the database itself cascades.
        self.database.run('DELETE FROM ms_links')
        self.database.run('DELETE FROM ms_nodes')
        for model in (models.Nonce, models.SsoTicket, models.LinkSession, models.InventoryCache, models.Capability):
            self.assertEqual(0, model.objects.count(), model.__name__)


class AuditTests(DjangoDatabase):
    def test_a_recorded_event_is_one_row_with_exactly_the_accepted_fields(self):
        with patch.object(audit.time, 'time', return_value=1795000000.2):
            self.assertIs(True, audit.record(
                'request', outcome='refused', reason='replay', link_id=LINK, actor='admin',
                source_ip='2001:DB8::9', method='POST', path='/websites/submitWebsiteCreation?x=' + 'f3' * 32,
                status=403, size=2048, body=b'{"password": "hunter2"}', ticket='f3' * 32))
        self.assertEqual(((1795000000, 'request', 'refused', 'replay', LINK, 'admin', '2001:db8::9', 'POST',
                           '/websites/submitWebsiteCreation', 403, 2048, 2),), self.database.run(
            'SELECT `at`, event, outcome, reason, link_id, actor, source_ip, method, path, status, size, dropped '
            'FROM ms_audit'))

    def test_an_event_with_no_fields_uses_the_table_defaults(self):
        self.assertIs(True, audit.record('link_pause'))
        entry = models.AuditEntry.objects.get()
        self.assertEqual(('link_pause', 'ok', '', '', '', '', '', '', None, None, 0),
                         (entry.event, entry.outcome, entry.reason, entry.link_id, entry.actor, entry.source_ip,
                          entry.method, entry.path, entry.status, entry.size, entry.dropped))

    def test_a_failed_write_is_false_and_leaves_the_callers_transaction_usable(self):
        self.database.run('RENAME TABLE ms_audit TO ms_audit_away')
        try:
            with transaction.atomic():
                models.Entitlement.objects.create(id=1, server_ip='203.0.113.20')
                self.assertIs(False, audit.record('licence', outcome='error', reason='internal'))
                self.assertEqual(1, models.Entitlement.objects.count())
        finally:
            self.database.run('RENAME TABLE ms_audit_away TO ms_audit')
        self.assertEqual(1, models.Entitlement.objects.count())
        self.assertIs(True, audit.record('licence'))


class EntitlementTests(DjangoDatabase):
    ADDRESS = '203.0.113.20'

    def row(self):
        return self.database.run('SELECT id, server_ip, granted, answered_at, checked_at FROM ms_entitlement')

    def test_nothing_stored_is_none(self):
        self.assertIsNone(entitlement._load())

    def test_an_answer_replaces_the_single_row(self):
        entitlement._save_answer(self.ADDRESS, True, 100)
        self.assertEqual(((1, self.ADDRESS, 1, 100, 100),), self.row())
        self.assertEqual(entitlement.State(self.ADDRESS, True, 100, 100), entitlement._load())
        self.assertIs(True, entitlement._load().granted)
        entitlement._save_answer(self.ADDRESS, False, 170)
        self.assertEqual(((1, self.ADDRESS, 0, 170, 170),), self.row())
        self.assertIs(False, entitlement._load().granted)
        entitlement._save_answer('2001:db8::20', True, 180)
        self.assertEqual(((1, '2001:db8::20', 1, 180, 180),), self.row())

    def test_an_unanswered_attempt_keeps_the_last_answer_for_the_same_address(self):
        entitlement._save_answer(self.ADDRESS, True, 100)
        entitlement._save_attempt(self.ADDRESS, 161)
        self.assertEqual(((1, self.ADDRESS, 1, 100, 161),), self.row())
        entitlement._save_attempt(self.ADDRESS, 171)
        self.assertEqual(((1, self.ADDRESS, 1, 100, 171),), self.row())

    def test_an_unanswered_attempt_for_another_address_forgets_the_old_answer(self):
        entitlement._save_answer(self.ADDRESS, True, 100)
        entitlement._save_attempt('203.0.113.21', 161)
        self.assertEqual(((1, '203.0.113.21', 0, 0, 161),), self.row())

    def test_the_first_attempt_ever_stores_that_there_is_no_answer(self):
        entitlement._save_attempt(self.ADDRESS, 50)
        self.assertEqual(((1, self.ADDRESS, 0, 0, 50),), self.row())
        self.assertEqual(entitlement.State(self.ADDRESS, False, 0, 50), entitlement._load())

    def test_workers_writing_at_once_leave_one_consistent_row(self):
        failures = []

        def worker(number):
            try:
                for _ in range(20):
                    if number % 2:
                        entitlement._save_answer(self.ADDRESS, True, 100)
                    else:
                        entitlement._save_attempt(self.ADDRESS, 161)
            except Exception as error:
                failures.append(error)
            finally:
                connection.close()
        workers = [threading.Thread(target=worker, args=(number,)) for number in range(8)]
        for thread in workers:
            thread.start()
        for thread in workers:
            thread.join()
        self.assertEqual([], failures)
        (row,) = self.row()
        # An attempt never erases a yes: whichever statement ran last, the yes of time 100 is there.
        self.assertEqual((1, self.ADDRESS, 1, 100), row[:4])
        self.assertIn(row[4], (100, 161))

    def test_allowed_through_the_real_row(self):
        answers = [True]
        now = [1795000000]
        with patch.object(entitlement, 'server_address', return_value=self.ADDRESS), \
                patch.object(entitlement, 'ask', side_effect=lambda address: answers[-1]) as ask, \
                patch.object(entitlement.time, 'time', side_effect=lambda: now[0]):
            self.assertIs(True, entitlement.allowed())
            self.assertIs(True, entitlement.allowed())
            self.assertEqual(1, ask.call_count)
            answers.append(None)
            now[0] += 60
            self.assertIs(True, entitlement.allowed())
            now[0] += 5
            self.assertIs(True, entitlement.allowed())
            self.assertEqual(2, ask.call_count)
            now[0] += 24 * 60 * 60
            self.assertIs(False, entitlement.allowed())
            answers.append(True)
            now[0] += 10
            self.assertIs(True, entitlement.allowed())

    def test_without_the_table_the_answer_is_no_and_the_platform_is_not_asked(self):
        self.database.run('RENAME TABLE ms_entitlement TO ms_entitlement_away')
        try:
            with patch.object(entitlement, 'server_address', return_value=self.ADDRESS), \
                    patch.object(entitlement, 'ask', return_value=True) as ask:
                with transaction.atomic():
                    self.assertIs(False, entitlement.allowed())
                    self.assertEqual(0, models.Link.objects.count())
                ask.assert_not_called()
        finally:
            self.database.run('RENAME TABLE ms_entitlement_away TO ms_entitlement')


class SwitchTests(DjangoDatabase):
    def test_on_only_with_a_role_working_signatures_and_usable_tables(self):
        with patch.object(keys, 'role', return_value='off'):
            self.assertEqual('off', switch.active_role())
        for role in ('node', 'controller'):
            with patch.object(keys, 'role', return_value=role):
                self.assertEqual(role, switch.active_role())

    def test_off_while_a_table_is_missing_or_lacks_its_unique_index(self):
        for damage, repair in (
                ('RENAME TABLE ms_audit TO ms_audit_away', 'RENAME TABLE ms_audit_away TO ms_audit'),
                ('ALTER TABLE ms_links DROP INDEX ms_links_pairing',
                 'ALTER TABLE ms_links ADD UNIQUE KEY ms_links_pairing (pairing_key)')):
            self.database.run(damage)
            try:
                with patch.object(keys, 'role', return_value='node'), patch.object(schema, '_READY', False):
                    self.assertIs(False, schema.ready())
                    self.assertEqual('off', switch.active_role())
                    self.database.run(repair)
                    repair = None
                    self.assertEqual('node', switch.active_role(), 'repaired tables are noticed without a restart')
            finally:
                if repair:
                    self.database.run(repair)

    def test_checking_an_empty_database_reports_every_table_and_creates_none(self):
        empty = testing.ScratchDatabase()
        try:
            server = empty.connect()
            try:
                self.assertEqual(len(NAMES), len(schema.problems(server.cursor())))
            finally:
                server.close()
            self.assertEqual((), empty.run('SHOW TABLES'))
        finally:
            empty.drop()


if __name__ == '__main__':
    unittest.main()
