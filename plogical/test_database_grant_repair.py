"""Grants of earlier releases get the exact form: escaped first, plain revoked after, others only listed."""
import re
import unittest
from pathlib import Path
from unittest import mock

from plogical import databaseGrantRepair
from plogical import databaseGrants

ROOT = Path(__file__).resolve().parents[1]
CHANGE = re.compile(r'(GRANT|REVOKE) (.+) ON `((?:[^`]|``)+)`\.\* (?:TO|FROM) %s(?:@%s)?( WITH GRANT OPTION)?')


class Server:
    """Just enough of a database server: its grant table and the statements the repair sends."""

    def __init__(self, grants, schemas=(), registered=(), literal=False, hidden=(), stuck=(), refuse=None,
                 folds=0, unstored=False):
        # grants: {(stored database, user, host): [privileges, with grant option]}
        self.grants = dict((key, list(value)) for key, value in grants.items())
        self.schemas, self.registered, self.literal = list(schemas), list(registered), literal
        self.hidden, self.stuck, self.refuse = set(hidden), set(stuck), refuse
        self.folds, self.unstored = folds, unstored
        self.statements, self.rows = [], []
        self.lowest_cover = {}

    def execute(self, query, args=None):
        self.statements.append((query, args))
        self.rows = []
        if self.refuse and query.startswith(self.refuse):
            raise RuntimeError('refused by the server')
        if query.startswith('SHOW VARIABLES'):
            self.rows = [('partial_revokes', 'ON')] if self.literal else []
        elif query == 'SELECT @@lower_case_table_names':
            self.rows = [(self.folds,)]
        elif query.startswith('SELECT Db, User, Host FROM mysql.db'):
            self.rows = sorted(self.grants)
        elif query.startswith('SELECT dbName FROM'):
            self.rows = [(name,) for name in self.registered]
        elif query.startswith('SELECT SCHEMA_NAME'):
            self.rows = [(name,) for name in self.schemas]
        elif query.startswith('SHOW GRANTS FOR'):
            holder = tuple(args) if len(args) == 2 else (args[0], '')
            self.rows = [("GRANT USAGE ON *.* TO `%s`@`%s` IDENTIFIED BY PASSWORD '*00'" % holder,)]
            for (stored, user, host), (privileges, option) in sorted(self.grants.items()):
                if (user, host) == holder and (stored, user, host) not in self.hidden:
                    self.rows.append(('GRANT %s ON `%s`.* TO `%s`@`%s`%s' % (
                        privileges, stored.replace('`', '``'), user, host, ' WITH GRANT OPTION' if option else ''),))
        elif query.startswith('SELECT 1 FROM mysql.db'):
            self.rows = [(1,)] if tuple(args) in self.grants else []
        else:
            change = CHANGE.fullmatch(query)
            assert change, 'unexpected statement: ' + query
            verb, privileges, stored, option = change.groups()
            holder = tuple(args) if len(args) == 2 else (args[0], '')
            key = (stored.replace('``', '`'),) + holder
            if verb == 'GRANT':
                if not self.unstored:
                    self.grants[key] = [privileges, bool(option)]
            elif key not in self.stuck:
                if privileges == 'GRANT OPTION':
                    self.grants.pop(key, None)
                elif not self.grants[key][1]:
                    del self.grants[key]
                else:
                    self.grants[key][0] = 'USAGE'
            self.note_cover(holder)

    def note_cover(self, account):
        """After each change: how many grants give this account its database."""
        held = [stored for (stored, user, host), value in self.grants.items()
                if (user, host) == tuple(account) and value[0] != 'USAGE']
        self.lowest_cover[tuple(account)] = min(self.lowest_cover.get(tuple(account), 9), len(held))

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows

    def changes(self):
        return [(query, args) for query, args in self.statements if query.startswith(('GRANT', 'REVOKE'))]


def repair(server, registered):
    return databaseGrantRepair.repair(server, registered)


class RepairTests(unittest.TestCase):
    def test_plain_grant_is_granted_exactly_before_it_is_revoked(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False],
                         ('shop_db', 'shop_user', '127.0.0.1'): ['ALL PRIVILEGES', False]})
        result = repair(server, ['shop_db'])
        self.assertEqual([
            ('GRANT ALL PRIVILEGES ON `shop\\_db`.* TO %s@%s', ('shop_user', '127.0.0.1')),
            ('REVOKE ALL PRIVILEGES ON `shop_db`.* FROM %s@%s', ('shop_user', '127.0.0.1')),
            ('GRANT ALL PRIVILEGES ON `shop\\_db`.* TO %s@%s', ('shop_user', 'localhost')),
            ('REVOKE ALL PRIVILEGES ON `shop_db`.* FROM %s@%s', ('shop_user', 'localhost')),
        ], server.changes())
        self.assertEqual({('shop\\_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False],
                          ('shop\\_db', 'shop_user', '127.0.0.1'): ['ALL PRIVILEGES', False]}, server.grants)
        self.assertEqual([['shop_db', 'shop_user', '127.0.0.1'], ['shop_db', 'shop_user', 'localhost']],
                         result['moved'])
        self.assertEqual(([], []), (result['failed'], result['patterns']))
        # The owner held at least one grant on its database after every single statement.
        self.assertEqual({('shop_user', 'localhost'): 1, ('shop_user', '127.0.0.1'): 1}, server.lowest_cover)

    def test_privilege_list_and_grant_option_are_kept(self):
        listed = 'SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER'
        server = Server({('shop_db', 'limited', 'localhost'): [listed, False],
                         ('shop_db', 'delegate', '%'): ['ALL PRIVILEGES', True]})
        repair(server, ['shop_db'])
        self.assertEqual([
            ('GRANT ALL PRIVILEGES ON `shop\\_db`.* TO %s@%s WITH GRANT OPTION', ('delegate', '%')),
            ('REVOKE ALL PRIVILEGES ON `shop_db`.* FROM %s@%s', ('delegate', '%')),
            ('REVOKE GRANT OPTION ON `shop_db`.* FROM %s@%s', ('delegate', '%')),
            ('GRANT %s ON `shop\\_db`.* TO %%s@%%s' % listed, ('limited', 'localhost')),
            ('REVOKE %s ON `shop_db`.* FROM %%s@%%s' % listed, ('limited', 'localhost')),
        ], server.changes())
        self.assertEqual({('shop\\_db', 'limited', 'localhost'): [listed, False],
                          ('shop\\_db', 'delegate', '%'): ['ALL PRIVILEGES', True]}, server.grants)

    def test_exact_grants_and_names_without_wildcards_are_left_alone(self):
        grants = {('shop\\_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False],
                  ('plain', 'plainuser', 'localhost'): ['ALL PRIVILEGES', False]}
        server = Server(grants)
        result = repair(server, ['shop_db', 'plain'])
        self.assertEqual([], server.changes())
        self.assertEqual(grants, server.grants)
        self.assertEqual({'literal': False, 'moved': [], 'failed': [], 'patterns': []}, result)
        self.assertEqual(["SHOW VARIABLES LIKE 'partial_revokes'", 'SELECT @@lower_case_table_names',
                          'SELECT Db, User, Host FROM mysql.db ORDER BY Db, User, Host'],
                         [query for query, args in server.statements])

    def test_pattern_that_is_not_a_registered_database_is_listed_and_kept(self):
        grants = {('__________', 'someone', 'localhost'): ['ALL PRIVILEGES', False],
                  ('shop%', 'agency', '%'): ['SELECT', False],
                  ('test\\_%', '', '%'): ['ALL PRIVILEGES', False]}
        server = Server(grants, schemas=['cyberpanel', 'mysql', 'shop_db', 'information_schema'])
        result = repair(server, ['shop_db', 'shop_two'])
        self.assertEqual([], server.changes())
        self.assertEqual(grants, server.grants)
        self.assertEqual([['__________', 'someone', 'localhost', ['cyberpanel']],
                          ['shop%', 'agency', '%', ['shop_db', 'shop_two']],
                          ['test\\_%', '', '%', []]], result['patterns'])
        self.assertEqual([], result['moved'])

    def test_grant_the_server_does_not_show_is_reported_and_not_revoked(self):
        server = Server({('shop_db', 'ghost', 'localhost'): ['ALL PRIVILEGES', False],
                         ('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]},
                        hidden=[('shop_db', 'ghost', 'localhost')])
        result = repair(server, ['shop_db'])
        self.assertEqual([['shop_db', 'ghost', 'localhost', 'RepairError: the server does not show this grant']],
                         result['failed'])
        self.assertEqual([['shop_db', 'shop_user', 'localhost']], result['moved'])
        self.assertIn(('shop_db', 'ghost', 'localhost'), server.grants)
        self.assertNotIn(('ghost', 'localhost'), [args for query, args in server.changes()])

    def test_unusual_privilege_text_is_never_put_into_a_statement(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['SELECT (id), INSERT', False]})
        result = repair(server, ['shop_db'])
        self.assertEqual([], server.changes())
        self.assertEqual(1, len(result['failed']))

    def test_refused_grant_leaves_the_plain_grant_in_place(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]}, refuse='GRANT')
        result = repair(server, ['shop_db'])
        self.assertEqual({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]}, server.grants)
        self.assertEqual([['shop_db', 'shop_user', 'localhost', 'RuntimeError: refused by the server']],
                         result['failed'])
        self.assertEqual([], [query for query, args in server.changes() if query.startswith('REVOKE')])

    def test_refused_revoke_is_reported_and_access_stays(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]}, refuse='REVOKE')
        result = repair(server, ['shop_db'])
        self.assertEqual(1, len(result['failed']))
        self.assertEqual([], result['moved'])
        self.assertEqual({('shop_db', 'shop_user', 'localhost'), ('shop\\_db', 'shop_user', 'localhost')},
                         set(server.grants))

    def test_plain_grant_that_survives_the_revoke_is_reported(self):
        key = ('shop_db', 'shop_user', 'localhost')
        server = Server({key: ['ALL PRIVILEGES', False]}, stuck=[key])
        result = repair(server, ['shop_db'])
        self.assertEqual([['shop_db', 'shop_user', 'localhost',
                           'RepairError: the plain grant is still there after the revoke']], result['failed'])

    def test_server_that_reads_names_literally_is_left_alone(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]}, literal=True)
        result = repair(server, ['shop_db'])
        self.assertEqual({'literal': True, 'moved': [], 'failed': [], 'patterns': []}, result)
        self.assertEqual([("SHOW VARIABLES LIKE 'partial_revokes'", None)], server.statements)

    def test_database_name_is_quoted_in_both_statements(self):
        server = Server({('odd`_name', 'odd', 'localhost'): ['ALL PRIVILEGES', False]})
        repair(server, ['odd`_name'])
        self.assertEqual([('GRANT ALL PRIVILEGES ON `odd``\\_name`.* TO %s@%s', ('odd', 'localhost')),
                          ('REVOKE ALL PRIVILEGES ON `odd``_name`.* FROM %s@%s', ('odd', 'localhost'))],
                         server.changes())

    def test_grant_line_is_read_in_the_forms_servers_write(self):
        for line, expected in (
                ("GRANT ALL PRIVILEGES ON `a_b`.* TO `u`@`localhost`", ('ALL PRIVILEGES', 'a_b', None)),
                ("GRANT ALL PRIVILEGES ON `a_b`.* TO 'u'@'localhost'", ('ALL PRIVILEGES', 'a_b', None)),
                ("GRANT SELECT, LOCK TABLES ON `a_b`.* TO `u`@`%` WITH GRANT OPTION",
                 ('SELECT, LOCK TABLES', 'a_b', ' WITH GRANT OPTION')),
                ("GRANT ALL PRIVILEGES ON `a\\_b`.* TO `u`@`localhost`", ('ALL PRIVILEGES', 'a\\_b', None))):
            self.assertEqual(expected, databaseGrantRepair.GRANT_LINE.fullmatch(line).groups(), line)
        for line in ("GRANT USAGE ON *.* TO `u`@`localhost` IDENTIFIED BY PASSWORD '*00'",
                     "GRANT SELECT ON `a_b`.`t` TO `u`@`localhost`",
                     "GRANT SELECT (id) ON `a_b`.* TO `u`@`localhost`",
                     "GRANT ALL PRIVILEGES ON *.* TO `root`@`localhost` WITH GRANT OPTION"):
            self.assertIsNone(databaseGrantRepair.GRANT_LINE.fullmatch(line), line)


class OtherHoldersTests(unittest.TestCase):
    def test_every_account_holding_the_plain_grant_is_moved(self):
        # The database's user at each host, a panel user's phpMyAdmin account and a remote-access account.
        holders = [('shop_user', 'localhost'), ('shop_user', '127.0.0.1'), ('shop_user', '203.0.113.9'),
                   ('reseller', 'localhost')]
        server = Server(dict((('shop_db',) + holder, ['ALL PRIVILEGES', False]) for holder in holders))
        result = repair(server, ['shop_db'])
        self.assertEqual(set(('shop\\_db',) + holder for holder in holders), set(server.grants))
        self.assertEqual(4, len(result['moved']))
        self.assertEqual([], result['failed'])

    def test_role_is_named_without_a_host(self):
        server = Server({('shop_db', 'readers', ''): ['SELECT', False]})
        result = repair(server, ['shop_db'])
        self.assertEqual([('GRANT SELECT ON `shop\\_db`.* TO %s', ('readers',)),
                          ('REVOKE SELECT ON `shop_db`.* FROM %s', ('readers',))], server.changes())
        self.assertEqual([['shop_db', 'readers', '']], result['moved'])

    def test_second_run_changes_nothing(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', True]})
        repair(server, ['shop_db'])
        after = dict(server.grants)
        first = len(server.changes())
        result = repair(server, ['shop_db'])
        self.assertEqual(first, len(server.changes()))
        self.assertEqual(after, server.grants)
        self.assertEqual({'literal': False, 'moved': [], 'failed': [], 'patterns': []}, result)

    def test_exact_grant_that_is_already_there_is_kept_when_the_plain_one_goes(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['SELECT', False],
                         ('shop\\_db', 'shop_user', 'localhost'): ['SELECT', False]})
        result = repair(server, ['shop_db'])
        self.assertEqual({('shop\\_db', 'shop_user', 'localhost'): ['SELECT', False]}, server.grants)
        self.assertEqual([['shop_db', 'shop_user', 'localhost']], result['moved'])

    def test_plain_grant_stays_when_the_exact_one_was_not_stored(self):
        key = ('shop_db', 'shop_user', 'localhost')
        server = Server({key: ['ALL PRIVILEGES', False]}, unstored=True)
        result = repair(server, ['shop_db'])
        self.assertEqual({key: ['ALL PRIVILEGES', False]}, server.grants)
        self.assertEqual([list(key) + ['RepairError: the exact grant was not stored']], result['failed'])
        self.assertEqual([], [query for query, args in server.changes() if query.startswith('REVOKE')])

    def test_server_that_folds_names_stores_the_grant_in_lower_case(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]}, folds=1)
        result = repair(server, ['Shop_DB'])
        self.assertEqual({('shop\\_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]}, server.grants)
        self.assertEqual([], result['patterns'])
        # Without folding the same row belongs to nobody the panel knows.
        server = Server({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]}, schemas=['shop_db'])
        result = repair(server, ['Shop_DB'])
        self.assertEqual([], server.changes())
        self.assertEqual(1, len(result['patterns']))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.log = []
        self.connection = mock.Mock()

    def run_with(self, server):
        with mock.patch.object(databaseGrantRepair, 'panel_database', return_value='cyberpanel'):
            return databaseGrantRepair.run(lambda: (self.connection, server), self.log.append)

    def test_registered_names_come_from_the_panel_database(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]}, registered=['shop_db'])
        self.assertEqual('repaired', self.run_with(server))
        self.assertIn(('SELECT dbName FROM `cyberpanel`.databases_databases', None), server.statements)
        self.assertEqual(['Database grants: 1 grant(s) of earlier releases now name their own database only.'],
                         self.log)
        self.connection.close.assert_called_once_with()

    def test_every_run_looks_again(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]}, registered=['shop_db'])
        self.assertEqual('repaired', self.run_with(server))
        self.assertEqual('nothing to change', self.run_with(server))
        server.grants[('shop_db', 'later', 'localhost')] = ['ALL PRIVILEGES', False]
        self.assertEqual('repaired', self.run_with(server))
        self.assertEqual({('shop\\_db', 'shop_user', 'localhost'), ('shop\\_db', 'later', 'localhost')},
                         set(server.grants))

    def test_other_patterns_are_reported(self):
        server = Server({('shop%', 'agency', '%'): ['SELECT', False]}, registered=['shop_db'], schemas=['mysql'])
        self.assertEqual('nothing to change', self.run_with(server))
        self.assertEqual(["NOTICE: The grant on `shop%` for agency@% is a pattern that is not the name of a database "
                          "made in the panel. It was left as it is. It covers: shop_db."], self.log)

    def test_incomplete_run_is_reported(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]}, registered=['shop_db'],
                        refuse='REVOKE')
        self.assertEqual('incomplete', self.run_with(server))
        self.assertEqual(['WARNING: The grant on `shop_db` for shop_user@localhost still covers similarly named '
                          'databases (RuntimeError: refused by the server).'], self.log)
        self.connection.close.assert_called_once_with()

    def test_no_connection_changes_nothing(self):
        self.assertEqual('no connection', databaseGrantRepair.run(lambda: (0, 0), self.log.append))
        self.assertEqual(1, len(self.log))

    def test_unreadable_registration_closes_the_connection_and_changes_nothing(self):
        server = Server({('shop_db', 'shop_user', 'localhost'): ['ALL PRIVILEGES', False]}, refuse='SELECT dbName')
        with self.assertRaises(RuntimeError):
            self.run_with(server)
        self.assertEqual([], server.changes())
        self.connection.close.assert_called_once_with()

    def test_long_cover_list_is_shortened(self):
        covered = ['db%02d' % number for number in range(15)]
        databaseGrantRepair.describe({'literal': False, 'moved': [], 'failed': [],
                                      'patterns': [['db%', '', 'localhost', covered]]}, self.log.append)
        self.assertIn("for ''@localhost", self.log[0])
        self.assertTrue(self.log[0].endswith('db11 and 3 more.'))


class CallSiteTests(unittest.TestCase):
    def test_upgrader_runs_the_repair_and_can_not_fail_on_it(self):
        upgrader = (ROOT / 'plogical' / 'upgrade.py').read_text()
        start = upgrader.index('    def repairDatabaseGrants():')
        method = upgrader[start:upgrader.index('    @staticmethod', start)]
        self.assertIn('from plogical.databaseGrantRepair import run as repair_database_grants', method)
        self.assertIn('connect=Upgrade.setupConnection, log=Upgrade.stdOut', method)
        self.assertIn("except Exception as error:\n            Upgrade.stdOut('WARNING: Database grants were not "
                      "checked: ' + str(error), 0)", method)
        self.assertLess(method.index('        try:'), method.index('from plogical.databaseGrantRepair'))
        # Called once in the upgrade itself, after the new source is in place and the server answers.
        call = '\n        Upgrade.repairDatabaseGrants()\n'
        self.assertEqual(1, upgrader.count(call))
        self.assertLess(upgrader.index('if Upgrade.waitForDatabaseReady() != 1:'), upgrader.index(call))
        self.assertLess(upgrader.index('Upgrade.downloadAndUpgrade('), upgrader.index(call))

    def test_upgrade_started_from_the_cloud_platform_runs_it_too(self):
        cloud = (ROOT / 'plogical' / 'CyberPanelUpgrade.py').read_text()
        call = '\n        Upgrade.repairDatabaseGrants()\n'
        self.assertEqual(1, cloud.count(call))
        self.assertLess(cloud.index('Upgrade.downloadAndUpgrade('), cloud.index(call))

    def test_helper_does_not_need_the_panel_models(self):
        source = (ROOT / 'plogical' / 'databaseGrantRepair.py').read_text()
        self.assertNotIn('django', source)
        self.assertEqual('`odd``name`', databaseGrantRepair.quote('odd`name'))
        self.assertTrue(databaseGrants.is_pattern('shop_db'))


if __name__ == '__main__':
    unittest.main()
