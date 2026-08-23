import json
import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

from plogical.upgrade import Upgrade


class UpgradeDatabaseAccessTests(unittest.TestCase):

    def setUp(self):
        self.database_settings = {
            'default': {
                'NAME': 'cyberpanel',
                'USER': 'cyberpanel',
                'PASSWORD': 'database-password',
                'HOST': '198.51.100.42',
            },
        }

    @patch('plogical.upgrade.os._exit')
    def test_fatal_upgrade_message_exits_nonzero(self, exit_process):
        original_log_path = Upgrade.LogPathNew
        original_soft_upgrade = Upgrade.SoftUpgrade
        original_from_cloud = Upgrade.FromCloud

        with tempfile.NamedTemporaryFile() as log_file:
            try:
                Upgrade.LogPathNew = log_file.name
                Upgrade.SoftUpgrade = 0
                Upgrade.FromCloud = 0
                Upgrade.stdOut('fatal upgrade error', 1)
            finally:
                Upgrade.LogPathNew = original_log_path
                Upgrade.SoftUpgrade = original_soft_upgrade
                Upgrade.FromCloud = original_from_cloud

        exit_process.assert_called_once_with(1)

    @patch('plogical.upgrade.mysql.connect')
    def test_remote_admin_connection_uses_configured_host_and_port(self, connect):
        connection = MagicMock()
        connect.return_value = connection
        password_file = json.dumps({
            'mysqlhost': 'database.example',
            'mysqlport': '3307',
            'mysqluser': 'remote-admin',
            'mysqlpassword': "strong $pass;'word",
        })

        with patch('builtins.open', mock_open(read_data=password_file)):
            returned_connection, returned_cursor = Upgrade.setupConnection()

        connect.assert_called_once_with(
            host='database.example',
            port=3307,
            user='remote-admin',
            passwd="strong $pass;'word",
        )
        self.assertIs(connection, returned_connection)
        self.assertIs(connection.cursor.return_value, returned_cursor)

    @patch('plogical.upgrade.mysql.connect')
    def test_remote_admin_connection_selects_requested_database(self, connect):
        connection = MagicMock()
        connect.return_value = connection
        password_file = json.dumps({
            'mysqlhost': 'database.example',
            'mysqlport': 3307,
            'mysqluser': 'remote-admin',
            'mysqlpassword': 'database-password',
        })

        with patch('builtins.open', mock_open(read_data=password_file)):
            Upgrade.setupConnection('cyberpanel')

        connect.assert_called_once_with(
            host='database.example',
            port=3307,
            user='remote-admin',
            passwd='database-password',
            db='cyberpanel',
        )

    @patch('plogical.upgrade.mysql.connect')
    def test_plaintext_password_keeps_legacy_local_connection(self, connect):
        connection = MagicMock()
        connect.return_value = connection

        with patch('builtins.open', mock_open(read_data='local-password\n')):
            Upgrade.setupConnection()

        connect.assert_called_once_with(
            user='root',
            passwd='local-password',
        )

    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.upgrade.Upgrade.getMachineIP', return_value='198.51.100.42')
    @patch('plogical.upgrade.settings')
    @patch('plogical.upgrade.Upgrade.setupConnection')
    def test_repairs_missing_account_for_the_machine_ip(
            self, setup_connection, settings, get_machine_ip, std_out):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        setup_connection.return_value = connection, cursor
        settings.DATABASES = self.database_settings

        self.assertEqual(1, Upgrade.repairLocalCyberPanelDatabaseAccess())

        queries = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertIn('CREATE USER %s@%s IDENTIFIED BY %s', queries)
        self.assertIn('GRANT ALL PRIVILEGES ON `cyberpanel`.* TO %s@%s', queries)
        self.assertNotIn("'%'", '\n'.join(queries))
        connection.close.assert_called_once_with()

    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.upgrade.Upgrade.getMachineIP', return_value='198.51.100.42')
    @patch('plogical.upgrade.settings')
    @patch('plogical.upgrade.Upgrade.setupConnection')
    def test_remote_database_is_not_modified(
            self, setup_connection, settings, get_machine_ip, std_out):
        self.database_settings['default']['HOST'] = 'database.example'
        settings.DATABASES = self.database_settings

        self.assertEqual(0, Upgrade.repairLocalCyberPanelDatabaseAccess())
        setup_connection.assert_not_called()

    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.upgrade.Upgrade.getMachineIP', return_value='198.51.100.42')
    @patch('plogical.upgrade.settings')
    @patch('plogical.upgrade.Upgrade.setupConnection')
    def test_existing_account_password_is_repaired(
            self, setup_connection, settings, get_machine_ip, std_out):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        setup_connection.return_value = connection, cursor
        settings.DATABASES = self.database_settings

        self.assertEqual(1, Upgrade.repairLocalCyberPanelDatabaseAccess())

        queries = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertNotIn('CREATE USER %s@%s IDENTIFIED BY %s', queries)
        self.assertIn('ALTER USER %s@%s IDENTIFIED BY %s', queries)
        self.assertIn('GRANT ALL PRIVILEGES ON `cyberpanel`.* TO %s@%s', queries)

    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.upgrade.Upgrade.getMachineIP', return_value='198.51.100.42')
    @patch('plogical.upgrade.settings')
    @patch('plogical.upgrade.Upgrade.setupConnection')
    def test_repairs_socket_and_loopback_accounts(
            self, setup_connection, settings, get_machine_ip, std_out):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(1,), None]
        setup_connection.return_value = connection, cursor
        self.database_settings['default']['HOST'] = 'localhost'
        settings.DATABASES = self.database_settings

        self.assertEqual(1, Upgrade.repairLocalCyberPanelDatabaseAccess())

        calls = cursor.execute.call_args_list
        self.assertIn(
            ('ALTER USER %s@%s IDENTIFIED BY %s',
             ('cyberpanel', 'localhost', 'database-password')),
            [(call.args[0], call.args[1]) for call in calls
             if len(call.args) > 1],
        )
        self.assertIn(
            ('CREATE USER %s@%s IDENTIFIED BY %s',
             ('cyberpanel', '127.0.0.1', 'database-password')),
            [(call.args[0], call.args[1]) for call in calls
             if len(call.args) > 1],
        )

    @patch('plogical.upgrade.time.sleep')
    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.upgrade.Upgrade.setupConnection')
    def test_database_readiness_retries_transient_failure(
            self, setup_connection, std_out, sleep):
        connection = MagicMock()
        cursor = MagicMock()
        setup_connection.side_effect = [(0, 0), (connection, cursor)]

        self.assertEqual(1, Upgrade.waitForDatabaseReady(attempts=3, delay=2))

        self.assertEqual(2, setup_connection.call_count)
        sleep.assert_called_once_with(2)
        cursor.execute.assert_called_once_with('SELECT 1')
        cursor.fetchone.assert_called_once_with()
        cursor.close.assert_called_once_with()
        connection.close.assert_called_once_with()

    @patch('plogical.upgrade.time.sleep')
    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.upgrade.Upgrade.setupConnection', return_value=(0, 0))
    def test_database_readiness_fails_after_bounded_retries(
            self, setup_connection, std_out, sleep):
        self.assertEqual(0, Upgrade.waitForDatabaseReady(attempts=3, delay=2))

        self.assertEqual(3, setup_connection.call_count)
        self.assertEqual(2, sleep.call_count)
        self.assertIn(
            unittest.mock.call(
                'MariaDB did not become ready; post-upgrade migrations were not run.',
                0,
            ),
            std_out.call_args_list,
        )

    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.securityUtils.ensure_api_token', side_effect=(True, False))
    @patch('loginSystem.models.Administrator.objects.exclude')
    @patch('django.setup')
    def test_upgrade_rotates_enabled_accounts_with_invalid_tokens(
            self, django_setup, exclude, ensure_api_token, std_out):
        invalid_account = MagicMock()
        valid_account = MagicMock()
        exclude.return_value.only.return_value = [invalid_account, valid_account]

        Upgrade.rotateInvalidAPITokens()

        exclude.assert_called_once_with(api=0)
        exclude.return_value.only.assert_called_once_with('id', 'token')
        self.assertEqual(
            [invalid_account, valid_account],
            [call.args[0] for call in ensure_api_token.call_args_list],
        )
        std_out.assert_called_once_with('Rotated 1 invalid API access token(s).', 0)


if __name__ == '__main__':
    unittest.main()
