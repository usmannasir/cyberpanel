from unittest import TestCase, mock

from plogical import sslUtilities as module
from plogical.sslUtilities import issueSSLForDomain, sslUtilities


class AliasCertificateTests(TestCase):
    def test_alias_on_existing_parent_bypasses_parent_only_renewal(self):
        with mock.patch.object(module.os.path, 'exists', return_value=True), \
                mock.patch.object(sslUtilities, 'obtainSSLForADomain', return_value=1) as obtain, \
                mock.patch.object(sslUtilities, 'installSSLForDomain', return_value=1), \
                mock.patch.object(module.subprocess, 'run') as process, \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'):
            result = issueSSLForDomain('main.test', 'admin@example.com', '/webroot', 'alias.test')
        self.assertEqual(result[0], 1)
        obtain.assert_called_once_with('main.test', 'admin@example.com', '/webroot', 'alias.test', False, False)
        process.assert_not_called()

    def test_valid_parent_certificate_does_not_skip_alias_san_issuance(self):
        with mock.patch.object(sslUtilities, 'CheckIfSSLNeedsToBeIssued', return_value=0), \
                mock.patch.object(sslUtilities, 'PatchVhostConf'), \
                mock.patch.object(sslUtilities, 'checkDNSRecords', return_value=False), \
                mock.patch.object(sslUtilities, 'validateACMECertificate'), \
                mock.patch.object(module.os.path, 'exists', return_value=True), \
                mock.patch.object(module.ProcessUtilities, 'executioner'), \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'), \
                mock.patch('plogical.customACME.CustomACME') as acme:
            acme.return_value.issue_certificate.return_value = True
            result = sslUtilities.obtainSSLForADomain('main.test', 'admin@example.com', '/webroot', 'alias.test')
        self.assertEqual(result, 1)
        acme.return_value.issue_certificate.assert_called_once_with(['main.test', 'alias.test'], use_dns=False)
