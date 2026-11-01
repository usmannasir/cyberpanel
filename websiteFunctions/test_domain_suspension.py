"""Run the actual status/action methods with inert permission/worker boundaries."""
import ast
import json
from pathlib import Path
import shlex
from types import SimpleNamespace
import unittest
from unittest import mock

from websiteFunctions.test_wordpress_entitlements import load_wordpress_manager, Response


class DomainSuspensionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.ns, self.services = load_wordpress_manager()
        self.ns['ChildDomains'] = self.children = mock.Mock()
        self.acl = self.services['ACLManager']
        self.acl.loadedACL.return_value = {'admin': 0}
        self.acl.currentContextPermission.return_value = 1
        self.acl.checkOwnership.return_value = 1
        self.acl.loadErrorJson.return_value = Response(json.dumps({'websiteStatus': 0}))
        self.admin = SimpleNamespace(pk=7)
        self.services['Administrator'].objects.get.return_value = self.admin
        self.services['virtualHostUtilities'].cyberPanel = '/usr/local/CyberCP'
        self.parent = SimpleNamespace(domain='parent.test', state=1)
        self.child = SimpleNamespace(domain='child.test', state=1, master=self.parent)
        self.children.objects.filter.return_value.select_related.return_value.first.return_value = self.child
        self.data = {'websiteName': 'child.test', 'state': 'Suspend'}

    def payload(self, response):
        return json.loads(response.content)

    def test_child_action_reaches_worker_with_exact_owner_domain_and_action(self):
        worker_result = {'websiteStatus': 1, 'state': 'Suspended', 'error_message': 'None',
                         'independentState': 0, 'parentSuspended': False}
        self.services['ProcessUtilities'].outputExecutioner.return_value = (1, json.dumps(worker_result))
        result = self.manager().submitWebsiteStatus(7, self.data)
        self.assertEqual(self.payload(result), worker_result)
        self.acl.checkOwnership.assert_called_once_with('child.test', self.admin, {'admin': 0})
        call = self.services['ProcessUtilities'].outputExecutioner.call_args
        self.assertEqual(shlex.split(call.args[0]), [
            '/usr/local/CyberCP/bin/python', '/usr/local/CyberCP/plogical/websiteSuspension.py',
            '--user-id', '7', '--domain', 'child.test', '--action', 'Suspend'])
        self.assertTrue(call.kwargs['retRequired'])

    def test_acl_denial_prevents_all_worker_and_domain_queries(self):
        self.acl.currentContextPermission.return_value = 0
        for method in ('submitWebsiteStatus', 'fetchWebsiteStatus'):
            self.assertEqual(self.payload(getattr(self.manager(), method)(7, self.data))['websiteStatus'], 0)
        self.children.assert_not_called()
        self.children.objects.filter.assert_not_called()
        self.services['ProcessUtilities'].outputExecutioner.assert_not_called()

    def test_other_customer_domain_is_rejected_before_worker_or_state_read(self):
        self.acl.checkOwnership.return_value = 0
        for method in ('submitWebsiteStatus', 'fetchWebsiteStatus'):
            self.assertEqual(self.payload(getattr(self.manager(), method)(7, self.data))['websiteStatus'], 0)
        self.children.objects.filter.assert_not_called()
        self.services['ProcessUtilities'].outputExecutioner.assert_not_called()

    def test_invalid_actions_cannot_be_interpreted_as_unsuspend(self):
        for state in ('', 'restore', None, 0, 'Un-Suspend;id'):
            with self.subTest(state=state):
                result = self.manager().submitWebsiteStatus(7, dict(self.data, state=state))
                self.assertEqual(self.payload(result)['websiteStatus'], 0)
        self.services['ProcessUtilities'].outputExecutioner.assert_not_called()

    def test_invalid_domain_is_refused_before_ownership_or_worker(self):
        result = self.manager().submitWebsiteStatus(7, dict(self.data, websiteName='../parent.test'))
        self.assertEqual(self.payload(result)['websiteStatus'], 0)
        self.acl.checkOwnership.assert_not_called()
        self.services['ProcessUtilities'].outputExecutioner.assert_not_called()

    def test_worker_exit_failure_is_not_reported_as_success(self):
        self.services['ProcessUtilities'].outputExecutioner.return_value = (
            0, json.dumps({'websiteStatus': 1, 'error_message': 'activation failed'}))
        self.assertEqual(self.payload(self.manager().submitWebsiteStatus(7, self.data))['websiteStatus'], 0)

    def test_worker_application_failure_and_missing_result_are_reported(self):
        for output in ('', 'not json', json.dumps({'websiteStatus': 0, 'error_message': 'reload failed'})):
            with self.subTest(output=output):
                self.services['ProcessUtilities'].outputExecutioner.return_value = (1, output)
                self.assertEqual(self.payload(self.manager().submitWebsiteStatus(7, self.data))['websiteStatus'], 0)

    def test_effective_status_covers_independent_and_inherited_suspension(self):
        for parent_state, child_state, effective in ((1, 1, 'Active'), (1, 0, 'Suspended'),
                                                      (0, 1, 'Suspended'), (0, 0, 'Suspended')):
            with self.subTest(parent=parent_state, child=child_state):
                self.parent.state, self.child.state = parent_state, child_state
                result = self.payload(self.manager().fetchWebsiteStatus(7, self.data))
                self.assertEqual(result['state'], effective)
                self.assertEqual(result['parentSuspended'], not bool(parent_state))
                self.assertEqual(result['independentState'], child_state)

    def test_main_site_status_uses_its_own_state(self):
        self.children.objects.filter.return_value.select_related.return_value.first.return_value = None
        self.services['Websites'].objects.get.return_value = self.parent
        self.parent.state = 0
        result = self.payload(self.manager().fetchWebsiteStatus(7, {'websiteName': 'parent.test'}))
        self.assertEqual(result['state'], 'Suspended')
        self.assertFalse(result['parentSuspended'])

    def test_selector_uses_existing_owned_site_and_child_scope(self):
        self.manager().siteState(userID=7)
        self.acl.findAllSites.assert_called_once_with({'admin': 0}, 7, fetchChilds=1)


class SuspensionViewTests(unittest.TestCase):
    def setUp(self):
        source = ast.parse((Path(__file__).parent / 'views.py').read_text(encoding='utf-8'))
        source.body = [node for node in source.body if isinstance(node, ast.FunctionDef)
                       and node.name in ('fetchWebsiteStatus', 'submitWebsiteStatus')]
        self.manager = mock.Mock()
        self.plugin = mock.Mock()
        self.plugin.preWebsiteSuspension.return_value = 200
        self.plugin.postWebsiteSuspension.return_value = 200
        self.ns = {'WebsiteManager': self.manager, 'pluginManager': self.plugin,
                   'json': json, 'JsonResponse': lambda data, status=200: Response(json.dumps(data), status),
                   'redirect': lambda value: Response(status=302), 'loadLoginPage': mock.Mock()}
        exec(compile(source, 'views.py', 'exec'), self.ns)

    def test_get_cannot_change_or_read_domain_state(self):
        request = SimpleNamespace(method='GET', session={'userID': 7}, body=b'{}')
        for name in ('fetchWebsiteStatus', 'submitWebsiteStatus'):
            self.assertEqual(self.ns[name](request).status_code, 405)
        self.manager.assert_not_called()
        self.plugin.assert_not_called()

    def test_anonymous_post_redirects_before_manager_or_plugins(self):
        request = SimpleNamespace(method='POST', session={}, body=b'{}')
        for name in ('fetchWebsiteStatus', 'submitWebsiteStatus'):
            self.assertEqual(self.ns[name](request).status_code, 302)
        self.manager.assert_not_called()
        self.plugin.assert_not_called()

    def test_submit_retains_both_existing_plugin_hooks(self):
        data = {'websiteName': 'child.test', 'state': 'Suspend'}
        request = SimpleNamespace(method='POST', session={'userID': 7}, body=json.dumps(data).encode())
        result = self.ns['submitWebsiteStatus'](request)
        self.manager.return_value.submitWebsiteStatus.assert_called_once_with(7, data)
        self.plugin.preWebsiteSuspension.assert_called_once_with(request)
        self.plugin.postWebsiteSuspension.assert_called_once_with(request, result)

    def test_malformed_json_is_rejected_before_plugins_or_manager(self):
        request = SimpleNamespace(method='POST', session={'userID': 7}, body=b'{')
        for name in ('fetchWebsiteStatus', 'submitWebsiteStatus'):
            self.assertEqual(self.ns[name](request).status_code, 400)
        self.manager.assert_not_called()
        self.plugin.assert_not_called()


if __name__ == '__main__':
    unittest.main()
