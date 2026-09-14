"""Keep optimizer-only cloud operations paid, without changing ordinary databases."""
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cloudAPI.test_wordpress_cloud_entitlements import load_cloud


class MySQLCloudEntitlementTests(unittest.TestCase):
    def setUp(self):
        self.ns, self.services, self.admin, self.output_file = load_cloud()
        self.acl = self.services['ACLManager']
        self.acl.loadedACL.return_value = {'admin':1}
        self.memory = mock.Mock(return_value=SimpleNamespace(total=5*1024**3+1))
        previous = self.ns['__builtins__']['__import__']
        def imports(name, *args, **kwargs):
            if name == 'psutil': return SimpleNamespace(virtual_memory=self.memory)
            if name == 'math': return math
            return previous(name, *args, **kwargs)
        self.ns['__builtins__']['__import__'] = imports
        self.mysql = mock.Mock()
        self.mysql.applyMySQLChanges.return_value = (1, None)
        self.ns['mysqlUtilities'] = self.mysql
        self.cloud = self.ns['CloudManager']({'inert':1}, self.admin)
        self.request = SimpleNamespace(session={})

    def assert_no_work(self):
        self.memory.assert_not_called()
        self.mysql.applyMySQLChanges.assert_not_called()
        self.services['ProcessUtilities'].outputExecutioner.assert_not_called()
        self.output_file.assert_not_called()
        self.assertEqual(self.request.session, {})

    def test_unpaid_direct_optimizer_operations_stop_before_reads_or_session_change(self):
        for name in ('fetchRam','applyMySQLChanges'):
            with self.subTest(name=name):
                self.acl.reset_mock()
                response = getattr(self.cloud,name)(self.request)
                payload = json.loads(response.content)
                self.assertEqual(payload['status'],0)
                self.assertIn('entitlement',payload['error_message'])
                self.acl.CheckForPremFeature.assert_called_once_with('Filemanager')
                self.assert_no_work()

    def test_lookup_failure_and_malformed_status_cannot_apply_mysql_changes(self):
        for value in (True,'1',1.0,None):
            self.acl.CheckForPremFeature.return_value = value
            self.assertEqual(json.loads(self.cloud.applyMySQLChanges(self.request).content)['status'],0)
            self.assert_no_work()
        self.acl.CheckForPremFeature.side_effect = TimeoutError('unavailable')
        self.assertEqual(json.loads(self.cloud.fetchRam(self.request).content)['status'],0)
        self.assert_no_work()

    def test_authenticated_router_keeps_entitlement_boundary(self):
        for name in ('fetchRam','applyMySQLChanges'):
            request = SimpleNamespace(body=json.dumps({'controller':name,'serverUserName':'admin'}).encode(),
                                      META={'HTTP_AUTHORIZATION':'inert-token'},session={})
            self.assertEqual(json.loads(self.ns['router'](request).content)['status'],0)
            self.assert_no_work()

    def test_paid_optimizer_keeps_original_memory_config_and_apply_response(self):
        self.acl.CheckForPremFeature.return_value = 1
        response = json.loads(self.cloud.fetchRam(self.request).content)
        self.assertEqual((response['status'],response['ramInGB']),(1,6))
        self.services['ProcessUtilities'].outputExecutioner.assert_called_once_with('sudo cat /etc/mysql/my.cnf')
        result = self.cloud.applyMySQLChanges(self.request)
        self.assertEqual(json.loads(result.content)['status'],1)
        self.mysql.applyMySQLChanges.assert_called_once_with({'inert':1})
        self.assertEqual(self.request.session, {'userID':7})

    def test_paid_does_not_bypass_existing_apply_admin_acl(self):
        self.acl.CheckForPremFeature.return_value = 1
        self.acl.loadedACL.return_value = {'admin':0}
        result = json.loads(self.cloud.applyMySQLChanges(self.request).content)
        self.assertEqual(result['status'],0)
        self.assertIn('administrators',result['error_message'])
        self.mysql.applyMySQLChanges.assert_not_called()


if __name__ == '__main__':
    unittest.main()
