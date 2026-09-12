import json
import unittest
from unittest import mock
from django.test import RequestFactory
from plogical.sslOutcome import RESULT_PREFIX, result_payload, parse_output
from manageSSL import views
from plogical.virtualHostUtilities import virtualHostUtilities


class IssuanceOutcomeTests(unittest.TestCase):
    def issue(self, result):
        request = RequestFactory().post('/manageSSL/issueSSL', json.dumps({'virtualHost': 'fixture.example'}), content_type='application/json')
        request.session = {'userID': 7}
        site = mock.Mock(adminEmail='admin@fixture.example')
        with mock.patch.object(views.Administrator.objects, 'get', return_value=mock.Mock()), mock.patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}), mock.patch.object(views.ACLManager, 'checkOwnership', return_value=1), mock.patch.object(views.ChildDomains.objects, 'get', side_effect=views.ChildDomains.DoesNotExist), mock.patch.object(views.Websites.objects, 'get', return_value=site), mock.patch.object(views.ProcessUtilities, 'outputExecutioner', return_value=RESULT_PREFIX + json.dumps(result_payload(result))):
            response = json.loads(views.issueSSL(request).content)
        return response, site

    def test_fresh_and_renewed_success_update_panel(self):
        for outcome in ('issued', 'renewed'):
            response, site = self.issue([1, 'None', {'outcome': outcome}])
            self.assertEqual(1, response['SSL'])
            self.assertEqual(outcome, response['outcome'])
            site.save.assert_called_once()

    def test_fallback_warning_reaches_api_without_new_issue_success(self):
        response, site = self.issue([2, 'Existing date-valid certificate retained.', {'outcome': 'existing_certificate', 'certificate_validity': 'valid', 'retained_existing': True}])
        self.assertEqual(0, response['SSL'])
        self.assertTrue(response['retained_existing'])
        self.assertEqual('valid', response['certificate_validity'])
        self.assertIn('retained', response['warning'])
        site.save.assert_not_called()

    def test_expired_and_failed_results_do_not_update_panel(self):
        response, site = self.issue([0, 'Existing certificate expired.', {'certificate_validity': 'expired'}])
        self.assertEqual(0, response['status'])
        self.assertEqual('expired', response['certificate_validity'])
        site.save.assert_not_called()

    def test_helper_requires_exact_marker_or_final_legacy_token(self):
        for output in ('', 'log says 1,None but failed', '1,None\nfailed', RESULT_PREFIX + '{broken', RESULT_PREFIX + '{"status":1,"SSL":0,"error_message":"None"}'):
            self.assertEqual(0, parse_output(output)['SSL'])
        self.assertEqual(1, parse_output('log\n1,None')['SSL'])

    def test_privileged_wrapper_preserves_fallback_message(self):
        from plogical import virtualHostUtilities as module
        result = [2, 'Existing certificate retained.', {'outcome': 'existing_certificate', 'retained_existing': True}]
        with mock.patch.object(module.sslUtilities, 'issueSSLForDomain', return_value=result), mock.patch.object(module.installUtilities.installUtilities, 'reStartLiteSpeed'), mock.patch.object(module.ProcessUtilities, 'executioner'), mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'), mock.patch('builtins.print') as output:
            self.assertEqual((2, result[1]), virtualHostUtilities.issueSSL('fixture.example', '/fixture', 'admin@fixture.example'))
        text = '\n'.join(call.args[0] for call in output.call_args_list)
        response = parse_output(text)
        self.assertEqual(0, response['SSL'])
        self.assertEqual(result[1], response['warning'])
        self.assertNotIn('1,None', text)

    def test_explicit_hostname_mail_and_alias_actions_do_not_flatten_fallback(self):
        from plogical import virtualHostUtilities as module
        calls = (
            lambda: virtualHostUtilities.issueSSLForHostName('fixture.example', '/fixture'),
            lambda: virtualHostUtilities.issueSSLForMailServer('fixture.example', '/fixture'),
            lambda: virtualHostUtilities.issueAliasSSL('fixture.example', 'alias.example', '/fixture', 'admin@fixture.example'),
        )
        for action in calls:
            with mock.patch.object(module.sslUtilities, 'issueSSLForDomain', return_value=[2, 'Existing certificate retained.']), \
                    mock.patch.object(virtualHostUtilities, 'emailServicesInstalled', return_value=True), \
                    mock.patch.object(module.os.path, 'exists', return_value=True), \
                    mock.patch.object(module.os, 'remove') as remove, \
                    mock.patch.object(module.ProcessUtilities, 'executioner') as execute, \
                    mock.patch.object(module.ProcessUtilities, 'normalExecutioner') as normal_execute, \
                    mock.patch('builtins.print') as output:
                self.assertEqual((2, 'Existing certificate retained.'), action())
            remove.assert_not_called()
            execute.assert_not_called()
            normal_execute.assert_not_called()
            self.assertEqual(['0,Existing certificate retained.'], [call.args[0] for call in output.call_args_list])
