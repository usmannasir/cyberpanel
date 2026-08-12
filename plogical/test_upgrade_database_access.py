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
    def test_existing_account_keeps_its_password(
            self, setup_connection, settings, get_machine_ip, std_out):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        setup_connection.return_value = connection, cursor
        settings.DATABASES = self.database_settings

        self.assertEqual(1, Upgrade.repairLocalCyberPanelDatabaseAccess())

        queries = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertNotIn('CREATE USER %s@%s IDENTIFIED BY %s', queries)
        self.assertIn('GRANT ALL PRIVILEGES ON `cyberpanel`.* TO %s@%s', queries)


if __name__ == '__main__':
    unittest.main()
