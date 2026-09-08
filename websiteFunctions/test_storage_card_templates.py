"""Render both storage cards to check totals, unavailable states and unlimited plans."""
from pathlib import Path
import unittest

from django.conf import settings
from django.template import Context, Engine


if not settings.configured:
    settings.configure(USE_I18N=False)


class StorageCardTemplateTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parent / 'templates' / 'websiteFunctions'
        self.templates = {}
        engine = Engine(libraries={'i18n': 'django.templatetags.i18n'})
        for name in ('website.html', 'launchChild.html'):
            source = (root / name).read_text()
            card = source.split('<!-- Disk Usage Card -->', 1)[1].split('<!-- Bandwidth Card -->', 1)[0]
            self.templates[name] = engine.from_string('{% load i18n %}' + card)
        self.values = {'storageUsageState': 'available', 'storageUsageAvailable': True,
                       'storageQuotaState': 'active', 'storageUsageCheckedAt': '2026-09-09 01:00 UTC',
                       'diskInMB': 110, 'diskInMBTotal': 200, 'diskUsage': 55}

    def render(self, template):
        return template.render(Context(self.values, use_l10n=False))

    def test_verified_combined_total_and_configured_label_render(self):
        for name, template in self.templates.items():
            with self.subTest(template=name):
                result = self.render(template)
                self.assertIn('Website + Mail Storage', result)
                self.assertIn('110 MB', result)
                self.assertIn('Combined limit configured', result)
                self.assertIn('width: 55%', result)
                self.assertIn('Last measured', result)
                if name == 'launchChild.html':
                    self.assertIn('Shared parent website home', result)

    def test_unavailable_never_presents_old_values_or_a_progress_bar(self):
        self.values.update(storageUsageState='unavailable', storageUsageAvailable=False,
                           storageQuotaState='unavailable', diskInMB=999)
        for name, template in self.templates.items():
            with self.subTest(template=name):
                result = self.render(template)
                self.assertIn('Unavailable', result)
                self.assertIn('Combined limit status unavailable', result)
                self.assertNotIn('999 MB', result)
                self.assertNotIn('resource-progress-bar', result)
                self.assertNotIn('Combined limit configured', result)

    def test_zero_allowance_renders_unlimited_instead_of_zero_limit(self):
        self.values.update(diskInMBTotal=0, diskUsage=0, storageQuotaState='unconfigured')
        for name, template in self.templates.items():
            with self.subTest(template=name):
                result = self.render(template)
                self.assertIn('Unlimited', result)
                self.assertNotIn('of 0 MB', result)
                self.assertNotIn('resource-progress-bar', result)
                self.assertIn('110 MB', result)

    def test_pending_unconfigured_and_unsupported_states_do_not_claim_enforcement(self):
        for state, message in (
                ('pending', 'Combined limit needs verification'),
                ('unconfigured', 'Combined limit not configured'),
                ('unsupported', 'Combined limit unavailable on this storage')):
            self.values['storageQuotaState'] = state
            for name, template in self.templates.items():
                with self.subTest(state=state, template=name):
                    result = self.render(template)
                    self.assertIn(message, result)
                    self.assertNotIn('Combined limit configured', result)


if __name__ == '__main__':
    unittest.main()
