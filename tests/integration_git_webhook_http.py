"""SSH-run HTTP acceptance using actual views, isolated secrets and no DB writes."""
import os
import tempfile
import threading
import subprocess
import json
from types import SimpleNamespace
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch
from wsgiref.simple_server import make_server
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
django.setup()
from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler
from django.urls import re_path
from websiteFunctions import views
from websiteFunctions.website import WebsiteManager

urlpatterns = [re_path(r'^websites/(?P<domain>[^/]+)/webhook$', views.webhook), re_path(r'^websites/(?P<domain>[^/]+)/gitNotify$', views.gitNotify)]
settings.ROOT_URLCONF = __name__
settings.MIDDLEWARE = []
settings.ALLOWED_HOSTS = ['127.0.0.1']
with tempfile.TemporaryDirectory() as folder:
    secret = Path(folder) / 'isolated.webhook_secret'
    with patch.object(WebsiteManager, 'webhookSecretPath', return_value=str(secret)):
        server = make_server('127.0.0.1', 0, WSGIHandler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for provisioned in (False, True):
                if provisioned:
                    secret.write_text('owned-test-secret')
                for endpoint in ('webhook', 'gitNotify'):
                    request = urllib.request.Request('http://127.0.0.1:%s/websites/owned-test.example/%s' % (server.server_port, endpoint), data=b'{}', headers={'Content-Type': 'application/json'})
                    try:
                        urllib.request.urlopen(request)
                        raise AssertionError('unauthenticated request accepted')
                    except urllib.error.HTTPError as response:
                        assert response.code == 403, response.code
                        print('%s, provisioned=%s: HTTP403, %s' % (endpoint, provisioned, response.read().decode()))
            remote = Path(folder) / 'origin'
            working = Path(folder) / 'working'
            subprocess.run(['git', 'init', '-q', str(remote)], check=True)
            subprocess.run(['git', '-C', str(remote), 'config', 'user.name', 'Owned QA'], check=True)
            subprocess.run(['git', '-C', str(remote), 'config', 'user.email', 'qa@example.invalid'], check=True)
            (remote / 'proof.txt').write_text('before')
            subprocess.run(['git', '-C', str(remote), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(remote), 'commit', '-qm', 'before'], check=True)
            subprocess.run(['git', 'clone', '-q', str(remote), str(working)], check=True)
            (remote / 'proof.txt').write_text('after')
            subprocess.run(['git', '-C', str(remote), 'commit', '-qam', 'after'], check=True)
            web = SimpleNamespace(domain='owned-test.example', externalApp='root')
            child = SimpleNamespace(path=str(working), master=web)
            with patch('websiteFunctions.website.Websites.objects.get', side_effect=LookupError), patch('websiteFunctions.website.ChildDomains.objects.get', return_value=child), patch('websiteFunctions.website.ACLManager.FetchExternalApp', return_value='root'), patch('websiteFunctions.website.GitLogs'), patch('websiteFunctions.website.os.mkdir') as mkdir:
                request = urllib.request.Request('http://127.0.0.1:%s/websites/owned-test.example/webhook' % server.server_port, data=b'{}', headers={'Content-Type': 'application/json', 'X-Webhook-Secret': 'owned-test-secret'})
                with urllib.request.urlopen(request) as response:
                    result = json.load(response)
                assert result['status'] == 1, result
                assert (working / 'proof.txt').read_text() == 'after'
                mkdir.assert_not_called()
                print('valid-secret webhook: HTTP200/status1; real Git pull advanced owned temporary repo and changed proof.txt from before to after; no configuration directory created.')
            print('PASS: isolated real HTTP routes, filesystem secrets and real Git; ORM records/log sink substituted with owned fixtures, no production DB write or installed runtime change.')
        finally:
            server.shutdown()
            server.server_close()
