import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


source = Path(__file__).with_name('virtualHostUtilities.py').read_text()
cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef)
           and n.name == 'virtualHostUtilities')


def function(name, namespace):
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(module, '<actual mail TLS helper>', 'exec'), namespace)
    return namespace[name]


class MailTLSAvailabilityTests(unittest.TestCase):
    def test_real_validator_controls_availability(self):
        ssl, logger = Mock(), Mock()
        validate = function('hasUsableMailTLS', {'sslUtilities':ssl, 'logging':logger})
        self.assertTrue(validate('fixture.example'))
        ssl.validateACMECertificate.assert_called_with(
            '/etc/letsencrypt/live/fixture.example/fullchain.pem',
            '/etc/letsencrypt/live/fixture.example/privkey.pem')
        for failure in (FileNotFoundError(), ValueError('invalid certificate')):
            ssl.validateACMECertificate.side_effect = failure
            self.assertFalse(validate('fixture.example'))

    def test_missing_root_tls_stops_before_config_changes_or_service_calls(self):
        host, process, logger = Mock(), Mock(), Mock()
        host.emailServicesInstalled.return_value = True
        host.hasUsableMailTLS.return_value = False
        setup = function('setupAutoDiscover', {
            'virtualHostUtilities':host, 'ProcessUtilities':process, 'logging':logger})
        with patch('builtins.open', side_effect=AssertionError('no config writes allowed')):
            setup(True, '/unused', 'fixture.example', SimpleNamespace(userName='admin'))
        host.createDomain.assert_not_called()
        process.executioner.assert_not_called()

    def test_child_sni_block_is_guarded_independently(self):
        node = next(n for n in cls.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'setupAutoDiscover')
        branch = next(n for n in node.body if isinstance(n, ast.If)
                      and isinstance(n.test, ast.Name) and n.test.id == 'mailDomain')
        guarded = [n for n in branch.body if isinstance(n, ast.If)
                   and 'hasUsableMailTLS(childDomain)' in ast.get_source_segment(source, n.test)]
        self.assertEqual(1, len(guarded))
        self.assertIn('getDovecotSNIBlock', ast.get_source_segment(source, guarded[0]))
        self.assertIn('postmap', ast.get_source_segment(source, guarded[0]))


if __name__ == '__main__':
    unittest.main()
