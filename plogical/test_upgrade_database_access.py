import unittest
from unittest.mock import MagicMock, patch

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
