"""The real page method must not reopen ports or override a stopped service."""
import ast
import ipaddress
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


class TerminalPagePolicyTests(unittest.TestCase):
    def page(self, service_status='active', owns=True, entitlement=1):
        tree = ast.parse((ROOT/'websiteFunctions/website.py').read_text())
        cls = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name == 'WebsiteManager')
        method = next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name == 'sshAccess')
        method.decorator_list = []
        acl, admins, sites, process = Mock(), Mock(), Mock(), Mock()
        acl.checkOwnership.return_value = 1 if owns else 0
        acl.GetServerIP.return_value = '192.0.2.4'
        acl.loadError.return_value = 'denied'
        sites.objects.get.return_value = SimpleNamespace(externalApp='owneduser')
        process.decideServer.return_value = 0
        process.ent = 1
        def command(value):
            if value == 'systemctl is-active fastapi_ssh_server':
                if isinstance(service_status,Exception): raise service_status
                return service_status
            if value == 'cat /usr/local/lscp/conf/cert.pem': return 'inert certificate'
            raise AssertionError('Page attempted a mutating command: '+value)
        process.outputExecutioner.side_effect = command
        requests = ModuleType('requests')
        requests.post = Mock()
        requests.post.return_value.json.return_value = {'status':entitlement}
        openssl, logs = ModuleType('OpenSSL'), ModuleType('plogical.CyberCPLogFileWriter')
        openssl.crypto = Mock()
        openssl.crypto.load_certificate.return_value.get_issuer.return_value.get_components.return_value = [(b'C',b'US'),(b'O',b'QA CA')]
        logs.CyberCPLogFileWriter = Mock()
        rendered = Mock(side_effect=lambda request,template,context: SimpleNamespace(render=lambda:context))
        env={'ACLManager':acl,'Administrator':admins,'Websites':sites,'ProcessUtilities':process,
             'httpProc':rendered,'ipaddress':ipaddress}
        module=ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[]))
        exec(compile(module,'<actual terminal page>','exec'),env)
        modules={'requests':requests,'OpenSSL':openssl,'plogical.CyberCPLogFileWriter':logs,
                 'firewall.firewallManager':None,'plogical.firewallUtilities':None,
                 'firewall.models':None,'plogical.securityUtils':None}
        with patch.dict('sys.modules',modules), patch('builtins.open',side_effect=AssertionError('No page writes')):
            result=env['sshAccess'](SimpleNamespace(domain='owned.example'),
                request=SimpleNamespace(get_host=lambda:'panel.example:8090'),userID=7)
        return result, process, requests, sites

    def test_active_stopped_or_unknown_service_never_changes_rules_or_service_state(self):
        for value,ready in [('active\n',True),('inactive\n',False),('unknown',False),(RuntimeError(),False)]:
            result,process,requests,sites=self.page(value)
            self.assertEqual(ready,result['terminal_service_ready'])
            self.assertEqual('owneduser',result['externalApp'])
            self.assertTrue(result['has_addons'])
            process.executioner.assert_not_called()
            self.assertEqual(['systemctl is-active fastapi_ssh_server','cat /usr/local/lscp/conf/cert.pem'],
                             [c.args[0] for c in process.outputExecutioner.call_args_list])
            self.assertEqual(8,requests.post.call_args.kwargs['timeout'])

    def test_unentitled_page_does_not_provision_access(self):
        result,process,requests,sites=self.page(entitlement=0)
        self.assertFalse(result['has_addons'])
        process.executioner.assert_not_called()

    def test_ownership_denial_precedes_service_and_entitlement_calls(self):
        result,process,requests,sites=self.page(owns=False)
        self.assertEqual('denied',result)
        process.outputExecutioner.assert_not_called()
        requests.post.assert_not_called()
        sites.objects.get.assert_not_called()

    def test_stopped_service_message_explains_operator_control(self):
        template=(ROOT/'websiteFunctions/templates/websiteFunctions/sshAccess.html').read_text()
        self.assertIn('{% if not terminal_service_ready %}',template)
        self.assertIn('Opening this page does not start services or change firewall rules.',template)


if __name__ == '__main__': unittest.main()
