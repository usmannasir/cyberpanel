"""Render the standalone mailbox without any panel account or cosmetic context."""
from pathlib import Path

from django.template import Context, Engine
from django.test import SimpleTestCase


class StandaloneMailboxTemplateTests(SimpleTestCase):
    def setUp(self):
        root = Path(__file__).resolve().parent
        self.engine = Engine(
            dirs=[str(root / 'templates')],
            libraries={
                'static': 'django.templatetags.static',
                'i18n': 'django.templatetags.i18n',
            },
        )

    def test_mailbox_renders_its_own_brand_and_escaped_account(self):
        html = self.engine.get_template('webmail/index.html').render(Context({
            'webmail_base_template': 'webmail/base.html',
            'standalone_webmail': True,
            'email': '<script>alert(1)</script>@example.com',
        }))
        self.assertIn('brand/cyberpanel-logo.svg', html)
        self.assertIn('cyberpanel-evergreen.css', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;@example.com', html)
        self.assertIn('ng-click="logoutStandalone()"', html)
        self.assertNotIn('system-status.js', html)
        self.assertNotIn('id="sidebar"', html)
        self.assertNotIn('id="cybermailBanner"', html)
        self.assertNotIn('/emailDelivery/', html)

    def test_mailbox_still_loads_message_controller_and_notifications(self):
        html = self.engine.get_template('webmail/index.html').render(Context({
            'webmail_base_template': 'webmail/base.html',
            'standalone_webmail': True,
            'email': 'user@example.com',
        }))
        self.assertLess(html.index('webmail/standalone.js'), html.index('webmail/webmail.js'))
        self.assertIn('pnotify.custom.min.js', html)
        self.assertIn('ng-controller="webmailCtrl"', html)
        self.assertIn('ng-click="composeNew()"', html)

    def test_login_has_brand_and_accessible_credentials(self):
        html = self.engine.get_template('webmail/login.html').render(Context())
        self.assertIn('brand/cyberpanel-logo.svg', html)
        self.assertIn('for="webmail-email"', html)
        self.assertIn('id="webmail-email" autocomplete="username"', html)
        self.assertIn('for="webmail-password"', html)
        self.assertIn('id="webmail-password" autocomplete="current-password"', html)
