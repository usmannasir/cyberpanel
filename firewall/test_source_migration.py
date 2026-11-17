"""Verify fresh and existing firewall schemas without the panel database."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceMigrationTests(unittest.TestCase):
    def test_existing_rows_survive_ipv6_source_migration(self):
        program = """
from django.conf import settings
settings.configure(SECRET_KEY='disposable-firewall-test',INSTALLED_APPS=['firewall'],
    DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}},
    DEFAULT_AUTO_FIELD='django.db.models.AutoField')
import django
django.setup()
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
e=MigrationExecutor(connection)
e.migrate([('firewall','0001_initial')])
old=e.loader.project_state([('firewall','0001_initial')]).apps.get_model('firewall','FirewallRules')
old.objects.create(name='legacy',proto='tcp',port='18099',ipAddress='192.0.2.4')
e=MigrationExecutor(connection)
e.migrate([('firewall','0002_source_ipv6')])
from firewall.models import FirewallRules
assert FirewallRules.objects.get(name='legacy').ipAddress=='192.0.2.4'
address='2001:db8:1111:2222:3333:4444:5555:6666/128'
row=FirewallRules(name='ipv6',proto='tcp',port='18099',ipAddress=address)
row.full_clean()
row.save()
assert FirewallRules.objects.get(name='ipv6').ipAddress==address
assert FirewallRules._meta.get_field('ipAddress').max_length==64
print('legacy row and complete IPv6 CIDR preserved')
"""
        env = os.environ.copy()
        env.pop('DJANGO_SETTINGS_MODULE', None)
        env['PYTHONPATH'] = str(ROOT)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        result = subprocess.run([sys.executable, '-c', program], cwd=str(ROOT),
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('complete IPv6 CIDR preserved', result.stdout)
