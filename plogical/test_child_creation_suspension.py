"""Creation/regeneration must never activate a suspended child domain."""
import ast
import contextlib
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

from plogical import websiteSuspension


def load_creation_methods():
    source = Path(__file__).with_name('virtualHostUtilities.py')
    tree = ast.parse(source.read_text(encoding='utf-8'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == 'virtualHostUtilities')
    keep = {'createDomain', '_createDomain', '_inheritDomainSuspension', 'restoreChildDomainState',
            'switchServer', '_switchServer'}
    cls.body = [node for node in cls.body if isinstance(node, ast.FunctionDef)
                and node.name in keep]
    namespace = {'os': os}
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace['virtualHostUtilities'], namespace


class ChildCreationSuspensionTests(unittest.TestCase):
    def setUp(self):
        self.worker, self.namespace = load_creation_methods()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.worker.Server_root = str(self.root)
        self.worker.redisConf = str(self.root / 'no-redis.conf')
        self.domain = 'child.example.test'
        self.config = self.root / 'conf' / 'vhosts' / self.domain / 'vhost.conf'
        self.config.parent.mkdir(parents=True)
        self.original = 'docRoot /tmp/site/\nindex {\n indexFiles index.html\n}\n'
        self.config.write_text(self.original)
        self.children = MagicMock()
        self.children.objects.filter.return_value.first.return_value = None
        self.namespace['ChildDomains'] = self.children

    def test_new_child_inherits_parent_suspension_before_activation(self):
        with patch.object(websiteSuspension, '_checked') as checked:
            self.worker._inheritDomainSuspension(types.SimpleNamespace(state=0), self.domain)
        self.assertIn(websiteSuspension.START, self.config.read_text())
        checked.assert_called_once_with([str(self.root / 'bin' / 'lshttpd'), '-t'])

    def test_regeneration_preserves_independent_child_suspension(self):
        self.children.objects.filter.return_value.first.return_value = types.SimpleNamespace(state=0)
        with patch.object(websiteSuspension, '_checked'):
            self.worker._inheritDomainSuspension(types.SimpleNamespace(state=1), self.domain)
        self.assertIn(websiteSuspension.START, self.config.read_text())

    def test_active_new_child_needs_no_vhost_change_or_activation(self):
        with patch.object(websiteSuspension, '_checked') as checked:
            self.worker._inheritDomainSuspension(types.SimpleNamespace(state=1), self.domain)
        self.assertEqual(self.original, self.config.read_text())
        checked.assert_not_called()

    def test_bad_inherited_config_restores_original_and_fails_creation(self):
        with patch.object(websiteSuspension, '_checked', side_effect=[RuntimeError('config invalid'), None]):
            with self.assertRaisesRegex(RuntimeError, 'config invalid'):
                self.worker._inheritDomainSuspension(types.SimpleNamespace(state=0), self.domain)
        self.assertEqual(self.original, self.config.read_text())

    def test_creation_holds_shared_suspension_lock(self):
        events = []

        @contextlib.contextmanager
        def locked(root):
            events.append(('lock', root))
            yield
            events.append(('unlock', root))

        with patch.object(websiteSuspension, 'suspension_lock', locked), \
                patch.object(self.worker, '_createDomain', side_effect=lambda *args: events.append('create') or (1, 'None')):
            result = self.worker.createDomain('example.test', self.domain, 'PHP 8.3', '/tmp/site', 0, 0, 0, 'owner', 0)
        self.assertEqual(result, (1, 'None'))
        self.assertEqual(events, [('lock', str(self.root)), 'create', ('unlock', str(self.root))])

    def configure_creation(self, apache=0):
        events = []
        self.namespace['open'] = MagicMock()
        self.namespace['logging'] = MagicMock()
        self.namespace['Administrator'] = MagicMock()
        package = types.SimpleNamespace(allowedDomains=0, allowFullDomain=1,
                                        memoryLimitMB=0, maxConnections=10,
                                        procSoftLimit=10, procHardLimit=10)
        master = types.SimpleNamespace(state=0, package=package,
                                       adminEmail='owner@example.test', externalApp='site',
                                       childdomains_set=MagicMock())
        websites = MagicMock()
        websites.objects.get.return_value = master
        websites.objects.filter.return_value.count.return_value = 0
        websites.objects.count.return_value = 1
        self.namespace['Websites'] = websites
        self.namespace['DNS'] = MagicMock()
        self.namespace['mailUtilities'] = MagicMock()
        self.namespace['sslUtilities'] = MagicMock()
        self.namespace['sslUtilities'].issueSSLForDomain.return_value = (1, 'None')
        self.namespace['ACLManager'] = MagicMock()
        self.namespace['ACLManager'].FindIfChild.return_value = 0
        vhost = MagicMock()
        vhost.Server_root = str(self.root)
        vhost.checkIfVirtualHostExists.return_value = 0
        vhost.checkIfAliasExists.return_value = 0
        vhost.createDirectoryForDomain.return_value = (1, 'None')
        vhost.createConfigInMainDomainHostFile.return_value = (1, 'None')
        vhost.finalizeDomainCreation.side_effect = lambda *args: events.append('finalize')
        self.namespace['vhost'] = vhost
        self.children.objects.filter.return_value.count.return_value = 0
        self.children.objects.count.return_value = 0
        self.children.return_value.save.side_effect = lambda: events.append('save')
        utility = MagicMock()
        utility.installUtilities.reStartLiteSpeed.side_effect = lambda: events.append('reload')
        self.namespace['installUtilities'] = utility
        self.namespace['ProcessUtilities'] = MagicMock(OLS=0)
        self.namespace['ProcessUtilities'].decideServer.return_value = 0
        self.namespace['ApacheController'] = MagicMock()
        self.namespace['ApacheController'].checkIfApacheInstalled.return_value = 1
        self.namespace['ApacheVhost'] = MagicMock()
        self.namespace['ApacheVhost'].setupApacheVhostChild.return_value = (1, 'None')
        self.namespace['ApacheVhost'].perHostVirtualConfOLS.side_effect = lambda *args: events.append('apache-replace')
        self.namespace['PHPManager'] = MagicMock()
        self.worker.dkimServicesInstalled = lambda: False
        return events

    def test_creation_installs_suspension_before_first_reload(self):
        events = self.configure_creation()
        with patch.object(self.worker, '_inheritDomainSuspension', side_effect=lambda *args: events.append('protect')):
            result = self.worker._createDomain('example.test', self.domain, 'PHP 8.3', '/tmp/site', 0, 0, 0, 'owner', 0)
        self.assertEqual(result, (1, 'None'))
        self.assertLess(events.index('protect'), events.index('save'))
        self.assertLess(events.index('protect'), events.index('reload'))
        self.assertEqual(self.children.call_args.kwargs['state'], 1)

    def test_restored_independent_state_is_saved_before_first_activation(self):
        events = self.configure_creation()
        with patch.object(self.worker, '_inheritDomainSuspension', side_effect=lambda *args: events.append('protect')) as protect:
            result = self.worker._createDomain('example.test', self.domain, 'PHP 8.3', '/tmp/site', 0, 0, 0, 'owner', 0,
                                               independentState=0)
        self.assertEqual(result, (1, 'None'))
        self.assertEqual(protect.call_args.args[-1], 0)
        self.assertEqual(self.children.call_args.kwargs['state'], 0)
        self.assertLess(events.index('save'), events.index('reload'))

    def test_apache_frontend_replacement_reapplies_protection_before_reload(self):
        events = self.configure_creation(apache=1)
        with patch.object(self.worker, '_inheritDomainSuspension', side_effect=lambda *args: events.append('protect')):
            result = self.worker._createDomain('example.test', self.domain, 'PHP 8.3', '/tmp/site', 0, 0, 0, 'owner', 1)
        self.assertEqual(result, (1, 'None'))
        index = events.index('apache-replace')
        self.assertEqual(events[index + 1:index + 3], ['protect', 'reload'])

    def test_failed_inheritance_stops_save_and_activation(self):
        events = self.configure_creation()
        with patch.object(self.worker, '_inheritDomainSuspension', side_effect=RuntimeError('cannot protect')):
            result = self.worker._createDomain('example.test', self.domain, 'PHP 8.3', '/tmp/site', 0, 0, 0, 'owner', 0)
        self.assertEqual(result, (0, 'cannot protect'))
        self.assertNotIn('save', events)
        self.assertNotIn('reload', events)
        self.namespace['vhost'].deleteCoreConf.assert_called_once()

    def test_backend_switch_holds_shared_suspension_lock(self):
        events = []

        @contextlib.contextmanager
        def locked(root):
            events.append('lock')
            yield
            events.append('unlock')

        with patch.object(websiteSuspension, 'suspension_lock', locked), \
                patch.object(self.worker, '_switchServer', side_effect=lambda *args: events.append('switch')):
            self.worker.switchServer(self.domain, 'PHP 8.3', 1, '/tmp/status')
        self.assertEqual(events, ['lock', 'switch', 'unlock'])

    def configure_switch(self, child):
        events = self.configure_creation()
        self.worker.apache = 1
        parent = types.SimpleNamespace(domain='parent.test', state=0, adminEmail='owner@example.test',
                                       externalApp='site', save=MagicMock())
        target = types.SimpleNamespace(domain=self.domain, state=0, master=parent,
                                       path='/home/site/child', save=MagicMock()) if child else parent
        if child:
            self.namespace['Websites'].objects.get.side_effect = ValueError('not a main website')
            self.children.objects.get.return_value = target
        else:
            self.namespace['Websites'].objects.get.return_value = target
        self.namespace['vhost'].perHostDomainConf.side_effect = lambda *args: events.append('replace')
        self.namespace['vhost'].perHostVirtualConf.side_effect = lambda *args: events.append('replace')
        self.namespace['ApacheVhost'].perHostVirtualConfOLS.side_effect = lambda *args: events.append('replace')
        self.namespace['sslUtilities'].sslUtilities.installSSLForDomain.return_value = 1
        return events, parent, target

    def test_both_backend_switch_directions_protect_main_and_child_before_reload(self):
        for child in (False, True):
            for server in (1, 2):
                with self.subTest(child=child, server=server):
                    events, parent, target = self.configure_switch(child)
                    with patch.object(self.worker, '_inheritDomainSuspension', side_effect=lambda *args: events.append('protect')) as protect:
                        self.worker._switchServer(self.domain, 'PHP 8.3', server, '/tmp/status')
                    protect.assert_called_once_with(parent, self.domain, target.state if child else 1)
                    self.assertLess(events.index('replace'), events.index('protect'))
                    self.assertEqual(events[events.index('protect') + 1], 'reload')

    def test_backend_switch_never_reloads_when_suspension_protection_fails(self):
        events, _, _ = self.configure_switch(child=True)
        with patch.object(self.worker, '_inheritDomainSuspension', side_effect=RuntimeError('protection failed')):
            self.worker._switchServer(self.domain, 'PHP 8.3', 1, '/tmp/status')
        self.assertNotIn('reload', events)


if __name__ == '__main__':
    unittest.main()
