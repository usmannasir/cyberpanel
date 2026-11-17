"""Smoke test the patched writer against a live daemon in a disposable container."""
import shlex
import subprocess
from firewall.test_firewalld_rules import load_rule_writer


def run(command, *, shell, retRequired):
    assert shell is False and retRequired is True
    result = subprocess.run(shlex.split(command), capture_output=True, text=True, timeout=15)
    return int(result.returncode == 0), result.stdout + result.stderr


code = load_rule_writer()
code['ProcessUtilities'].outputExecutioner = run
writer = code['FirewallUtilities']
operator_rule = 'rule family="ipv6" source address="2001:db8:2::/64" port port="18090" protocol="tcp" accept'
subprocess.run(['firewall-cmd', '--zone=public', '--add-rich-rule='+operator_rule],
               check=True, capture_output=True, text=True, timeout=15)
before = writer.currentFirewalldConfiguration()
assert writer.addRule('tcp', '18090', '192.0.2.20', require_new=True)
after = writer.currentFirewalldConfiguration()
for scope in before:
    added = set(after[scope].splitlines()) - set(before[scope].splitlines())
    assert len(added) == 1
    rule = added.pop()
    assert 'family="ipv4" source address="192.0.2.20"' in rule and 'port="18090"' in rule
assert writer.deleteRule('tcp', '18090', '192.0.2.20')
assert writer.currentFirewalldConfiguration() == before
print('Live AlmaLinux firewalld checks passed in both runtime and permanent configuration.')
