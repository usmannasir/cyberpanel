"""The selected parent reaches the existing authorized domain-creation boundary."""
import json
import shlex
from types import SimpleNamespace
import unittest

from websiteFunctions.test_wordpress_entitlements import load_wordpress_manager, Response


class AddonParentOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.manager, unused_namespace, self.services = load_wordpress_manager()
        self.acl = self.services['ACLManager']
        self.current_acl = {'admin': 0}
        self.admin = SimpleNamespace(pk=7, userName='owner', defaultSite=1)
        self.services['Administrator'].objects.get.return_value = self.admin
        self.acl.loadedACL.return_value = self.current_acl
        self.acl.checkOwnership.side_effect = lambda parent, admin, acl: int(parent == 'zeta.example')
        self.denied = Response(json.dumps({'status': 0, 'createWebSiteStatus': 0}))
        self.acl.loadErrorJson.return_value = self.denied
        self.services['validators'].domain.return_value = True
        self.services['virtualHostUtilities'].cyberPanel = '/usr/local/CyberCP'

    def data(self, parent='zeta.example'):
        return {'masterDomain': parent, 'domainName': 'addon.example',
                'phpSelection': 'PHP 8.3', 'path': 'public_html/addon',
                'openBasedir': 0, 'apacheBackend': 0}

    def test_selected_owned_parent_reaches_worker_without_default_site_substitution(self):
        response = self.manager().submitDomainCreation(7, self.data())
        self.assertEqual(1, json.loads(response.content)['createWebSiteStatus'])
        self.acl.checkOwnership.assert_called_once_with('zeta.example', self.admin, self.current_acl)
        command = shlex.split(self.services['ProcessUtilities'].popenExecutioner.call_args.args[0])
        self.assertEqual('zeta.example', command[command.index('--masterDomain') + 1])
        self.assertEqual('/home/zeta.example/public_html/addon', command[command.index('--path') + 1])
        self.assertEqual('owner', command[command.index('--websiteOwner') + 1])
        self.assertEqual('1', command[command.index('--openBasedir') + 1])
        self.services['Websites'].objects.get.assert_not_called()

    def test_parent_not_owned_by_requesting_user_is_refused_before_worker(self):
        response = self.manager().submitDomainCreation(7, self.data('alpha.example'))
        self.assertIs(self.denied, response)
        self.acl.checkOwnership.assert_called_once_with('alpha.example', self.admin, self.current_acl)
        self.services['ProcessUtilities'].popenExecutioner.assert_not_called()

    def test_empty_parent_is_refused_before_worker(self):
        response = self.manager().submitDomainCreation(7, self.data(''))
        self.assertIs(self.denied, response)
        self.services['ProcessUtilities'].popenExecutioner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
