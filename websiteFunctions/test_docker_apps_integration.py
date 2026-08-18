"""Integration tests for the Hermes Docker app, these talk to a real Docker engine.

They stand the app up exactly the way CyberPanel does, on a scratch project name and
a loopback port, then tear it down again. No website, vhost or DockerSites row is touched.

    DOCKER_APPS_INTEGRATION=1 /usr/local/CyberCP/bin/python -m unittest \
        websiteFunctions.test_docker_apps_integration -v
"""

import json
import os
import shutil
import subprocess
import time
import unittest
import urllib.error
import urllib.request

from websiteFunctions.test_docker_apps import make_site

INTEGRATION = os.getenv('DOCKER_APPS_INTEGRATION') == '1'
WORKDIR = '/tmp/hermes-integration'
PROJECT = 'hermes-integration'
PORT = '19119'


def compose(*args, check=True):
    return subprocess.run(['docker', 'compose', '-f', f'{WORKDIR}/docker-compose.yml', '-p', PROJECT] + list(args),
                          capture_output=True, text=True, timeout=900, check=check)


@unittest.skipUnless(INTEGRATION, 'set DOCKER_APPS_INTEGRATION=1 to run')
class TestHermesDeployment(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.site = make_site('Hermes')
        cls.site.data['port'] = PORT
        cls.site.data['finalURL'] = 'hermes-integration.local'
        cls.site.data['ServiceName'] = 'hermesit'
        cls.site.data['SiteName'] = 'hermesit'

        shutil.rmtree(WORKDIR, ignore_errors=True)
        os.makedirs(f'{WORKDIR}/data', exist_ok=True)

        composeConfig = cls.site.generate_hermes_compose_config()
        ## The volume path is derived from the domain, point it at the scratch dir.
        composeConfig = composeConfig.replace(f"/home/docker/{cls.site.data['finalURL']}/data", f'{WORKDIR}/data')

        with open(f'{WORKDIR}/docker-compose.yml', 'w') as composeFile:
            composeFile.write(composeConfig)

        compose('up', '-d')
        cls.status = cls.waitForDashboard()

    @classmethod
    def waitForDashboard(cls, timeout=300):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/status', timeout=5) as answer:
                    return json.loads(answer.read())
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                time.sleep(5)
        return None

    @classmethod
    def tearDownClass(cls):
        compose('down', '-v', check=False)
        shutil.rmtree(WORKDIR, ignore_errors=True)

    def test_compose_file_is_valid(self):
        parsed = compose('config', '--format', 'json')
        service = json.loads(parsed.stdout)['services']['hermesit']
        self.assertEqual(service['image'], 'nousresearch/hermes-agent:latest')

    def test_container_is_running(self):
        state = compose('ps', '--format', 'json').stdout.strip().splitlines()
        self.assertTrue(state, 'no container in the project')
        self.assertIn('running', state[0].lower())

    def test_dashboard_answers_with_the_auth_gate_engaged(self):
        ## Hermes fails closed on a non loopback bind, if the credentials we pass are
        ## wrong or missing the container exits instead of serving an open admin panel.
        self.assertIsNotNone(self.status,
                             f'dashboard never came up, logs:\n{compose("logs", check=False).stdout[-2000:]}')
        self.assertTrue(self.status.get('auth_required'), f'dashboard is unauthenticated: {self.status}')
        self.assertIn('basic', self.status.get('auth_providers', []))

    def test_dashboard_rejects_anonymous_requests(self):
        request = urllib.request.Request(f'http://127.0.0.1:{PORT}/api/system/stats')
        with self.assertRaises(urllib.error.HTTPError) as rejected:
            urllib.request.urlopen(request, timeout=10)
        self.assertIn(rejected.exception.code, (401, 403))

    def test_configured_credentials_authenticate(self):
        ## The panel hands Hermes the admin username and password from the creation form,
        ## these are the credentials the customer logs into the dashboard with.
        def login(password):
            payload = json.dumps({'provider': 'basic',
                                  'username': self.site.data['adminUser'],
                                  'password': password}).encode()
            request = urllib.request.Request(f'http://127.0.0.1:{PORT}/auth/password-login', data=payload,
                                             headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(request, timeout=10) as answer:
                    return answer.status, answer.headers.get_all('Set-Cookie') or []
            except urllib.error.HTTPError as failed:
                return failed.code, []

        code, cookies = login(self.site.data['adminPassword'])
        self.assertEqual(code, 200)
        self.assertTrue(any('hermes_session_at' in cookie for cookie in cookies))

        self.assertEqual(login('not-the-password')[0], 401)

    def test_state_lands_in_the_mounted_volume(self):
        self.assertTrue(os.listdir(f'{WORKDIR}/data'), 'nothing was written to /opt/data')


if __name__ == '__main__':
    unittest.main()
