"""WordPress tools: names from the request are plain names, and backup destinations have an owner."""
import json
from types import SimpleNamespace
import unittest

from plogical.wordpressInstallerUtilities import wordpress_item_names
from websiteFunctions.test_wordpress_entitlements import Response, load_wordpress_manager

OTHER_NAMES = ('akismet --allow-root', 'a;b', 'a b', '$(id)', '`id`', '../x', 'a/b', '', '-x', '.x',
               'x' * 201, {'a': 1}, ['a', {'b': 1}], [['a']], None, 7, True, ['ok', 'not ok'])


class ItemNameTests(unittest.TestCase):
    def test_plugin_and_theme_names_and_lists_of_them_are_accepted(self):
        self.assertTrue(wordpress_item_names('akismet', 'all', 'selected', 'woocommerce-payments',
                                             'twentytwentyfive', 'hello.php', 'wp_mail_smtp', []))
        self.assertTrue(wordpress_item_names('selected', ['akismet', 'jetpack']))
        self.assertTrue(wordpress_item_names())

    def test_anything_else_is_refused(self):
        for value in OTHER_NAMES:
            self.assertFalse(wordpress_item_names(value), repr(value))
            self.assertFalse(wordpress_item_names('akismet', value), repr(value))


class Handlers(unittest.TestCase):
    def setUp(self):
        self.manager, self.ns, self.services = load_wordpress_manager()
        acl = self.services['ACLManager']
        acl.CheckForPremFeature.return_value = 1
        acl.loadedACL.return_value = {'admin': 0}
        acl.checkOwnership.return_value = 1
        acl.getPHPString.return_value = '83'
        acl.loadErrorJson.return_value = Response(json.dumps({'status': 0, 'error_message': 'ACL denied'}))
        acl.loadError.return_value = Response(json.dumps({'status': 0, 'error_message': 'ACL denied'}))
        self.admin = SimpleNamespace(pk=7, userName='customer')
        self.services['Administrator'].objects.get.return_value = self.admin
        site = SimpleNamespace(path='/home/example.com/public_html', owner_id=3,
                               owner=SimpleNamespace(domain='example.com', externalApp='examp1234',
                                                     phpSelection='PHP 8.3'))
        self.services['WPSites'].objects.get.return_value = site
        self.services['Websites'].objects.get.return_value = site.owner
        self.services['ProcessUtilities'].outputExecutioner.return_value = 'Status: Active'

    def call(self, method, data):
        for name in ('ProcessUtilities', 'ApplicationInstaller'):
            self.services[name].reset_mock()
        self.services['ProcessUtilities'].outputExecutioner.return_value = 'Status: Active'
        return json.loads(getattr(self.manager(), method)(7, data).content)


class ItemNameHandlerTests(Handlers):
    FIELDS = {'UpdatePlugins': ('plugin', 'pluginarray'), 'DeletePlugins': ('plugin', 'pluginarray'),
              'UpdateThemes': ('Theme', 'Themearray'), 'DeleteThemes': ('Theme', 'Themearray'),
              'ChangeStatus': ('plugin', None), 'ChangeStatusThemes': ('theme', None)}

    def test_other_values_stop_before_any_command_or_worker(self):
        for method, (name, array) in self.FIELDS.items():
            for value in OTHER_NAMES:
                for data in ({'WPid': 1, name: value, array: []},
                             {'WPid': 1, name: 'selected', array: value if isinstance(value, list) else [value]}):
                    if array is None:
                        data.pop(None)
                        if data[name] == 'selected':
                            continue
                    result = self.call(method, data)
                    self.assertEqual(0, result['status'], (method, data))
                    self.services['ProcessUtilities'].outputExecutioner.assert_not_called()
                    self.services['ApplicationInstaller'].assert_not_called()

    def test_plain_names_still_reach_the_tools(self):
        self.assertEqual(1, self.call('ChangeStatus', {'WPid': 1, 'plugin': 'akismet'})['status'])
        commands = [call.args[0] for call in self.services['ProcessUtilities'].outputExecutioner.call_args_list]
        self.assertIn(' /usr/bin/wp plugin status akismet ', commands[0])
        self.call('UpdatePlugins', {'WPid': 1, 'plugin': 'selected', 'pluginarray': ['akismet', 'jetpack']})
        arguments = self.services['ApplicationInstaller'].call_args.args[1]
        self.assertEqual(('selected', ['akismet', 'jetpack']), (arguments['plugin'], arguments['pluginarray']))

    def test_search_visibility_is_written_as_zero_or_one(self):
        for value, expected in ((1, '1'), ('1', '1'), (True, '1'), (0, '0'), ('0 --allow-root', '0'),
                                ({'a': '$(id)'}, '0'), (['1'], '0')):
            self.call('UpdateWPSettings', {'siteId': 1, 'setting': 'search-indexing', 'value': value})
            calls = self.services['ProcessUtilities'].outputExecutioner.call_args_list
            calls = calls or self.services['ProcessUtilities'].executioner.call_args_list
            command = calls[0].args[0]
            self.assertIn(' /usr/bin/wp option update blog_public %s --skip-plugins ' % expected, command, value)


class RemoteBackupOwnerTests(Handlers):
    def owned(self):
        return self.manager.ownedRemoteBackupConfigs

    def test_customer_sees_only_destinations_they_created(self):
        configs = self.services['RemoteBackupConfig']
        self.assertIs(configs.objects.filter.return_value, self.owned()(self.admin, {'admin': 0}))
        configs.objects.filter.assert_called_once_with(owner=self.admin)
        self.assertIs(configs.objects.filter.return_value, self.owned()(self.admin, {}))
        self.assertIs(configs.objects.all.return_value, self.owned()(self.admin, {'admin': 1}))

    def test_site_is_added_only_by_its_owner_and_only_to_an_owned_schedule(self):
        acl = self.services['ACLManager']
        schedules = self.services['RemoteBackupSchedule']
        acl.checkOwnership.return_value = 0
        result = self.call('AddWPsiteforRemoteBackup', {'WpsiteID': 5, 'RemoteScheduleID': 9})
        self.assertEqual(0, result['status'])
        schedules.objects.get.assert_not_called()
        self.services['RemoteBackupsites'].assert_not_called()
        self.services['ProcessUtilities'].outputExecutioner.assert_not_called()

        acl.checkOwnership.return_value = 1
        schedules.objects.get.side_effect = LookupError('RemoteBackupSchedule matching query does not exist.')
        result = self.call('AddWPsiteforRemoteBackup', {'WpsiteID': 5, 'RemoteScheduleID': 9})
        self.assertEqual(0, result['status'])
        self.services['RemoteBackupsites'].assert_not_called()
        lookup = schedules.objects.get.call_args.kwargs
        self.assertEqual(9, lookup['pk'])
        self.assertIs(self.services['RemoteBackupConfig'].objects.filter.return_value,
                      lookup['RemoteBackupConfig__in'])

    def test_schedules_are_created_and_changed_only_under_owned_destinations(self):
        configs = self.services['RemoteBackupConfig']
        configs.objects.filter.return_value.get.side_effect = LookupError('not yours')
        result = self.call('SaveBackupSchedule', {'FileRetention': '3', 'Backfrequency': 'Daily',
                                                  'ScheduleName': 'x', 'RemoteConfigID': 4, 'BackupType': 'Full'})
        self.assertEqual(0, result['status'])
        configs.objects.filter.return_value.get.assert_called_once_with(pk=4)
        self.services['RemoteBackupSchedule'].assert_not_called()

        schedules = self.services['RemoteBackupSchedule']
        schedules.objects.get.side_effect = LookupError('not yours')
        result = self.call('UpdateRemoteschedules', {'ScheduleID': 2, 'Frequency': 'Daily', 'FileRetention': '3'})
        self.assertEqual(0, result['status'])
        self.assertIn('RemoteBackupConfig__in', schedules.objects.get.call_args.kwargs)

    def test_no_handler_looks_up_a_destination_or_schedule_by_number_alone(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / 'websiteFunctions/website.py').read_text()
        self.assertNotIn('RemoteBackupConfig.objects.get(', source)
        self.assertNotIn('RemoteBackupSchedule.objects.get(pk=', source)
        self.assertNotIn('RemoteBackupsites.objects.get(pk=DeleteSiteID)', source)


if __name__ == '__main__':
    unittest.main()
