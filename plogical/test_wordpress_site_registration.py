import unittest
from unittest import mock

from plogical.applicationInstaller import ApplicationInstaller


class WordPressSiteRegistrationTests(unittest.TestCase):

    @mock.patch('plogical.applicationInstaller.WPSites')
    def test_new_install_is_registered_for_wordpress_manager(self, wordpress_sites):
        wordpress_sites.objects.filter.return_value.first.return_value = None
        owner = mock.Mock()

        ApplicationInstaller.registerWordPressSite(
            owner,
            'Example site',
            '/home/example.com/public_html/',
            'example.com',
        )

        wordpress_sites.objects.create.assert_called_once_with(
            owner=owner,
            title='Example site',
            path='/home/example.com/public_html/',
            FinalURL='example.com',
            AutoUpdates='Disabled',
            PluginUpdates='Disabled',
            ThemeUpdates='Disabled',
        )

    @mock.patch('plogical.applicationInstaller.WPSites')
    def test_retry_updates_existing_registration_without_a_duplicate(self, wordpress_sites):
        existing = mock.Mock()
        wordpress_sites.objects.filter.return_value.first.return_value = existing

        ApplicationInstaller.registerWordPressSite(
            mock.Mock(),
            'Updated title',
            '/home/example.com/public_html/',
            'example.com',
        )

        wordpress_sites.objects.create.assert_not_called()
        self.assertEqual('Updated title', existing.title)
        self.assertEqual('example.com', existing.FinalURL)
        existing.save.assert_called_once_with(update_fields=['title', 'FinalURL'])

    @mock.patch('plogical.applicationInstaller.WPSites')
    def test_deploy_reuses_the_row_installwordpress_already_created(self, wordpress_sites):
        """DeployWordPress runs installWordPress(), which registers the site first.

        Registering again must update that row with the chosen update policies
        instead of inserting a second row for the same path.
        """
        already_registered = mock.Mock()
        wordpress_sites.objects.filter.return_value.first.return_value = already_registered

        wpobj = ApplicationInstaller.registerWordPressSite(
            mock.Mock(),
            'Example site',
            '/home/example.com/public_html/',
            'example.com',
        )
        wpobj.AutoUpdates = 'All minor and major'
        wpobj.PluginUpdates = 'Enabled'
        wpobj.ThemeUpdates = 'Enabled'
        wpobj.save(update_fields=['AutoUpdates', 'PluginUpdates', 'ThemeUpdates'])

        wordpress_sites.objects.create.assert_not_called()
        self.assertIs(already_registered, wpobj)
        self.assertEqual('All minor and major', already_registered.AutoUpdates)
        self.assertEqual('Enabled', already_registered.PluginUpdates)
        self.assertEqual('Enabled', already_registered.ThemeUpdates)
        already_registered.save.assert_called_with(
            update_fields=['AutoUpdates', 'PluginUpdates', 'ThemeUpdates'],
        )


if __name__ == '__main__':
    unittest.main()
