import json
import os
import unittest
from unittest import mock

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
django.setup()

from websiteFunctions.website import WebsiteManager


class ExistingSiteWordPressInstallTests(unittest.TestCase):

    def test_existing_site_install_passes_validated_wordpress_version(self):
        response = mock.Mock()
        response.json.return_value = {
            'offers': [
                {'current': '7.0.2;id'},
                {'current': '7.0.2'},
            ]
        }
        data = {
            'domain': 'example.com',
            'home': '1',
            'blogTitle': 'Example',
            'adminUser': 'siteadmin',
            'passwordByPass': 'not-a-real-password',
            'adminEmail': 'admin@example.com',
        }

        with mock.patch(
            'websiteFunctions.website.ACLManager.loadedACL',
            return_value={'admin': 1},
        ), mock.patch(
            'websiteFunctions.website.ACLManager.checkOwnership', return_value=1,
        ), mock.patch(
            'websiteFunctions.website.Administrator.objects.get',
            return_value=mock.Mock(pk=1),
        ), mock.patch(
            'websiteFunctions.website.mailUtilities.checkHome',
        ), mock.patch(
            'websiteFunctions.website.requests.get', return_value=response,
        ), mock.patch(
            'websiteFunctions.website.ApplicationInstaller',
        ) as installer, mock.patch(
            'websiteFunctions.website.time.sleep',
        ):
            result = WebsiteManager().installWordpress(userID=1, data=data)

        payload = json.loads(result.content)
        self.assertEqual(1, payload['installStatus'])
        response.raise_for_status.assert_called_once_with()
        install_args = installer.call_args.args[1]
        self.assertEqual('7.0.2', install_args['WPVersion'])
        installer.return_value.start.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
