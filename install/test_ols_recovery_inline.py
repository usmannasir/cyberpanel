"""Regression fixtures for recovery inspection; no native code or services run."""
import ast
from pathlib import Path, PurePosixPath
import re
import unittest

BASE = Path(__file__).resolve().parent
SOURCE = BASE / 'olsRecoveryPreflight.py'
NAMES = {'WAF_IP_SETTINGS', 'PANEL_INLINE_SETTINGS', 'WAF_FILE', 'WAF_INCLUDE', 'CRS_DIRECTORY'}
FUNCTIONS = {'offline_method_action', 'require_offline_crs_settings', 'require_full_waf_keys',
             'stock_config_policy', 'collect_waf_entries', 'waf_path'}
tree = ast.parse(SOURCE.read_text())
body = [n for n in tree.body if
        (isinstance(n, ast.FunctionDef) and n.name in FUNCTIONS) or
        (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in NAMES for t in n.targets))]
namespace = {'re': re, 'Path': PurePosixPath}
exec(compile(ast.Module(body=body, type_ignores=[]), str(SOURCE), 'exec'), namespace)
ROOT = PurePosixPath('/usr/local/lsws')
ACTION = 'SecAction "id:900000,phase:1,nolog,pass,t:none,setvar:tx.allowed_methods=GET HEAD POST OPTIONS PUT PATCH DELETE"'


def verify(documents):
    namespace['require_offline_crs_settings'](documents, ROOT)


def block(action, quote="'"):
    return 'module mod_security {\n modsecurity on\n modsecurity_rules ' + quote + '\nSecRuleEngine On\n' + action + '\n' + quote + '\n}\n'


class InlinePolicyTests(unittest.TestCase):
    def test_exact_customer_block_unchanged(self):
        text = (BASE / 'fixtures/quoted-api-methods.conf').read_text(encoding='utf-8')
        original = text.encode()
        verify([text])
        verify([text.replace('\n', '\r\n')])
        self.assertEqual(text.encode(), original)

    def test_all_native_quote_styles_for_engine(self):
        for quote in ('`', "'", '"'):
            with self.subTest(quote=quote):
                verify([block('', quote)])
                verify(['modsecurity_rules ' + quote + 'SecRuleEngine On' + quote])

    def test_method_action_in_single_and_backtick_blocks(self):
        for quote in ('`', "'"):
            verify([block(ACTION, quote)])

    def test_quoted_assignment_and_action_order(self):
        verify([block('SecAction "pass,nolog,id:900001,t:none,setvar:\'tx.allowed_methods=GET POST\',phase:1"', '`')])

    def test_default_panel_settings(self):
        verify([block('\n'.join([
            'SecDebugLogLevel 9', 'SecDebugLog /usr/local/lsws/logs/modsec.log',
            'SecAuditEngine RelevantOnly', 'SecAuditLogParts ABIJDEFHZ',
            'SecAuditLogType Serial', 'SecAuditLog /usr/local/lsws/logs/auditmodsec.log',
            'SecAuditLogRelevantStatus "^(?:5|4(?!04))"',
        ]), '`')])

    def test_multiple_documents_and_blocks(self):
        verify([block(ACTION), block('SecAuditEngine Off', '`') + block(ACTION, '`')])

    def test_malformed_or_ambiguous_quoting(self):
        for doc in [
            block(ACTION).replace("\n'\n", '\n`\n'),
            block(ACTION).replace("\n'\n", "\n' trailing\n"),
            block(ACTION, '"'),
            block(ACTION).replace('t:none', 't:\\none'),
            "modsecurity_rules 'SecRuleEngine On' 'SecAuditEngine Off'",
            "modsecurity_rules '\nSecRuleEngine On",
            'modsecurity_rules SecRuleEngine On',
        ]:
            with self.subTest(doc=doc), self.assertRaises(RuntimeError):
                verify([doc])

    def test_only_static_method_assignment_is_allowed(self):
        bad = [
            ACTION.replace('phase:1', 'phase:2'),
            ACTION.replace('nolog', 'log'),
            ACTION.replace('pass', 'deny'),
            ACTION.replace('t:none', 't:lowercase'),
            ACTION.replace('id:900000', 'id:0'),
            ACTION.replace('id:900000', 'id:2147483648'),
            ACTION.replace('t:none', 'phase:1'),
            ACTION.replace('tx.allowed_methods', 'tx.block_suspicious_ip'),
            ACTION.replace('GET HEAD POST OPTIONS PUT PATCH DELETE', '%{tx.other}'),
            ACTION.replace('GET HEAD POST OPTIONS PUT PATCH DELETE', 'GET|POST'),
            ACTION.replace('GET HEAD POST OPTIONS PUT PATCH DELETE', 'GET;POST'),
            ACTION.replace('setvar:', 'setvar:!'),
            ACTION[:-1] + ',setvar:tx.block_spammer_ip=1"',
            ACTION[:-1] + ',ctl:ruleEngine=Off"',
            ACTION[:-1] + ',exec:/tmp/helper"',
            ACTION.replace('tx.allowed_methods=', 'tx.allowed_methods=+'),
            ACTION.replace('tx.allowed_methods', 'ip.allowed_methods'),
            ACTION.replace('SecAction ', 'SecRule '),
        ]
        for action in bad:
            with self.subTest(action=action), self.assertRaises(RuntimeError):
                verify([block(action, '`')])

    def test_reputation_guard_retained(self):
        for line in ('SecHttpBlKey placeholder', 'SecGeoLookupDb /tmp/geo',
                     'SecAction "id:1,phase:1,pass,nolog,setvar:tx.block_search_ip=1"'):
            with self.subTest(line=line), self.assertRaisesRegex(RuntimeError, 'reputation dependencies'):
                verify([block(line)])

    def test_native_key_abbreviations_refused(self):
        for key in ('m', 'mods', 'modsecurity_r', 'MODSECURITY_RULES_F',
                    'modsecurity_rules_r', 'modsecurity_wrong'):
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'parameter'):
                verify([key + " '\nSecRuleEngine On\n'\n"])
        with self.assertRaisesRegex(RuntimeError, 'parameter'):
            verify(["modsecurity_\\\nrules '\nSecRuleEngine On\n'\n"])

    def test_action_whitespace_not_normalized(self):
        for action in (ACTION.replace(',phase', ', phase'),
                       ACTION.replace('900000,', '900000 ,'),
                       ACTION[:-1] + ' "'):
            with self.subTest(action=action), self.assertRaises(RuntimeError):
                verify([block(action)])

    def test_comment_quotes_are_ignored_like_native_parser(self):
        verify([block("# comments containing ' or ` or \\\n" + ACTION)])

    def test_native_assembled_parameter_forms_refused(self):
        for text in (
            "modsecurity\\\n_rules_remote key https://example.invalid/rules",
            'modsecurity_rules_f<<<END\n /tmp/rules.conf\nEND',
            'modsecurity_rules<<<END\n SecRuleEngine On\nEND',
            'param modsecurity_rules_file /tmp/rules.conf',
            "param 'modsecurity_rules_file /tmp/rules.conf'",
            "\vmodsecurity_r '\nSecRuleEngine On\n'",
            "\fmodsecurity_rules '\nSecRuleEngine On\n'",
            "modsecurity on\rmodsecurity_r '\nSecRuleEngine On\n'",
        ):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                verify([text])

    def test_secaction_ids_follow_native_semantics(self):
        # libmodsecurity permits repeated SecAction ids; unlike SecRule ids,
        # they do not replace or remove the inherited operator rules.
        verify([block(ACTION.replace('id:900000', 'id:911100'))])
        verify([block(ACTION + '\n' + ACTION)])

    def test_stock_cache_parameter_block(self):
        verify(['module cache {\nparam <<<END_param\nenableCache 1\nmaxCacheObjSize 10000000\nEND_param\n}\n'])
        for body in ('modsecurity_rules_file /tmp/rules.conf',
                     "modsecurity_rules '\nSecRuleEngine On\n'",
                     'modsecurity_r anything'):
            with self.subTest(body=body), self.assertRaisesRegex(RuntimeError, 'alternate parameter block'):
                verify(['param <<<END\n' + body + '\nEND\n'])

    def test_trailing_and_qualified_directives_refused(self):
        for text in ('}modsecurity_rules_remote key https://example.invalid/rules',
                     '} modsecurity_rules_file /tmp/rules.conf',
                     "} modsecurity_r 'SecRuleEngine Off'",
                     '} module third_party {',
                     'mod_security::modsecurity_rules_remote key https://example.invalid/rules'):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                verify([text])
            with self.subTest(policy='stock', text=text), self.assertRaises(RuntimeError):
                namespace['stock_config_policy'](text, ROOT)
        verify(['}\n} # stock closing brace with comment\n'])

    def test_shipped_stock_configuration_templates(self):
        templates = (BASE / 'litespeed/conf/httpd_config.conf',
                     BASE.parent / 'serverStatus/litespeed/conf/httpd_config.conf')
        if not all(path.exists() for path in templates):
            templates = (BASE / 'stock-httpd.conf', BASE / 'status-httpd.conf')
        for path in templates:
            with self.subTest(template=str(path)):
                namespace['stock_config_policy'](path.read_text(encoding='utf-8'), ROOT)


if __name__ == '__main__':
    unittest.main()
