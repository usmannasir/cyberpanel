"""Website settings rendering must not provision services or firewall rules."""
import ast
import ipaddress
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class DomainHomeReadOnlyTests(unittest.TestCase):
    def test_render_does_not_modify_terminal_or_firewall(self):
        source = ast.parse((ROOT / 'websiteFunctions/website.py').read_text())
        manager = next(node for node in source.body
                       if isinstance(node, ast.ClassDef) and node.name == 'WebsiteManager')
        method = next(node for node in manager.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'loadDomainHome')
        for csf_present in (False, True):
            with self.subTest(csf_present=csf_present):
                process, firewall, rules, secret, csf = (mock.Mock() for _ in range(5))
                process.outputExecutioner.return_value = 'missing'
                request = mock.Mock()
                request.get_host.return_value = 'panel.example:8090'
                sites, admins, acl, stats, php, proc = (mock.Mock() for _ in range(6))
                acl.checkOwnership.return_value = 1
                stats.FindStats.return_value = (10, 5, 20, 2)
                env = dict(Websites=sites, Administrator=admins, ACLManager=acl,
                           virtualHostUtilities=stats, PHPManager=php, httpProc=proc,
                           storage_card_context=lambda website: {}, emACL=mock.Mock(),
                           logging=mock.Mock(), ipaddress=ipaddress)
                modules = {}
                for name, attrs in {
                    'plogical.processUtilities': {'ProcessUtilities': process},
                    'plogical.securityUtils': {'get_terminal_jwt_secret': secret},
                    'plogical.CyberCPLogFileWriter': {'CyberCPLogFileWriter': mock.Mock()},
                    'plogical.firewallUtilities': {'FirewallUtilities': firewall},
                    'firewall.models': {'FirewallRules': rules},
                    'firewall.firewallManager': {'FirewallManager': csf},
                    'requests': {'post': mock.Mock()},
                }.items():
                    module = ModuleType(name)
                    vars(module).update(attrs)
                    modules[name] = module
                exec(compile(ast.Module(body=[method], type_ignores=[]), 'website.py', 'exec'), env)
                with mock.patch.dict('sys.modules', modules), \
                        mock.patch('os.path.exists', side_effect=lambda path: csf_present and path == '/etc/csf'), \
                        mock.patch('builtins.open', side_effect=FileNotFoundError):
                    result = env['loadDomainHome'](SimpleNamespace(domain='example.com'), request, 1)
                self.assertIs(result, proc.return_value.render.return_value)
                proc.assert_called_once()
                self.assertEqual(proc.call_args.args[1], 'websiteFunctions/website.html')
                process.outputExecutioner.assert_not_called()
                secret.assert_not_called()
                firewall.assert_not_called()
                self.assertEqual(firewall.method_calls, [])
                self.assertEqual(rules.mock_calls, [])
                csf.assert_not_called()


if __name__ == '__main__':
    unittest.main()
