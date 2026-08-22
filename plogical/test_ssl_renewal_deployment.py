"""
Regression coverage for the issue #1676 renewal path in plogical/sslUtilities.py.

acme.sh --renew only updates its own store under /root/.acme.sh. Unless the
renewed material is deployed into /etc/letsencrypt/live and LiteSpeed is
reloaded, the site keeps presenting the previous certificate until it expires.
These tests pin the command construction and, more importantly, prove that a
deployment failure is reported as a failure instead of being reported as a
successful renewal.

No certificate authority is contacted; every process call is mocked.

    python3 -m unittest plogical.test_ssl_renewal_deployment -v
"""

import unittest
from unittest import mock
import os

from plogical import sslUtilities as ssl_module
from plogical.sslUtilities import issueSSLForDomain, sslUtilities


DOMAIN = 'example.com'
ADMIN_EMAIL = 'admin@example.com'
LIVE_PATH = '/etc/letsencrypt/live/example.com'


class CompletedProcess(object):
    """Stand-in for subprocess.CompletedProcess with the attributes the
    renewal path reads."""

    def __init__(self, returncode=0, stdout='', stderr=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class RenewalDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.run_calls = []
        self.run_kwargs = []
        self.call_calls = []
        self.call_kwargs = []

        # Every path the renewal branch probes exists: the current certificate
        # and the acme.sh client.
        patcher = mock.patch.object(ssl_module.os.path, 'exists',
                                    return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        # The expiry probe opens the live certificate. Letting it raise takes
        # the documented "could not check expiry" path, which leaves the
        # certificate treated as not expired — the renew branch under test.
        log = mock.patch.object(ssl_module.logging.CyberCPLogFileWriter,
                                'writeToFile')
        self.log = log.start()
        self.addCleanup(log.stop)

        dns = mock.patch.object(sslUtilities, 'checkDNSRecords',
                                return_value=False)
        dns.start()
        self.addCleanup(dns.stop)

        install = mock.patch.object(sslUtilities, 'installSSLForDomain',
                                    return_value=1)
        self.install_vhost = install.start()
        self.addCleanup(install.stop)

        # A failed renewal legitimately falls through to fresh issuance. That
        # path reaches DNS and the ACME client, so it is stubbed out: these
        # tests are about the renewal branch, and nothing here may touch the
        # network.
        obtain = mock.patch.object(sslUtilities, 'obtainSSLForADomain',
                                   return_value=1)
        self.obtain_fresh = obtain.start()
        self.addCleanup(obtain.stop)

        call = mock.patch.object(ssl_module.subprocess, 'call',
                                 side_effect=self._record_call)
        call.start()
        self.addCleanup(call.stop)

    def _record_call(self, command, **kwargs):
        self.call_calls.append(command)
        self.call_kwargs.append(kwargs)
        return 0

    def _run_with(self, renew_rc=0, install_rc=0):
        """Drive the renewal path, returning (result, recorded commands)."""

        def fake_run(command, **kwargs):
            self.run_calls.append(command)
            self.run_kwargs.append(kwargs)
            if '--install-cert' in command:
                return CompletedProcess(install_rc, 'install out', 'install err')
            return CompletedProcess(renew_rc, 'renew out', 'renew err')

        with mock.patch.object(ssl_module.subprocess, 'run',
                               side_effect=fake_run):
            result = issueSSLForDomain(DOMAIN, ADMIN_EMAIL, '/home/example.com')
        return result, self.run_calls

    def _renew_command(self):
        for command in self.run_calls:
            if '--renew' in command or '--issue' in command:
                return command
        return None

    def _install_command(self):
        for command in self.run_calls:
            if '--install-cert' in command:
                return command
        return None

    # --- command construction -------------------------------------------

    def test_non_expired_renewal_targets_the_ecc_certificate(self):
        self._run_with()
        command = self._renew_command()
        self.assertIsNotNone(command)
        self.assertIn('--renew', command)
        self.assertIn('--ecc', command)
        self.assertIn('-d %s' % DOMAIN, command)

    def test_successful_renew_is_followed_by_install_cert(self):
        self._run_with()
        command = self._install_command()
        self.assertIsNotNone(command,
                             'a renewed certificate must be deployed')
        self.assertIn('--install-cert', command)
        self.assertIn('--ecc', command)

    def test_install_cert_writes_the_three_served_files(self):
        self._run_with()
        command = self._install_command()
        self.assertIn('--cert-file %s/cert.pem' % LIVE_PATH, command)
        self.assertIn('--key-file %s/privkey.pem' % LIVE_PATH, command)
        self.assertIn('--fullchain-file %s/fullchain.pem' % LIVE_PATH, command)

    def test_install_cert_registers_the_reload_command_for_acme_cron(self):
        self._run_with()
        command = self._install_command()
        self.assertIn('--reloadcmd', command)
        self.assertIn(sslUtilities.lswsReloadCmd, command)

    def test_reload_command_is_the_graceful_litespeed_reload(self):
        self.assertEqual(sslUtilities.lswsReloadCmd,
                         '/usr/local/lsws/bin/lswsctrl reload')

    def test_acme_processes_do_not_inherit_django_log_controls(self):
        with mock.patch.dict(os.environ, {
                'DEBUG': 'False', 'LOG_LEVEL': 'INFO',
                'CYBERPANEL_TEST_VALUE': 'preserved'}, clear=True):
            environment = sslUtilities.acmeEnvironment()

        self.assertNotIn('DEBUG', environment)
        self.assertNotIn('LOG_LEVEL', environment)
        self.assertEqual('preserved', environment['CYBERPANEL_TEST_VALUE'])

        with mock.patch.dict(os.environ, {
                'DEBUG': 'False', 'LOG_LEVEL': 'INFO'}, clear=False):
            self._run_with()

        for kwargs in self.call_kwargs + self.run_kwargs:
            self.assertNotIn('DEBUG', kwargs['env'])
            self.assertNotIn('LOG_LEVEL', kwargs['env'])

    # --- failure behaviour ----------------------------------------------

    def test_failed_renewal_deploys_nothing_and_falls_back_to_issuance(self):
        result, _ = self._run_with(renew_rc=1)
        self.assertIsNone(self._install_command(),
                          'nothing may be deployed when the renew failed')
        self.assertNotEqual(result[1], 'SSL successfully renewed',
                            'a failed renew must not be reported as renewed')
        # Falling through to a fresh issue is the intended recovery.
        self.obtain_fresh.assert_called_once()

    def test_failed_deployment_is_not_reported_as_a_successful_renewal(self):
        """The #1676 symptom itself: acme.sh renewed, the copy into
        /etc/letsencrypt/live failed, and the site is still serving the old
        certificate. Returning success here hides it until the cert expires."""
        result, _ = self._run_with(install_rc=1)
        self.assertNotEqual(
            result[0], 1,
            'a renewal whose deployment failed must not report success')
        self.assertIn('deployment', result[1].lower())

    def test_failed_deployment_does_not_install_the_vhost_configuration(self):
        self._run_with(install_rc=1)
        self.install_vhost.assert_not_called()

    def test_failed_deployment_is_logged_with_the_exit_code(self):
        self._run_with(install_rc=1)
        logged = ' '.join(str(c) for c in self.log.call_args_list)
        self.assertIn('could not be deployed', logged)

    def test_successful_deployment_reports_success(self):
        result, _ = self._run_with()
        self.assertEqual(result[0], 1)
        self.install_vhost.assert_called_once()


class ExpiredCertificateTests(unittest.TestCase):
    """An expired certificate cannot be renewed; acme.sh has to re-issue it,
    and the re-issue must still ask for an ECC key or the next renewal looks
    for an RSA certificate that was never created."""

    def setUp(self):
        self.run_calls = []

        patcher = mock.patch.object(ssl_module.os.path, 'exists',
                                    return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        log = mock.patch.object(ssl_module.logging.CyberCPLogFileWriter,
                                'writeToFile')
        log.start()
        self.addCleanup(log.stop)

        for name in ('checkDNSRecords',):
            p = mock.patch.object(sslUtilities, name, return_value=False)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(sslUtilities, 'installSSLForDomain',
                              return_value=1)
        p.start()
        self.addCleanup(p.stop)

        p = mock.patch.object(ssl_module.subprocess, 'call', return_value=0)
        p.start()
        self.addCleanup(p.stop)

    @staticmethod
    def _expired_certificate_pem():
        from OpenSSL import crypto
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)
        cert = crypto.X509()
        cert.get_subject().CN = DOMAIN
        cert.set_issuer(cert.get_subject())
        cert.set_serial_number(1)
        # Valid from two years ago until one year ago.
        cert.gmtime_adj_notBefore(-2 * 365 * 24 * 3600)
        cert.gmtime_adj_notAfter(-365 * 24 * 3600)
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')
        return crypto.dump_certificate(crypto.FILETYPE_PEM, cert)

    def test_expired_certificate_is_reissued_with_an_ecc_key(self):
        pem = self._expired_certificate_pem()

        def fake_run(command, **kwargs):
            self.run_calls.append(command)
            return CompletedProcess(0, '', '')

        with mock.patch('builtins.open', mock.mock_open(read_data=pem)), \
                mock.patch.object(ssl_module.subprocess, 'run',
                                  side_effect=fake_run):
            issueSSLForDomain(DOMAIN, ADMIN_EMAIL, '/home/example.com')

        issue = [c for c in self.run_calls if '--issue' in c]
        self.assertTrue(issue, 'an expired certificate must be re-issued')
        self.assertIn('-k ec-256', issue[0])
        self.assertIn('--force', issue[0])
        self.assertFalse([c for c in self.run_calls if '--renew' in c],
                         'an expired certificate cannot be renewed')


if __name__ == '__main__':
    unittest.main()
