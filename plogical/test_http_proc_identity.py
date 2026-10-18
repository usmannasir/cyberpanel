"""Page rendering keeps the signed-in identity when loading shared onboarding."""
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, mock_open, patch


class PageIdentityTests(unittest.TestCase):
    def render_page(self, admin_acl=True, default_config='{"onboarding": 1}', missing_default=False):
        signed_in = SimpleNamespace(pk=7, firstName='Quality', lastName='Backlog')
        default_admin = SimpleNamespace(pk=1, firstName='Cyber', lastName='Panel', config=default_config)

        def get_admin(**query):
            if query == {'pk': 7}:
                return signed_in
            if query == {'userName': 'admin'} and not missing_default:
                return default_admin
            raise LookupError('No default admin')

        administrator = SimpleNamespace(objects=SimpleNamespace(get=Mock(side_effect=get_admin)))
        backups = SimpleNamespace(objects=SimpleNamespace(filter=Mock(return_value=SimpleNamespace(count=lambda: 0))))
        acl = SimpleNamespace(loadedACL=lambda uid: {'admin': int(admin_acl)}, GetServiceStatus=lambda data: None)
        process = SimpleNamespace(ent=1, decideServer=lambda: 0)
        render = Mock(side_effect=lambda request, template, data: {'template': template, 'data': data})
        modules = {}
        for name, values in {
            'django.shortcuts': {'render': render, 'HttpResponse': Mock()},
            'plogical.processUtilities': {'ProcessUtilities': process},
            'loginSystem.models': {'Administrator': administrator},
            'plogical.acl': {'ACLManager': acl},
            'IncBackups.models': {'OneClickBackups': backups},
            'baseTemplate.models': {'CyberPanelCosmetic': SimpleNamespace(objects=SimpleNamespace(get=lambda **kw: object()))},
        }.items():
            module = ModuleType(name)
            module.__dict__.update(values)
            modules[name] = module
        source = Path(__file__).with_name('httpProc.py')
        with patch.dict(sys.modules, modules), patch('builtins.open', mock_open(read_data='192.0.2.1\n')):
            spec = importlib.util.spec_from_file_location('qa_http_proc_identity', source)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            request = SimpleNamespace(session={'userID': 7})
            result = module.httpProc(request, 'baseTemplate/homePage.html').render()
        self.assertEqual(result['template'], 'baseTemplate/homePage.html')
        self.assertEqual(result['data']['fullName'], 'Quality Backlog')
        backups.objects.filter.assert_called_once_with(owner=signed_in)
        return result['data'], administrator.objects.get

    def test_secondary_admin_keeps_own_name_and_shared_onboarding(self):
        data, lookup = self.render_page()
        self.assertEqual(data['onboarding'], 1)
        self.assertEqual(lookup.call_args_list[-1].kwargs, {'userName': 'admin'})

    def test_malformed_default_config_keeps_signed_in_name(self):
        data, _ = self.render_page(default_config='not-json')
        self.assertEqual(data['onboarding'], 0)
        self.assertIn('onboardingError', data)

    def test_missing_default_admin_keeps_signed_in_name(self):
        data, _ = self.render_page(missing_default=True)
        self.assertEqual(data['onboarding'], 0)

    def test_standard_user_does_not_load_default_admin(self):
        data, lookup = self.render_page(admin_acl=False)
        self.assertEqual(data['onboarding'], 2)
        lookup.assert_called_once_with(pk=7)


if __name__ == '__main__':
    unittest.main()
