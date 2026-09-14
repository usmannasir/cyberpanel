import json
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from serverStatus import views
from plogical import processUtilities


class ServiceActionTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        unchecked = mock.patch.object(views.ProcessUtilities, 'executioner', return_value=0)
        unchecked.start()
        self.addCleanup(unchecked.stop)

    def request(self, service='lsws', action='start', logged_in=True):
        request = self.factory.post(
            '/serverstatus/servicesAction',
            json.dumps({'service': service, 'action': action}),
            content_type='application/json',
        )
        request.session = {'userID': 7} if logged_in else {}
        return request

    def test_failed_command_is_reported_as_failure(self):
        for result in ((0, 'fixture failure'), None):
            with self.subTest(result=result), \
                    mock.patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}), \
                    mock.patch.object(views.ProcessUtilities, 'outputExecutioner', return_value=result) as execute:
                response = json.loads(views.servicesAction(self.request()).content)
                self.assertEqual(0, response['serviceAction'])
                self.assertIn('Service command failed', response['error_message'])
                execute.assert_called_once_with('sudo systemctl start lsws', shell=False, retRequired=True)

    def test_successful_commands_preserve_response_and_dispatch(self):
        for action in ('start', 'stop', 'restart'):
            with self.subTest(action=action), \
                    mock.patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}), \
                    mock.patch.object(views.ProcessUtilities, 'outputExecutioner', return_value=(1, '')) as execute:
                response = json.loads(views.servicesAction(self.request(action=action)).content)
                self.assertEqual({'serviceAction': 1, 'error_message': 0}, response)
                execute.assert_called_once_with('sudo systemctl %s lsws' % action, shell=False, retRequired=True)

    def test_non_admin_cannot_dispatch_service_command(self):
        with mock.patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 0}), \
                mock.patch.object(views.ProcessUtilities, 'outputExecutioner') as execute:
            response = json.loads(views.servicesAction(self.request()).content)
        self.assertEqual(0, response['serviceAction'])
        execute.assert_not_called()

    def test_missing_session_cannot_dispatch_service_command(self):
        with mock.patch.object(views.ACLManager, 'loadedACL') as acl, \
                mock.patch.object(views.ProcessUtilities, 'outputExecutioner') as execute:
            response = json.loads(views.servicesAction(self.request(logged_in=False)).content)
        self.assertEqual(0, response['serviceAction'])
        acl.assert_not_called()
        execute.assert_not_called()

    def test_invalid_service_cannot_dispatch(self):
        with mock.patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}), \
                mock.patch.object(views.ProcessUtilities, 'outputExecutioner') as execute:
            response = json.loads(views.servicesAction(self.request(service='unlisted')).content)
        self.assertEqual({'serviceAction': 0, 'error_message': 'Invalid Service'}, response)
        execute.assert_not_called()

    def test_invalid_action_cannot_dispatch(self):
        with mock.patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}), \
                mock.patch.object(views.ProcessUtilities, 'outputExecutioner') as execute:
            response = json.loads(views.servicesAction(self.request(action='invalid')).content)
        self.assertEqual({'serviceAction': 0, 'error_message': 'Invalid Action'}, response)
        execute.assert_not_called()

    def test_command_exception_preserves_failure_response(self):
        with mock.patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}), \
                mock.patch.object(views.ProcessUtilities, 'outputExecutioner', side_effect=RuntimeError('fixture command failure')):
            response = json.loads(views.servicesAction(self.request()).content)
        self.assertEqual({'serviceAction': 0, 'error_message': 'fixture command failure'}, response)

    def test_ftp_service_alias_is_preserved(self):
        for debian, expected in ((True, 'pure-ftpd-mysql'), (False, 'pure-ftpd')):
            with self.subTest(debian=debian), \
                    mock.patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}), \
                    mock.patch.object(views.os.path, 'exists', return_value=debian), \
                    mock.patch.object(views.ProcessUtilities, 'outputExecutioner', return_value=(1, '')) as execute:
                response = json.loads(views.servicesAction(self.request(service='pure-ftpd')).content)
                self.assertEqual(1, response['serviceAction'])
                execute.assert_called_once_with('sudo systemctl start ' + expected, shell=False, retRequired=True)

    def test_root_command_exit_status_reaches_endpoint(self):
        for exit_code in (0, 1):
            process = mock.Mock(returncode=exit_code)
            process.communicate.return_value = ('fixture output', None)
            with self.subTest(exit_code=exit_code), \
                    mock.patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}), \
                    mock.patch.object(processUtilities.getpass, 'getuser', return_value='root'), \
                    mock.patch.object(processUtilities.os.path, 'exists', return_value=False), \
                    mock.patch.object(processUtilities.subprocess, 'Popen', return_value=process) as spawn, \
                    mock.patch.object(views.ProcessUtilities, 'executioner', side_effect=AssertionError('unchecked helper used')):
                response = json.loads(views.servicesAction(self.request()).content)
                self.assertEqual(1 if exit_code == 0 else 0, response['serviceAction'])
                self.assertEqual(['sudo', 'systemctl', 'start', 'lsws'], spawn.call_args[0][0])
                self.assertNotIn('shell', spawn.call_args[1])

    def test_socket_command_exit_status_reaches_endpoint(self):
        for exit_code in (0, 1):
            with self.subTest(exit_code=exit_code), \
                    mock.patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}), \
                    mock.patch.object(processUtilities.getpass, 'getuser', return_value='lscpd'), \
                    mock.patch.object(processUtilities.os.path, 'exists', return_value=False), \
                    mock.patch.object(views.ProcessUtilities, 'sendCommand', return_value='fixture output' + chr(exit_code)) as send, \
                    mock.patch.object(views.ProcessUtilities, 'executioner', side_effect=AssertionError('unchecked helper used')):
                response = json.loads(views.servicesAction(self.request()).content)
                self.assertEqual(1 if exit_code == 0 else 0, response['serviceAction'])
                send.assert_called_once_with('sudo systemctl start lsws', None)
