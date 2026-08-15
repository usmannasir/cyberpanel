import json
import unittest
from types import SimpleNamespace
from unittest import mock

from websiteFunctions.website import WebsiteManager


class SSHPasswordSecurityTests(unittest.TestCase):

    @staticmethod
    def common_patches():
        return (
            mock.patch('websiteFunctions.website.ACLManager.loadedACL', return_value={}),
            mock.patch('websiteFunctions.website.Administrator.objects.get', return_value=SimpleNamespace()),
            mock.patch('websiteFunctions.website.ACLManager.checkOwnership', return_value=1),
            mock.patch(
                'websiteFunctions.website.Websites.objects.get',
                return_value=SimpleNamespace(externalApp='exampleuser'),
            ),
        )

    def test_password_is_not_in_the_privileged_command(self):
        patches = self.common_patches()
        with patches[0], patches[1], patches[2], patches[3], mock.patch(
            'websiteFunctions.website.create_system_password_request',
            return_value='a' * 43,
        ) as create_request, mock.patch(
            'websiteFunctions.website.ProcessUtilities.executioner',
            return_value=1,
        ) as execute:
            response = WebsiteManager().saveSSHAccessChanges(
                1,
                {'domain': 'example.com', 'password': "strong'$(id)-password"},
            )

        result = json.loads(response.content)
        self.assertEqual(1, result['status'])
        create_request.assert_called_once_with('exampleuser', "strong'$(id)-password")
        command = execute.call_args.args[0]
        self.assertIn('changeSystemPassword.py', command)
        self.assertNotIn("strong'$(id)-password", command)

    def test_non_string_password_is_rejected_without_execution(self):
        with mock.patch(
            'websiteFunctions.website.ProcessUtilities.executioner',
        ) as execute:
            response = WebsiteManager().saveSSHAccessChanges(
                1,
                {'domain': 'example.com', 'password': ["value'", '$(id)']},
            )

        result = json.loads(response.content)
        self.assertEqual(0, result['status'])
        execute.assert_not_called()

    def test_failed_privileged_execution_removes_an_unconsumed_request(self):
        patches = self.common_patches()
        with patches[0], patches[1], patches[2], patches[3], mock.patch(
            'websiteFunctions.website.create_system_password_request',
            return_value='a' * 43,
        ), mock.patch(
            'websiteFunctions.website.ProcessUtilities.executioner',
            return_value=0,
        ), mock.patch(
            'websiteFunctions.website.consume_system_password_request',
        ) as consume_request:
            response = WebsiteManager().saveSSHAccessChanges(
                1,
                {'domain': 'example.com', 'password': 'valid-password'},
            )

        result = json.loads(response.content)
        self.assertEqual(0, result['status'])
        consume_request.assert_called_once_with('a' * 43)
