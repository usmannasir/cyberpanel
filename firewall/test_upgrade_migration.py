"""Run the actual post-download migration sequence with mail services absent."""
import ast
from pathlib import Path
import types
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]


def load_migration_sequence(result):
    tree = ast.parse((ROOT/'plogical/upgrade.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Upgrade')
    methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    upgrade = methods['upgrade']
    def calls(node, name):
        return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and isinstance(n.func.value, ast.Name) and n.func.value.id == 'Upgrade'
                   and n.func.attr == name for n in ast.walk(node))
    start = next(i for i,n in enumerate(upgrade.body) if calls(n,'applyLoginSystemMigrations'))
    end = next(i for i,n in enumerate(upgrade.body) if calls(n,'setupSieve'))
    upgrade.body = upgrade.body[start:end]
    cls.body = [upgrade, methods['applyFirewallMigrations'], methods['setupWebmail']]
    namespace = {'os':types.SimpleNamespace(path=types.SimpleNamespace(exists=lambda _:False))}
    exec(compile(ast.Module(body=[cls],type_ignores=[]),'upgrade.py','exec'),namespace)
    upgrade_class = namespace['Upgrade']
    for node in ast.walk(upgrade):
        if (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
            and isinstance(node.func.value,ast.Name) and node.func.value.id=='Upgrade'
            and not hasattr(upgrade_class,node.func.attr)):
            setattr(upgrade_class,node.func.attr,Mock())
    upgrade_class.executioner = Mock(return_value=result)
    upgrade_class.stdOut = Mock()
    return upgrade_class


class FirewallUpgradeMigrationTests(unittest.TestCase):
    def test_mail_less_upgrade_applies_firewall_migrations(self):
        upgrade = load_migration_sequence(True)
        upgrade.upgrade('v3.0.8')
        upgrade.executioner.assert_called_once_with(
            '/usr/local/CyberPanel/bin/python /usr/local/CyberCP/manage.py migrate firewall --noinput',
            'Firewall database migrations',0)
        upgrade.stdOut.assert_any_call('Dovecot not installed, skipping webmail setup.',0)

    def test_migration_failure_aborts_before_later_upgrade_steps(self):
        upgrade = load_migration_sequence(False)
        with self.assertRaisesRegex(RuntimeError,'firewall database migrations failed'):
            upgrade.upgrade('v3.0.8')
        upgrade.rotateInvalidAPITokens.assert_not_called()
        upgrade.stdOut.assert_not_called()
