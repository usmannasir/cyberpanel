"""Run the patched rule writer against separate AlmaLinux firewalld configs."""
import ast
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class Logging:
    @staticmethod
    def writeToFile(message):
        pass


def load_rule_writer():
    modules = {
        'django': {'setup': lambda: None},
        'plogical.CyberCPLogFileWriter': {'CyberCPLogFileWriter': Logging},
        'plogical.processUtilities': {'ProcessUtilities': types.SimpleNamespace()},
        'plogical.sshKeyUtilities': {'delete_authorized_key': None},
        'plogical.sshConfigUtilities': {'update_ssh_config': None, 'ssh_service_is_listening': None},
    }
    stubs = {'plogical': types.ModuleType('plogical')}
    for name, attributes in modules.items():
        stubs[name] = types.ModuleType(name)
        stubs[name].__dict__.update(attributes)
    scope = {'__name__': 'firewall_candidate'}
    with patch.dict(sys.modules, stubs):
        exec(compile((ROOT/'plogical/firewallUtilities.py').read_bytes(), 'firewallUtilities.py', 'exec'), scope)
    return scope


@unittest.skipUnless(shutil.which("firewall-offline-cmd"), "requires firewalld integration tools")
class RuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.paths = {}
        for scope in ('runtime', 'permanent'):
            path = Path(self.temp.name)/scope
            (path/'zones').mkdir(parents=True)
            self.paths[scope] = path
        self.code = load_rule_writer()
        self.writer = self.code['FirewallUtilities']
        self.code['ProcessUtilities'].outputExecutioner = self.transport
        self.fail_runtime_add = False
        self.fail_runtime_remove = False
        self.calls = []
        self.ignore_runtime_add = False

    def offline(self, scope, *args):
        return subprocess.run(['firewall-offline-cmd', '--system-config='+str(self.paths[scope]),
                               *args], capture_output=True, text=True, timeout=15)

    def transport(self, command, *, shell, retRequired):
        import shlex
        argv = shlex.split(command)
        assert argv.pop(0) == 'firewall-cmd'
        assert shell is False and retRequired is True
        scope = 'permanent' if '--permanent' in argv else 'runtime'
        if scope == 'permanent':
            argv.remove('--permanent')
        self.calls.append((scope, argv))
        if self.ignore_runtime_add and scope == 'runtime' and any(a.startswith('--add-rich-rule=') for a in argv):
            return 1, 'success'
        if self.fail_runtime_add and scope == 'runtime' and any(a.startswith('--add-rich-rule=') for a in argv):
            return 0, 'simulated write failure'
        if self.fail_runtime_remove and scope == 'runtime' and any(a.startswith('--remove-rich-rule=') for a in argv):
            return 0, 'simulated remove failure'
        result = self.offline(scope, *argv)
        return int(result.returncode == 0), result.stdout

    def rules(self, scope):
        result = self.offline(scope, '--zone=public', '--list-rich-rules')
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip().splitlines()

    def seed(self, rule, scopes=('runtime', 'permanent')):
        for scope in scopes:
            result = self.offline(scope, '--zone=public', '--add-rich-rule='+rule)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_ipv4_create_delete_preserves_existing_rules(self):
        existing = 'rule family="ipv6" port port="18080" protocol="tcp" accept'
        operator = 'rule family="ipv4" source address="198.51.100.8" port port="18081" protocol="tcp" accept'
        self.seed(existing)
        self.seed(operator, ('runtime',))
        before = {scope: self.rules(scope) for scope in self.paths}
        self.assertEqual(self.writer.addRule('tcp', '18080', '192.0.2.4', require_new=True), 1)
        for scope in self.paths:
            added = set(self.rules(scope)) - set(before[scope])
            self.assertEqual(len(added), 1)
            self.assertIn('family="ipv4" source address="192.0.2.4"', added.pop())
        self.assertEqual(self.writer.deleteRule('tcp', '18080', '192.0.2.4/32'), 1)
        for scope in self.paths:
            self.assertEqual(self.rules(scope), before[scope])
        self.assertTrue(all('--reload' not in argv for _, argv in self.calls))

    def test_ipv6_source_and_range(self):
        source = '2001:db8:1111:2222:3333:4444:5555:6666/128'
        self.assertEqual(self.writer.addRule('udp', '18082-18083', source), 1)
        for scope in self.paths:
            rules = self.rules(scope)
            self.assertEqual(len(rules), 1)
            self.assertIn('family="ipv6" source address="'+source.split('/')[0]+'"', rules[0])

    def test_dual_stack_is_explicit(self):
        self.assertEqual(self.writer.addRule('tcp', '18084', '0.0.0.0/0', dual_stack=True), 1)
        for scope in self.paths:
            self.assertEqual(len(self.rules(scope)), 2)
        self.assertEqual(self.writer.addRule('tcp', '18085', '192.0.2.4', dual_stack=True), 0)

    def test_existing_rule_is_not_adopted(self):
        self.seed('rule family="ipv4" source address="192.0.2.4" port port="18086" protocol="tcp" accept')
        self.assertEqual(self.writer.addRule('tcp', '18086', '192.0.2.4/32', require_new=True), 0)
        self.assertFalse(any('--add-rich-rule=' in ' '.join(argv) for _, argv in self.calls))

    def test_runtime_failure_undoes_only_candidate_permanent_write(self):
        original = 'rule family="ipv6" source address="2001:db8:1::/64" port port="18087" protocol="tcp" accept'
        self.seed(original)
        self.fail_runtime_add = True
        self.assertEqual(self.writer.addRule('tcp', '18087', '192.0.2.4'), 0)
        for scope in self.paths:
            self.assertEqual(self.rules(scope), [original])

    def test_invalid_values_have_no_side_effects(self):
        for port, source in [('0', '192.0.2.1'), ('65536', '192.0.2.1'),
                             ('18089-18088', '192.0.2.1'), ('18088', 'invalid')]:
            self.assertEqual(self.writer.addRule('tcp', port, source), 0)
        self.assertEqual(self.calls, [])

    def test_zone_inventory_is_read_only(self):
        self.seed('rule family="ipv6" source address="2001:db8:1::/64" port port="18089" protocol="tcp" accept')
        snapshot = self.writer.currentFirewalldConfiguration()
        for scope in self.paths:
            self.assertIn('18089', snapshot[scope])
        self.assertEqual(self.calls, [('runtime', ['--list-all-zones']),
                                      ('permanent', ['--list-all-zones'])])

    def panel_manager(self, records):
        tree = ast.parse((ROOT/'firewall/firewallManager.py').read_text())
        manager = next(node for node in tree.body
                       if isinstance(node, ast.ClassDef) and node.name == 'FirewallManager')
        manager.body = [node for node in manager.body if isinstance(node, ast.FunctionDef)
                        and node.name in ('addRule', 'deleteRule')]
        scope = {
            'ACLManager': types.SimpleNamespace(loadedACL=lambda uid: {'admin': 1}),
            'FirewallUtilities': self.writer,
            'FirewallRules': types.SimpleNamespace(objects=records),
            'HttpResponse': json.loads,
            'json': json,
        }
        exec(compile(ast.Module(body=[manager], type_ignores=[]), 'firewallManager.py', 'exec'), scope)
        return scope['FirewallManager']()

    def test_panel_delete_uses_saved_rule_identity(self):
        record = types.SimpleNamespace(proto='tcp', port='18091', ipAddress='192.0.2.4',
                                       pk=1, delete=lambda: None)
        records = types.SimpleNamespace(get=lambda **kwargs: record,
                                        filter=lambda **kwargs: types.SimpleNamespace(exclude=lambda **kw: []))
        self.assertEqual(self.writer.addRule('tcp', '18091', '192.0.2.4'), 1)
        result = self.panel_manager(records).deleteRule(1, {'id': 1})
        self.assertEqual(result['delete_status'], 1)
        self.assertTrue(all(self.rules(scope) == [] for scope in self.paths))

    def test_panel_delete_preserves_semantically_duplicate_records(self):
        record = types.SimpleNamespace(proto='tcp', port='18092', ipAddress='192.0.2.4', pk=1)
        peer = types.SimpleNamespace(proto='tcp', port='18092', ipAddress='192.0.2.4/32', pk=2)
        records = types.SimpleNamespace(get=lambda **kwargs: record,
                                        filter=lambda **kwargs: types.SimpleNamespace(exclude=lambda **kw: [peer]))
        result = self.panel_manager(records).deleteRule(1, {'id': 1})
        self.assertEqual(result['delete_status'], 0)
        self.assertEqual(self.calls, [])



    def test_permanent_only_existing_rule_is_not_adopted(self):
        self.seed('rule family="ipv4" source address="192.0.2.4" port port="18093" protocol="tcp" accept', ('permanent',))
        before = {scope: self.rules(scope) for scope in self.paths}
        self.assertEqual(self.writer.addRule('tcp', '18093', '192.0.2.4', require_new=True), 0)
        self.assertEqual({scope: self.rules(scope) for scope in self.paths}, before)

    def test_runtime_only_existing_rule_is_not_adopted(self):
        self.seed('rule family="ipv4" source address="192.0.2.4" port port="18094" protocol="tcp" accept', ('runtime',))
        before = {scope: self.rules(scope) for scope in self.paths}
        self.assertEqual(self.writer.addRule('tcp', '18094', '192.0.2.4', require_new=True), 0)
        self.assertEqual({scope: self.rules(scope) for scope in self.paths}, before)

    def test_runtime_delete_failure_restores_permanent_rule(self):
        self.assertEqual(self.writer.addRule('tcp', '18095', '192.0.2.4'), 1)
        before = {scope: self.rules(scope) for scope in self.paths}
        self.fail_runtime_remove = True
        self.assertEqual(self.writer.deleteRule('tcp', '18095', '192.0.2.4'), 0)
        self.assertEqual({scope: self.rules(scope) for scope in self.paths}, before)

    def test_legacy_ipv6_unrestricted_rule_is_not_removed(self):
        self.seed('rule family="ipv6" port port="18096" protocol="tcp" accept')
        self.assertEqual(self.writer.deleteRule('tcp', '18096', '192.0.2.4'), 1)
        for scope in self.paths:
            self.assertEqual(len(self.rules(scope)), 1)

    def test_malformed_bridge_response_fails_without_write(self):
        for result in [None, 0, '1', (1,), (1, None), (0, 'failed')]:
            self.code['ProcessUtilities'].outputExecutioner = lambda *a, **kw: result
            self.assertEqual(self.writer.addRule('tcp', '18097', '192.0.2.4'), 0)

    def test_scoped_ipv6_and_injected_input_are_rejected(self):
        for source in ['fe80::1%eth0', '192.0.2.1;id', "192.0.2.1'"]:
            self.assertEqual(self.writer.addRule('tcp', '18098', source), 0)
        for port in ['18098\\n', '18098;id', '-1']:
            self.assertEqual(self.writer.addRule('tcp', port, '192.0.2.4'), 0)
        self.assertEqual(self.calls, [])

    def test_ipv4_cidr_is_not_widened_to_ipv6(self):
        self.assertEqual(self.writer.addRule('tcp', '18099', '192.0.2.0/24'), 1)
        for scope in self.paths:
            self.assertEqual(self.rules(scope), ['rule family="ipv4" source address="192.0.2.0/24" port port="18099" protocol="tcp" accept'])



    def test_success_without_rule_readback_is_failure_and_rolls_back(self):
        self.ignore_runtime_add = True
        self.assertEqual(self.writer.addRule('tcp', '18100', '192.0.2.4'), 0)
        self.assertTrue(all(self.rules(scope) == [] for scope in self.paths))

    def test_panel_save_failure_undoes_only_new_rule(self):
        self.seed('rule family="ipv6" port port="18101" protocol="tcp" accept')
        before = {scope: self.rules(scope) for scope in self.paths}
        manager = self.panel_manager(None)
        class UnsavedRecord:
            def __init__(self, **kw):
                pass
            def full_clean(self):
                pass
            def save(self):
                raise RuntimeError('simulated database save failure')
        manager.addRule.__globals__['FirewallRules'] = UnsavedRecord
        result = manager.addRule(1, {'ruleName':'qa', 'ruleProtocol':'tcp',
                                    'rulePort':'18101','ruleIP':'192.0.2.4'})
        self.assertEqual(result['add_status'], 0)
        self.assertEqual({scope: self.rules(scope) for scope in self.paths}, before)


class RuleSourceTests(unittest.TestCase):
    def setUp(self):
        self.code = load_rule_writer()

    def test_source_family_preserved(self):
        rich = self.code['_richRules']
        self.assertEqual(len(rich('tcp','80','192.0.2.1')),1)
        self.assertIn('family="ipv4" source address="192.0.2.1"',rich('tcp','80','192.0.2.1')[0])
        self.assertEqual(len(rich('udp','53','2001:db8::/64')),1)
        self.assertIn('family="ipv6" source address="2001:db8::/64"',rich('udp','53','2001:db8::/64')[0])

    def test_dual_stack_requires_unrestricted_ipv4(self):
        rich = self.code['_richRules']
        self.assertEqual(len(rich('tcp','80','0.0.0.0/0',True)),2)
        for source in ('192.0.2.0/24','::/0'):
            with self.assertRaises(ValueError):
                rich('tcp','80',source,True)

    def test_service_callers_explicitly_preserve_dual_stack(self):
        paths = ('CLManager/CageFS.py','WebTerminal/views.py','highAvailability/haManager.py',
                 'plogical/ClusterManager.py','serverStatus/views.py')
        count = 0
        for path in paths:
            for node in ast.walk(ast.parse((ROOT/path).read_text())):
                if (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
                    and isinstance(node.func.value,ast.Name)
                    and node.func.value.id=='FirewallUtilities'
                    and node.func.attr in ('addRule','deleteRule')):
                    self.assertTrue(any(k.arg=='dual_stack' and isinstance(k.value,ast.Constant)
                                        and k.value.value is True for k in node.keywords), path)
                    count += 1
        self.assertEqual(count,11)

    def test_both_served_javascript_sources_handle_inventory(self):
        for path in ('firewall/static/firewall/firewall.js','static/firewall/firewall.js'):
            text = (ROOT/path).read_text()
            self.assertIn('$scope.firewalld = response.data.firewalld;', text)
            fetch = text.split('    function populateCurrentRecords() {', 1)[1].split('    $scope.deleteRule', 1)[0]
            failure = fetch.split('function cantLoadInitialDatas(response) {', 1)[1]
            self.assertIn('$scope.firewalldRead = true;', failure)
            self.assertIn('$scope.rulesLoading = true;', failure)


if __name__ == '__main__':
    unittest.main(verbosity=2)
