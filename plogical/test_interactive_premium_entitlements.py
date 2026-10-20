"""Exercise exact endpoint bodies with inert services and no Django bootstrap."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
BACKUP_ACTIONS = (
    'ConfigureV2BackupSetup', 'CreateV2BackupButton', 'RestorePathV2',
    'DeleteSnapshotV2Final', 'selectwebsiteRetorev2', 'ConfigureSftpV2Backup',
    'selectwebsiteCreatev2', 'selectreporestorev2', 'CreateScheduleV2',
)


def forbidden(*args, **kwargs):
    raise AssertionError('A denied endpoint reached an external operation')


def response(data):
    return data if isinstance(data, dict) else json.loads(data)


def actual(path, names, env, owner=None):
    tree = ast.parse((ROOT / path).read_text())
    body = tree.body
    if owner:
        body = next(n.body for n in body if isinstance(n, ast.ClassDef) and n.name == owner)
    nodes = [n for n in body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert set(names) == {n.name for n in nodes}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), env)
    return env


class EntitlementTests(unittest.TestCase):
    def setUp(self):
        self.acl = SimpleNamespace(CheckForPremFeature=Mock(return_value=0),
            loadedACL=Mock(return_value={'admin': 1, 'manageSSL': 1}),
            findAllSites=Mock(return_value=['fixture.invalid']),
            checkOwnership=Mock(return_value=1),
            loadError=Mock(return_value={'ownership_denied': True}),
            loadErrorJson=Mock(return_value={'ownership_denied': True}),
            FetchCloudFlareAPIKeyFromAcme=Mock(side_effect=forbidden))
        self.env = {'ACLManager': self.acl, 'JsonResponse': response,
            'HttpResponse': response, 'json': json,
            'wraps': __import__('functools').wraps,
            'redirect': lambda name: {'redirect': name}}
        actual('plogical/premiumEntitlements.py', ['premium_entitlement_required'], self.env)
        self.env.update(Administrator=SimpleNamespace(objects=SimpleNamespace(get=Mock(return_value='owner'))),
            CPBackupsV2=Mock(side_effect=forbidden),
            httpProc=Mock(side_effect=lambda *a: SimpleNamespace(render=lambda: a)),
            ProcessUtilities=SimpleNamespace(outputExecutioner=Mock(side_effect=forbidden)),
            time=SimpleNamespace(sleep=lambda *_: None))

    def test_every_backup_action_denies_before_request_or_worker_access(self):
        actual('IncBackups/views.py', BACKUP_ACTIONS, self.env)
        for grant in (0, '1', True, 1.0, None):
            for name in BACKUP_ACTIONS:
                with self.subTest(grant=grant, endpoint=name):
                    self.acl.CheckForPremFeature.return_value = grant
                    result = self.env[name](object())
                    self.assertEqual(0, result['status'])
                    self.assertEqual(0, result['installStatus'])
                    self.assertEqual(0, result['fetchStatus'])
                    self.assertEqual('An active Backup V2 entitlement is required.', result['error_message'])
        self.env['CPBackupsV2'].assert_not_called()
        self.acl.loadedACL.assert_not_called()

    def test_lookup_exception_denies_every_backup_action(self):
        actual('IncBackups/views.py', BACKUP_ACTIONS, self.env)
        self.acl.CheckForPremFeature.side_effect = TimeoutError
        for name in BACKUP_ACTIONS:
            with self.subTest(endpoint=name):
                self.assertEqual(0, self.env[name](object())['status'])
        self.env['CPBackupsV2'].assert_not_called()

    def test_licensed_owner_starts_backup_with_original_options(self):
        actual('IncBackups/views.py', ['CreateV2BackupButton'], self.env)
        self.acl.CheckForPremFeature.return_value = 1
        worker = SimpleNamespace(start=Mock())
        self.env['CPBackupsV2'] = Mock(return_value=worker)
        req = SimpleNamespace(session={'userID': 7}, body=json.dumps({
            'Selectedwebsite': 'fixture.invalid', 'Selectedrepo': 'fixture-repository',
            'websiteData': True, 'websiteDatabases': True, 'websiteEmails': False}))
        result = self.env['CreateV2BackupButton'](req)
        self.assertEqual(1, result['installStatus'])
        self.acl.checkOwnership.assert_called_once_with('fixture.invalid', 'owner', {'admin': 1, 'manageSSL': 1})
        worker.start.assert_called_once_with()
        args = self.env['CPBackupsV2'].call_args.args[0]
        self.assertEqual('InitiateBackup', args['function'])
        self.assertEqual('fixture-repository', args['BackendName'])
        self.assertTrue(args['BackupData'])
        self.assertTrue(args['BackupDatabase'])
        self.assertFalse(args['BackupEmails'])

    def test_license_does_not_override_backup_ownership(self):
        actual('IncBackups/views.py', ['CreateV2BackupButton'], self.env)
        self.acl.CheckForPremFeature.return_value = 1
        self.acl.checkOwnership.return_value = 0
        req = SimpleNamespace(session={'userID': 7}, body=json.dumps({
            'Selectedwebsite': 'other.invalid', 'Selectedrepo': 'fixture-repository'}))
        self.assertEqual({'ownership_denied': True}, self.env['CreateV2BackupButton'](req))
        self.env['CPBackupsV2'].assert_not_called()

    def test_backup_page_redirects_unpaid_and_renders_for_paid(self):
        actual('backup/backupManager.py', ['CreateV2backupSite'], self.env, 'BackupManager')
        self.assertEqual({'redirect': 'ConfigureV2Backup'}, self.env['CreateV2backupSite'](object()))
        self.acl.loadedACL.assert_not_called()
        self.acl.CheckForPremFeature.return_value = 1
        result = self.env['CreateV2backupSite'](object(), request='request', userID=7)
        self.assertEqual('IncBackups/CreateV2Backup.html', result[1])
        self.assertEqual('createBackup', result[3])

    def test_unpaid_advanced_ssl_get_and_post_render_without_reading_or_configuring_secrets(self):
        actual('manageSSL/views.py', ['v2ManageSSL'], self.env)
        for method in ('GET', 'POST'):
            with self.subTest(method=method):
                request = SimpleNamespace(session={'userID': 7}, method=method)
                result = self.env['v2ManageSSL'](request)
                self.assertEqual('manageSSL/v2ManageSSL.html', result[1])
                self.assertEqual({'PremStat': 0, 'websiteList': ['fixture.invalid']}, result[2])
        self.acl.FetchCloudFlareAPIKeyFromAcme.assert_not_called()

    def test_unpaid_ssl_issue_returns_legacy_failure_before_request_access(self):
        actual('manageSSL/views.py', ['v2IssueSSL'], self.env)
        result = self.env['v2IssueSSL'](object())
        self.assertEqual(0, result['status'])
        self.assertEqual(0, result['SSL'])
        self.assertEqual('An active SSL V2 entitlement is required.', result['error_message'])
        self.env['ProcessUtilities'].outputExecutioner.assert_not_called()

    def test_licensed_ssl_still_requires_website_ownership(self):
        actual('manageSSL/views.py', ['v2IssueSSL'], self.env)
        self.acl.CheckForPremFeature.return_value = 1
        self.acl.checkOwnership.return_value = 0
        req = SimpleNamespace(session={'userID': 7}, method='POST', body=json.dumps({'virtualHost': 'other.invalid'}))
        self.assertEqual({'ownership_denied': True}, self.env['v2IssueSSL'](req))
        self.env['ProcessUtilities'].outputExecutioner.assert_not_called()

    def test_root_file_pages_and_download_deny_before_any_work(self):
        actual('filemanager/views.py', ['FileManagerRoot', 'RootDownloadFile'], self.env)
        self.assertEqual({'redirect': 'https://cyberpanel.net/cyberpanel-addons'}, self.env['FileManagerRoot'](object()))
        self.assertEqual(0, self.env['RootDownloadFile'](object())['status'])
        self.acl.loadedACL.assert_not_called()

    def test_mysql_pages_and_actions_deny_before_work(self):
        pages = ['MySQLManager', 'OptimizeMySQL', 'Upgardemysql']
        actual('databases/databaseManager.py', pages, self.env, 'DatabaseManager')
        self.env['require_POST'] = lambda fn: fn
        actions = ['generateRecommendations', 'applyMySQLChanges', 'upgrademysqlnow']
        actual('databases/views.py', actions, self.env)
        for name in pages:
            with self.subTest(page=name):
                self.assertEqual({'redirect': 'https://cyberpanel.net/cyberpanel-addons'}, self.env[name](object()))
        for name in actions:
            with self.subTest(action=name):
                result = self.env[name](object())
                self.assertEqual(0, result['status'])
                self.assertEqual('An active MySQL Manager entitlement is required.', result['error_message'])
        self.acl.loadedACL.assert_not_called()

    def test_licensed_mysql_optimizer_still_checks_admin_before_configuration(self):
        actual('databases/views.py', ['generateRecommendations', 'applyMySQLChanges'], self.env)
        self.acl.CheckForPremFeature.return_value = 1
        self.env['MySQLOptimizer'] = SimpleNamespace(generateRecommendations=Mock(return_value='fixture-conf'))
        self.env['mysqlUtilities'] = SimpleNamespace(applyMySQLChanges=Mock(return_value=(1, 'saved')))
        req = SimpleNamespace(session={'userID': 7}, body=json.dumps({'detectedRam': 4}))
        result = self.env['generateRecommendations'](req)
        self.assertEqual('fixture-conf', result['generatedConf'])
        self.env['MySQLOptimizer'].generateRecommendations.assert_called_once_with(4)
        self.assertEqual(1, self.env['applyMySQLChanges'](req)['status'])
        self.env['mysqlUtilities'].applyMySQLChanges.assert_called_once_with({'detectedRam': 4})
        self.env['mysqlUtilities'].applyMySQLChanges.reset_mock()
        self.acl.loadedACL.return_value = {'admin': 0}
        self.assertEqual({'ownership_denied': True}, self.env['applyMySQLChanges'](req))
        self.env['mysqlUtilities'].applyMySQLChanges.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
