"""Render the actual layouts without a database or panel services."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from django.conf import settings
if not settings.configured:
    settings.configure(USE_I18N=False, STATIC_URL='/static/', INSTALLED_APPS=[])
    import django
    django.setup()
from django.template import Context, Engine, Library

from baseTemplate.panelThemes import PANEL_V3_STARTER


class CustomCSSRenderingTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.engine = Engine(
            dirs=[str(root / 'baseTemplate/templates'), str(root / 'loginSystem/templates')],
            libraries={'i18n': 'django.templatetags.i18n', 'static': 'django.templatetags.static'})
        # Routes are irrelevant to stylesheet order; keep the real inheritance,
        # blocks, includes, static tags and escaping behavior.
        routes = Library()
        routes.simple_tag(name='url')(lambda *args, **kwargs: '/placeholder/')
        self.engine.template_builtins.append(routes)

    def test_dashboard_overrides_follow_shared_page_and_footer_styles(self):
        template = self.engine.from_string('''{% extends "baseTemplate/index.html" %}
            {% block header_scripts %}<style id="page-head">body{color:red}</style>{% endblock %}
            {% block content %}<style id="page-body">body{color:blue}</style>{% endblock %}
            {% block footer_scripts %}<style id="page-footer">body{color:green}</style>{% endblock %}''')
        css = 'html body { color: purple; }'
        html = template.render(Context({'cosmetic': {'MainDashboardCSS': css}}))
        self.assertEqual(1, html.count('id="cyberpanel-custom-css"'))
        self.assertIn(css, html)
        custom = html.index('id="cyberpanel-custom-css"')
        for marker in ('cyberpanel-schemes.css', 'id="page-head"', 'id="page-body"', 'id="page-footer"'):
            self.assertLess(html.index(marker), custom)
        self.assertNotIn('<style', html[html.index('</style>', custom) + 8:])

    def test_design_and_login_render_saved_css_last_without_duplication(self):
        for name in ('baseTemplate/design.html', 'loginSystem/login.html'):
            with self.subTest(template=name):
                html = self.engine.get_template(name).render(Context({
                    'cosmetic': {'MainDashboardCSS': PANEL_V3_STARTER}}))
                self.assertEqual(1, html.count('id="cyberpanel-custom-css"'))
                custom = html.index('id="cyberpanel-custom-css"')
                self.assertIn(PANEL_V3_STARTER, html[custom:])
                self.assertLess(html.index('cyberpanel-schemes.css'), custom)
                self.assertNotIn('<style', html[html.index('</style>', custom) + 8:])

    def test_empty_css_does_not_create_override_stylesheet(self):
        html = self.engine.get_template('baseTemplate/customCSS.html').render(Context({
            'cosmetic': {'MainDashboardCSS': ''}}))
        self.assertNotIn('<style', html)


class PanelStarterTests(unittest.TestCase):
    def get_theme(self, admin):
        path = Path(__file__).with_name('views.py')
        function = next(node for node in ast.parse(path.read_text()).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'getthemedata')
        requests = Mock()
        namespace = dict(json=json, requests=requests,
                         ACLManager=SimpleNamespace(loadedACL=lambda user: {'admin': admin},
                                                    loadErrorJson=lambda *args: 'denied'),
                         HttpResponse=lambda body: body)
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        response = namespace['getthemedata'](SimpleNamespace(
            session={'userID': 1}, body=json.dumps({'Themename': 'cyberpanel-3-starter'})))
        requests.get.assert_not_called()
        return response

    def test_current_starter_is_available_without_remote_theme_fetch(self):
        result = json.loads(self.get_theme(admin=1))
        self.assertEqual(1, result['status'])
        self.assertEqual(PANEL_V3_STARTER, result['csscontent'])

    def test_starter_preserves_admin_permission_check(self):
        self.assertEqual('denied', self.get_theme(admin=0))
