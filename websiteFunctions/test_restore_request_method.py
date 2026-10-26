"""Only POST may reach the paid restore manager; CSRF is exercised natively."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
from django.http import HttpResponse
from django.test import RequestFactory
from django.views.decorators.http import require_POST

class RestoreRequestMethodTests(unittest.TestCase):
    def setUp(self):
        from django.conf import settings
        if not settings.configured:settings.configure(DEFAULT_CHARSET='utf-8')
        self.manager=Mock();self.plugin=Mock();self.plugin.preWebsiteCreation.return_value=200;self.plugin.postWebsiteCreation.return_value=200
        self.manager.return_value.RestoreWPbackupNow.return_value=HttpResponse('started')
        scope={'require_POST':require_POST,'json':json,'WebsiteManager':self.manager,'pluginManager':self.plugin}
        tree=ast.parse((Path(__file__).parent/'views.py').read_text());method=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='RestoreWPbackupNow')
        exec(compile(ast.Module(body=[method],type_ignores=[]),'restore-view','exec'),scope);self.view=scope['RestoreWPbackupNow']
    def test_safe_methods_do_not_reach_manager_or_plugin(self):
        for method in ('get','head'):
            request=getattr(RequestFactory(),method)('/websites/RestoreWPbackupNow');request.session={'userID':7}
            self.assertEqual(405,self.view(request).status_code)
        self.manager.assert_not_called();self.plugin.preWebsiteCreation.assert_not_called()
    def test_post_preserves_paid_manager_dispatch(self):
        data={'backupid':12,'DesSite':34};request=RequestFactory().post('/websites/RestoreWPbackupNow',data=json.dumps(data),content_type='application/json');request.session={'userID':7}
        self.assertEqual(b'started',self.view(request).content);self.manager.return_value.RestoreWPbackupNow.assert_called_once_with(7,data)
