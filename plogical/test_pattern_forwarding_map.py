"""Pattern forwarding rules reach Postfix as a map it uses, and nothing typed into a rule escapes its line."""
import ast
import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plogical import patternForwardingMap as pattern_map  # noqa: E402

DOMAIN = 'example.com'
DESTINATION = 'qa@example.com'


def line(pattern, pattern_type='wildcard', domain=DOMAIN, destination=DESTINATION):
    return pattern_map.rule_line(pattern_type, pattern, domain, destination)


class TranslationTests(unittest.TestCase):
    def refused(self, *arguments, **named):
        with self.assertRaises(pattern_map.RuleError):
            line(*arguments, **named)

    def test_wildcard_becomes_one_line_tied_to_its_domain(self):
        self.assertEqual('/^(support_[^@]*)@example\\.com$/ qa@example.com', line('support_*'))
        self.assertEqual('/^(a\\.b\\+c[^@]x-y=z)@mail\\.example\\.com$/ Some.One+tag@other.example',
                         line('a.b+c?x-y=z', domain='Mail.Example.COM', destination='Some.One+tag@other.example'))

    def test_examples_shown_on_the_page_are_accepted(self):
        self.assertEqual('/^(user_[^@]*)@example\\.com$/ qa@example.com', line('user_*'))
        self.assertEqual('/^(support-[^@])@example\\.com$/ qa@example.com', line('support-?'))
        self.assertEqual('/^(team[^@]*)@example\\.com$/ qa@example.com', line('team*'))
        self.assertEqual('/^(user_[0-9]+)@example\\.com$/ qa@example.com', line('user_[0-9]+', 'regex'))
        self.assertEqual('/^(support-(sales|billing))@example\\.com$/ qa@example.com',
                         line('support-(sales|billing)', 'regex'))

    def test_hostile_wildcards_are_refused(self):
        for pattern in ('', ' ', 'a b', 'a\tb', 'a\nb', 'support_*\n/.*/ thief@evil.test', 'a/b', 'a|b', '(a', 'a)',
                        'a$', '^a', 'a\\', '[a]', 'a{2}', 'a@evil.test', 'a@example.com, b', 'a,b', 'a;b', 'a"b',
                        "a'b", 'a#b', 'café*', 'a\x00b', 'x' * 201, None, 7, ['a']):
            with self.subTest(pattern=pattern):
                self.refused(pattern)

    def test_hostile_destinations_are_refused(self):
        for destination in ('', 'qa', '@example.com', 'qa@', 'qa@example', 'qa@example.com, thief@evil.test',
                            'qa@example.com thief@evil.test', 'qa@example.com\n/.*/ thief@evil.test',
                            'qa@example.com\n', ' qa@example.com', '$1@example.com', '${1}@example.com',
                            'qa@$1', 'qa@a@example.com', '|/bin/sh', 'qa|x@example.com', 'qa@example.com/',
                            '"a b"@example.com', 'qa@exa mple.com', 'qa@example.com.', 'qa@-example.com',
                            'q\\a@example.com', 'qa@example.com#x', 'x' * 250 + '@example.com', None):
            with self.subTest(destination=destination):
                self.refused('support_*', destination=destination)

    def test_hostile_domains_are_refused(self):
        for domain in ('', 'example', 'example.com$/ thief@evil.test', 'example.com|evil.test', 'exa mple.com',
                       'example.com\n', '.*', 'example..com', 'example.com/', '(example.com)', 'a_b.com', None):
            with self.subTest(domain=domain):
                self.refused('support_*', domain=domain)

    def test_regular_expression_is_grouped_and_tied_to_its_domain(self):
        self.assertEqual('/^((sales|support)-[0-9]{1,4})@example\\.com$/ qa@example.com',
                         line('(sales|support)-[0-9]{1,4}', 'regex'))
        for pattern in ('support_.*', '[^@]+', 'order\\.[[:digit:]]+', 'a\\+b', '[]()]x', '[^]]+', 'a\\(b', 'a|b',
                        '\\{x\\}', 'x{3,}', '$|^.*', 'a{16}', 'a{8}b{8}', '[0-9]{4}-[0-9]{4}-[0-9]{4}',
                        'a*b*c*d*e*f*g*h*', 'a+b+c+d+e{2,}f{0,}g*h*', '(a|b)*', '(ab?)+c*', '(a?)*',
                        '(a*)?b', '((((a))))', 'colou?r', 'a?' * 16, 'x' * 100):
            with self.subTest(pattern=pattern):
                self.assertEqual('/^(%s)@example\\.com$/ qa@example.com' % pattern, line(pattern, 'regex'))

    def test_hostile_regular_expressions_are_refused(self):
        for pattern in ('', '.*@evil\\.test|x', 'a)|(.*', 'a|b)(c', '(a', '((a)', 'a)', 'a\\', '\\d+', '\\w+', '\\1',
                        '(a)\\1', 'a/b', 'a\\/b', 'a b', 'a\nb', 'a\n/.*/ thief@evil.test', '(?i)a', '(?:a)', '[a',
                        '[]', '[\\]]', '[[:foo:]]', '[[.a.]]', '[[=a=]]', 'a{', 'a{x}', 'a{,3}', 'a{99999}',
                        'a{1,256}', '(ab){3}', 'café', 'x' * 201, None):
            with self.subTest(pattern=pattern):
                self.refused(pattern, 'regex')

    def test_stacked_repeats_are_refused(self):
        # The C library multiplies a repeat that follows another; these were measured in minutes and
        # hundreds of megabytes. They are refused by reading the pattern, nothing is compiled.
        for pattern in ('a{0,255}{0,60}', '(a{255})?{255}', 'a{2}{3}', 'a{2}{2}{2}', 'a**', 'a*+', 'a+*', 'a+?',
                        'a*?', 'a?*', 'a??', 'a?+', 'a{2}*', 'a{2}+', 'a{2}?', 'a*{2}', 'a+{2}', 'a?{2}',
                        '(a)?{2}', '(a)*{2}', '(a)+*', '[ab]{2}{2}', '\\.{2}{2}'):
            with self.subTest(pattern=pattern):
                self.refused(pattern, 'regex')

    def test_repeats_inside_repeated_groups_are_refused(self):
        for pattern in ('(a*)*', '(a+)+', '(a*)+', '(a+)*', '(a{2})*', '(a{2})+', '(a{2,})*', '((a*)b)*',
                        '((a+)?)*', '(a|(b+))*', '((a|b)*c)+', '(a{2}){2}', '(a*){2}', '((a){2})'):
            with self.subTest(pattern=pattern):
                self.refused(pattern, 'regex')

    def test_repeat_with_nothing_to_repeat_is_refused(self):
        for pattern in ('*a', '+a', '?a', '{2}a', '(*a)', '(+a)', 'a|*b', 'a|+', '^*', '$+', '^{2}', '(|?)'):
            with self.subTest(pattern=pattern):
                self.refused(pattern, 'regex')

    def test_total_repetition_of_a_pattern_is_bounded(self):
        self.assertEqual(16, pattern_map.MAX_COUNTED)
        self.assertEqual(8, pattern_map.MAX_UNBOUNDED)
        self.assertEqual(4, pattern_map.MAX_GROUP_DEPTH)
        self.assertEqual(100, pattern_map.MAX_PATTERN_LENGTH)
        for pattern in ('a{17}', 'a{0,17}', 'a{255}', 'a{0,255}', 'a{9}b{8}', 'a{16}b?', 'a{16}b{1}', 'a?' * 17,
                        'a{2}' * 9, 'a{5,2}', 'a{1000}', 'a*b*c*d*e*f*g*h*i*', 'a+' * 9, 'a{1,}' * 9,
                        'a*b*c*d*e*f*g*h*i{2,}', '(((((a)))))', 'x' * 101, '[a-z]' * 21):
            with self.subTest(pattern=pattern):
                self.refused(pattern, 'regex')

    def test_wildcards_stay_within_the_same_bounds(self):
        self.assertEqual('/^(a[^@]*b)@example\\.com$/ qa@example.com', line('a****b'))
        self.assertEqual(8, line('*a*b*c*d*e*f*g*').count('[^@]*'))
        self.assertTrue(line('x' * 100))
        for pattern in ('*a*b*c*d*e*f*g*h*', 'x' * 101, '*' * 101):
            with self.subTest(pattern=pattern):
                self.refused(pattern)

    def test_unknown_pattern_type_is_refused(self):
        self.refused('support_*', 'glob')
        self.refused('support_*', None)

    @unittest.skipUnless(shutil.which('grep'), 'needs grep for POSIX extended expressions')
    def test_accepted_patterns_match_their_own_domain_only(self):
        """The expressions are run by grep -E, which reads them as Postfix's regexp tables do."""
        own = ['support_a@example.com', 'SUPPORT_b@Example.COM', 'a@example.com', 'x@example.com', '.@example.com']
        foreign = ['support_a@evil.test', 'support_a@example.com.evil.test', 'support_a@xexample.com',
                   'a@evil.test', 'x@evil.test', 'thief@evil.test', 'support_a@example.com@evil.test',
                   'a@example-com', 'a@examplexcom']
        patterns = [('wildcard', item) for item in ('support_*', '*', '?', 'a.b', '*+*')]
        patterns += [('regex', item) for item in ('support_.*', '.*', 'a|.*', '(a|b)|.*', '$|^.*', 'x|', '[)]|.*',
                                                  '[]()]|.*', '\\)|.*', '.*\\\\', '[^@]+', 'a|[^@]*')]
        with tempfile.TemporaryDirectory() as directory:
            addresses = Path(directory, 'addresses')
            addresses.write_text('\n'.join(own + foreign) + '\n')
            for pattern_type, pattern in patterns:
                with self.subTest(pattern=pattern):
                    expression = line(pattern, pattern_type).split(' ')[0]
                    self.assertTrue(expression.startswith('/') and expression.endswith('/'))
                    done = subprocess.run(['grep', '-E', '-i', '-e', expression[1:-1], str(addresses)],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                    self.assertIn(done.returncode, (0, 1), done.stderr)
                    self.assertEqual([], [found for found in done.stdout.split() if found in foreign])
        with tempfile.TemporaryDirectory() as directory:
            addresses = Path(directory, 'addresses')
            addresses.write_text('\n'.join(own + foreign) + '\n')
            done = subprocess.run(['grep', '-E', '-i', '-e', line('support_*').split(' ')[0][1:-1], str(addresses)],
                                  stdout=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(['support_a@example.com', 'SUPPORT_b@Example.COM'], done.stdout.split())


class AliasMapSettingTests(unittest.TestCase):
    reference = 'regexp:/etc/postfix/virtual_regexp'
    shipped = 'proxy:mysql:/etc/postfix/mysql-virtual_forwardings.cf, mysql:/etc/postfix/mysql-virtual_email2email.cf'

    def placed(self, value):
        return pattern_map.alias_maps_with_reference(value, self.reference)

    def test_reference_is_added_after_the_maps_that_answer_exact_addresses(self):
        self.assertEqual(self.shipped + ', ' + self.reference, self.placed(self.shipped))
        self.assertEqual(self.reference, self.placed(''))
        self.assertEqual('$virtual_maps, ' + self.reference, self.placed('$virtual_maps'))
        self.assertEqual('hash:/etc/postfix/virtual mysql:/x.cf, ' + self.reference,
                         self.placed('hash:/etc/postfix/virtual mysql:/x.cf'))

    def test_value_that_already_ends_with_the_reference_is_kept(self):
        for value in (self.shipped + ', ' + self.reference, self.reference, 'hash:/a ' + self.reference):
            self.assertEqual(value, self.placed(value))

    def test_reference_found_elsewhere_moves_behind_the_other_entries(self):
        self.assertEqual(self.shipped + ', ' + self.reference, self.placed(self.reference + ',' + self.shipped))
        self.assertEqual(self.shipped + ', ' + self.reference, self.placed(self.reference + ', ' + self.shipped))
        self.assertEqual('hash:/a, hash:/b, ' + self.reference, self.placed('hash:/a, %s, hash:/b' % self.reference))
        self.assertEqual('hash:/a, ' + self.reference,
                         self.placed('%s, hash:/a, %s' % (self.reference, self.reference)))

    def test_maps_with_similar_names_are_other_entries(self):
        value = 'regexp:/etc/postfix/virtual_regexp.local, pcre:/etc/postfix/virtual_regexp'
        self.assertEqual(value + ', ' + self.reference, self.placed(value))


class FakePostfix:
    """Stands in for postconf, postmap and postfix; no real command is run."""

    def __init__(self, value):
        self.value = value
        self.commands = []
        self.running = True
        self.refuse = {}
        self.fatal = None
        self.edit_fails = False
        self.reload_fails = False
        self.checked = []
        self.main_cf = None
        self.slow = ()
        self.stalled = False
        self.timeouts = []
        self.edits_left = None

    def __call__(self, command, timeout=None):
        name, arguments = os.path.basename(command[0]), list(command[1:])
        self.commands.append([name] + arguments)
        if name == 'postconf' and arguments[0] == '-h':
            return 0, self.value + '\n', ''
        if name == 'postconf' and arguments[0] == '-e':
            if self.edit_fails or self.edits_left == 0:
                return 1, '', 'postconf: fatal: open /etc/postfix/main.cf.tmp: Permission denied\n'
            if self.edits_left is not None:
                self.edits_left -= 1
            self.value = arguments[1].split(' = ', 1)[1]
            if self.main_cf:
                # postconf writes a new file in place of the old one.
                replacement = Path(str(self.main_cf) + '.tmp')
                replacement.write_text('virtual_alias_maps = %s\n' % self.value)
                replacement.chmod(0o600)
                os.replace(str(replacement), str(self.main_cf))
            return 0, '', ''
        if name == 'postmap':
            path = arguments[2][len('regexp:'):]
            self.checked.append(Path(path).read_text())
            self.timeouts.append(timeout)
            if self.stalled or any(needle in self.checked[-1] for needle in self.slow):
                # As subprocess.run does when the time is up; the real one also ends the command.
                raise subprocess.TimeoutExpired(command, timeout)
            if self.fatal:
                return 1, '', 'postmap: fatal: %s\n' % self.fatal
            warnings = ''
            for number, text in enumerate(self.checked[-1].splitlines(), 1):
                for needle, reason in self.refuse.items():
                    if needle in text:
                        warnings += 'postmap: warning: regexp map %s, line %s: %s\n' % (path, number, reason)
            return 1, '', 'postmap: warning: /etc/postfix/main.cf, line 9: overriding earlier entry\n' + warnings
        if name == 'postfix' and arguments == ['status']:
            return (0 if self.running else 1), '', ''
        if name == 'postfix' and arguments == ['reload']:
            return (1, '', 'postfix/postfix-script: fatal: reload failed\n') if self.reload_fails else (0, '', '')
        raise AssertionError('unexpected command %r' % (command,))

    def count(self, *start):
        return len([command for command in self.commands if command[:len(start)] == list(start)])


class ApplyTests(unittest.TestCase):
    shipped = AliasMapSettingTests.shipped

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.map = Path(self.directory.name, 'virtual_regexp')
        self.main_cf = Path(self.directory.name, 'main.cf')
        self.main_cf.write_text('virtual_alias_maps = %s\n' % self.shipped)
        self.postfix = FakePostfix(self.shipped)
        self.rules = [(1, DOMAIN, 'support_*', DESTINATION, 'wildcard')]
        self.disabled = []

    def apply(self):
        return pattern_map.apply(lambda: self.rules, self.postfix, str(self.map), str(self.main_cf),
                                 self.disabled.extend)

    def leftovers(self):
        return sorted(name for name in os.listdir(self.directory.name) if name not in ('main.cf', 'virtual_regexp'))

    def test_server_without_rules_is_left_untouched(self):
        self.rules = []
        self.assertEqual({'state': 'not in use', 'rejected': []}, self.apply())
        self.assertFalse(self.map.exists())
        self.assertEqual([['postconf', '-h', 'virtual_alias_maps']], self.postfix.commands)

    def test_server_without_postfix_is_left_untouched(self):
        self.main_cf.unlink()
        self.assertEqual({'state': 'no mail server', 'rejected': []}, self.apply())
        self.assertEqual([], self.postfix.commands)

    def test_rules_are_written_listed_last_and_loaded(self):
        self.rules.append((2, 'other.example', 'billing-[0-9]+', 'accounts@other.example', 'regex'))
        self.assertEqual({'state': 'updated', 'rejected': []}, self.apply())
        self.assertEqual(pattern_map.HEADER
                         + '/^(support_[^@]*)@example\\.com$/ qa@example.com\n'
                         + '/^(billing-[0-9]+)@other\\.example$/ accounts@other.example\n', self.map.read_text())
        self.assertEqual(0o640, stat.S_IMODE(self.map.stat().st_mode))
        self.assertEqual('%s, regexp:%s' % (self.shipped, self.map), self.postfix.value)
        self.assertEqual([self.map.read_text()], self.postfix.checked)
        # The file is in place before Postfix is told about it, and the reload comes last.
        self.assertEqual(['postconf', 'postmap', 'postconf', 'postfix', 'postfix'],
                         [command[0] for command in self.postfix.commands])
        self.assertEqual(['postfix', 'reload'], self.postfix.commands[-1])
        self.assertEqual([], self.leftovers())

    def test_main_cf_stays_readable_as_before(self):
        self.main_cf.chmod(0o644)
        self.postfix.main_cf = self.main_cf
        self.apply()
        self.assertEqual(0o644, stat.S_IMODE(self.main_cf.stat().st_mode))
        self.assertIn('regexp:%s' % self.map, self.main_cf.read_text())

    def test_second_run_changes_nothing(self):
        self.apply()
        self.postfix.commands = []
        before = self.map.stat().st_mtime_ns
        self.assertEqual({'state': 'unchanged', 'rejected': []}, self.apply())
        self.assertEqual(before, self.map.stat().st_mtime_ns)
        self.assertEqual(0, self.postfix.count('postconf', '-e'))
        self.assertEqual(0, self.postfix.count('postfix'))
        self.assertEqual([], self.leftovers())

    def test_changed_and_deleted_rules_replace_the_map(self):
        self.apply()
        self.rules = [(3, DOMAIN, 'sales_*', DESTINATION, 'wildcard')]
        self.assertEqual('updated', self.apply()['state'])
        self.assertNotIn('support_', self.map.read_text())
        self.assertIn('sales_', self.map.read_text())
        self.rules = []
        self.assertEqual('updated', self.apply()['state'])
        self.assertEqual(pattern_map.HEADER, self.map.read_text())
        self.assertTrue(self.postfix.value.endswith('regexp:%s' % self.map))
        self.assertEqual(3, self.postfix.count('postfix', 'reload'))
        self.assertEqual(1, self.postfix.count('postconf', '-e'))

    def test_reference_placed_first_by_hand_moves_behind_the_exact_maps(self):
        self.postfix.value = 'regexp:%s, %s' % (self.map, self.shipped)
        self.assertEqual('updated', self.apply()['state'])
        self.assertEqual('%s, regexp:%s' % (self.shipped, self.map), self.postfix.value)

    def test_listed_map_that_was_never_written_gets_its_file(self):
        self.rules = []
        self.postfix.value = '%s, regexp:%s' % (self.shipped, self.map)
        self.assertEqual('updated', self.apply()['state'])
        self.assertEqual(pattern_map.HEADER, self.map.read_text())

    def test_stopped_postfix_is_not_reloaded(self):
        self.postfix.running = False
        self.assertEqual('updated', self.apply()['state'])
        self.assertEqual(0, self.postfix.count('postfix', 'reload'))

    def test_saved_rule_that_cannot_be_written_is_reported_and_left_out(self):
        self.rules = [(4, DOMAIN, 'x\n/.*/ thief@evil.test', DESTINATION, 'wildcard'),
                      (5, DOMAIN, '.*@evil\\.test|x', DESTINATION, 'regex'),
                      (6, DOMAIN, 'support_*', 'qa@example.com, thief@evil.test', 'wildcard'),
                      (7, DOMAIN, 'support_*', DESTINATION, 'wildcard')]
        result = self.apply()
        self.assertEqual('updated', result['state'])
        self.assertEqual([4, 5, 6], [refused['id'] for refused in result['rejected']])
        self.assertEqual([4, 5, 6], self.disabled)
        # Refusing them took no command beyond those for the map itself.
        self.assertEqual(1, self.postfix.count('postmap'))
        self.assertEqual(pattern_map.HEADER + '/^(support_[^@]*)@example\\.com$/ qa@example.com\n',
                         self.map.read_text())
        self.assertNotIn('evil', self.map.read_text())

    def test_rule_postfix_cannot_compile_is_reported_and_left_out(self):
        self.rules = [(8, DOMAIN, '[b-a]x', DESTINATION, 'regex'), (9, DOMAIN, 'support_*', DESTINATION, 'wildcard'),
                      (10, DOMAIN, '[d-c]x', DESTINATION, 'regex')]
        self.postfix.refuse = {'[b-a]': 'Invalid range end', '[d-c]': 'Invalid range end'}
        result = self.apply()
        self.assertEqual('updated', result['state'])
        self.assertEqual([8, 10], sorted(refused['id'] for refused in result['rejected']))
        self.assertEqual([8, 10], sorted(self.disabled))
        self.assertIn('Invalid range end', result['rejected'][0]['reason'])
        self.assertEqual(pattern_map.HEADER + '/^(support_[^@]*)@example\\.com$/ qa@example.com\n',
                         self.map.read_text())
        self.assertEqual(self.map.read_text(), self.postfix.checked[-1])
        self.assertEqual([], self.leftovers())
        self.postfix.commands = []
        self.assertEqual('unchanged', self.apply()['state'])
        self.assertEqual(0, self.postfix.count('postfix'))

    def test_map_postfix_cannot_read_is_not_installed(self):
        self.apply()
        installed, value = self.map.read_text(), self.postfix.value
        self.rules.append((11, DOMAIN, 'sales_*', DESTINATION, 'wildcard'))
        self.postfix.fatal = 'unsupported dictionary type: regexp'
        self.postfix.commands = []
        with self.assertRaises(pattern_map.MapError) as raised:
            self.apply()
        self.assertIn('unsupported dictionary type', str(raised.exception))
        self.assertEqual(installed, self.map.read_text())
        self.assertEqual(value, self.postfix.value)
        self.assertEqual(0, self.postfix.count('postfix'))
        self.assertEqual([], self.leftovers())

    def test_refused_write_is_an_error(self):
        with mock.patch.object(pattern_map.tempfile, 'mkstemp',
                               side_effect=PermissionError(13, 'Permission denied', str(self.map))):
            with self.assertRaises(pattern_map.MapError) as raised:
                self.apply()
        self.assertIn('Permission denied', str(raised.exception))
        self.assertFalse(self.map.exists())
        self.assertEqual(self.shipped, self.postfix.value)

    def test_refused_setting_is_an_error(self):
        self.postfix.edit_fails = True
        with self.assertRaises(pattern_map.MapError) as raised:
            self.apply()
        self.assertIn('virtual_alias_maps', str(raised.exception))
        self.assertEqual(0, self.postfix.count('postfix'))

    def test_failed_reload_is_an_error(self):
        self.postfix.reload_fails = True
        with self.assertRaises(pattern_map.MapError) as raised:
            self.apply()
        self.assertIn('did not reload', str(raised.exception))

    def test_command_that_cannot_be_run_is_an_error(self):
        def missing(command, timeout=None):
            raise FileNotFoundError(2, 'No such file or directory', command[0])
        with self.assertRaises(pattern_map.MapError) as raised:
            pattern_map.apply(lambda: self.rules, missing, str(self.map), str(self.main_cf))
        self.assertTrue(raised.exception.unchanged)

    # A rule can never keep the helper waiting.

    def test_every_check_has_a_short_time_limit(self):
        self.apply()
        self.assertEqual([pattern_map.CHECK_TIMEOUT], self.postfix.timeouts)
        self.assertLessEqual(pattern_map.CHECK_TIMEOUT, 10)
        self.assertLessEqual(pattern_map.RULE_TIMEOUT, 3)

    def test_rule_that_stalls_the_check_is_left_out_and_marked(self):
        self.rules = [(20, DOMAIN, 'poison*', DESTINATION, 'wildcard'), (21, DOMAIN, 'support_*', DESTINATION, 'wildcard'),
                      (22, 'other.example', 'sales_*', 'a@other.example', 'wildcard')]
        self.postfix.slow = ('poison',)
        result = self.apply()
        self.assertEqual('updated', result['state'])
        self.assertEqual([20], [refused['id'] for refused in result['rejected']])
        self.assertIn('not read within %s seconds' % pattern_map.RULE_TIMEOUT, result['rejected'][0]['reason'])
        self.assertEqual([20], self.disabled)
        self.assertNotIn('poison', self.map.read_text())
        self.assertIn('support_', self.map.read_text())
        self.assertIn('sales_', self.map.read_text())
        # The whole map, an empty one, each rule on its own, then the whole map without the slow rule.
        self.assertEqual([pattern_map.CHECK_TIMEOUT, pattern_map.CHECK_TIMEOUT] + [pattern_map.RULE_TIMEOUT] * 3
                         + [pattern_map.CHECK_TIMEOUT], self.postfix.timeouts)
        self.assertEqual(pattern_map.HEADER, self.postfix.checked[1])
        self.assertEqual([], self.leftovers())
        # The rule is marked, so the next run does not meet it again.
        self.rules = self.rules[1:]
        self.postfix.timeouts = []
        self.assertEqual('unchanged', self.apply()['state'])
        self.assertEqual([pattern_map.CHECK_TIMEOUT], self.postfix.timeouts)

    def test_rule_refused_on_its_own_after_a_stalled_check_is_left_out(self):
        self.rules = [(23, DOMAIN, 'poison*', DESTINATION, 'wildcard'), (24, DOMAIN, '[b-a]x', DESTINATION, 'regex'),
                      (25, DOMAIN, 'support_*', DESTINATION, 'wildcard')]
        self.postfix.slow = ('poison',)
        self.postfix.refuse = {'[b-a]': 'Invalid range end'}
        result = self.apply()
        self.assertEqual([23, 24], sorted(refused['id'] for refused in result['rejected']))
        self.assertEqual(pattern_map.HEADER + '/^(support_[^@]*)@example\\.com$/ qa@example.com\n',
                         self.map.read_text())

    def test_postfix_that_cannot_read_an_empty_map_in_time_changes_nothing(self):
        self.apply()
        installed, value = self.map.read_text(), self.postfix.value
        self.rules.append((26, DOMAIN, 'sales_*', DESTINATION, 'wildcard'))
        self.postfix.stalled = True
        self.postfix.commands = []
        with self.assertRaises(pattern_map.MapError) as raised:
            self.apply()
        self.assertIn('empty pattern map', str(raised.exception))
        self.assertTrue(raised.exception.unchanged)
        self.assertEqual(installed, self.map.read_text())
        self.assertEqual(value, self.postfix.value)
        self.assertEqual([], self.disabled)
        self.assertEqual(2, self.postfix.count('postmap'))
        self.assertEqual([], self.leftovers())

    def test_many_slow_rules_mean_postfix_is_slow_and_nothing_changes(self):
        self.rules = [(30 + number, DOMAIN, 'poison%s*' % number, DESTINATION, 'wildcard') for number in range(8)]
        self.postfix.slow = ('poison',)
        with self.assertRaises(pattern_map.MapError) as raised:
            self.apply()
        self.assertIn('too slow', str(raised.exception))
        self.assertFalse(self.map.exists())
        self.assertEqual([], self.disabled)
        # The whole map, the empty one, and one more rule than is put down to the rules themselves.
        self.assertEqual(2 + pattern_map.MAX_SLOW_RULES + 1, self.postfix.count('postmap'))

    def test_rules_beyond_the_limits_are_left_out_and_marked(self):
        self.rules = [(100 + number, DOMAIN, 'a%s_*' % number, DESTINATION, 'wildcard')
                      for number in range(pattern_map.MAX_RULES_PER_DOMAIN + 2)]
        result = self.apply()
        self.assertEqual([120, 121], [refused['id'] for refused in result['rejected']])
        self.assertIn('A domain can have 20 pattern rules', result['rejected'][0]['reason'])
        self.assertEqual([120, 121], self.disabled)
        self.assertEqual(1 + pattern_map.MAX_RULES_PER_DOMAIN, len(self.map.read_text().splitlines()))

    def test_rules_that_could_not_be_marked_are_reported(self):
        self.rules.append((40, DOMAIN, '\\d+', DESTINATION, 'regex'))

        def refuse(identifiers):
            raise RuntimeError('database is read only')
        result = pattern_map.apply(lambda: self.rules, self.postfix, str(self.map), str(self.main_cf), refuse)
        self.assertEqual('updated', result['state'])
        self.assertEqual('database is read only', result['unmarked'])

    # A failed step leaves the map and the setting as they were.

    def test_first_map_is_taken_back_when_postfix_does_not_reload(self):
        self.postfix.reload_fails = True
        with self.assertRaises(pattern_map.MapError) as raised:
            self.apply()
        self.assertIn('did not reload', str(raised.exception))
        self.assertIn('The previous pattern map was put back.', str(raised.exception))
        self.assertTrue(raised.exception.unchanged)
        self.assertFalse(self.map.exists())
        self.assertEqual(self.shipped, self.postfix.value)
        self.assertEqual([], self.leftovers())

    def test_changed_map_is_taken_back_when_postfix_does_not_reload(self):
        self.apply()
        installed, value = self.map.read_text(), self.postfix.value
        for rules in ([(50, DOMAIN, 'sales_*', DESTINATION, 'wildcard')] + self.rules, []):
            self.rules = rules
            self.postfix.reload_fails = True
            with self.assertRaises(pattern_map.MapError) as raised:
                self.apply()
            self.assertIn('The previous pattern map was put back.', str(raised.exception))
            self.assertTrue(raised.exception.unchanged)
            self.assertEqual(installed, self.map.read_text())
            self.assertEqual(0o640, stat.S_IMODE(self.map.stat().st_mode))
            self.assertEqual(value, self.postfix.value)
            self.assertEqual([], self.leftovers())

    def test_first_map_is_taken_back_when_the_setting_is_refused(self):
        self.postfix.edit_fails = True
        with self.assertRaises(pattern_map.MapError) as raised:
            self.apply()
        self.assertTrue(raised.exception.unchanged)
        self.assertFalse(self.map.exists())
        self.assertEqual(self.shipped, self.postfix.value)

    def test_map_that_could_not_be_put_back_is_reported_as_changed(self):
        self.postfix.reload_fails = True
        self.postfix.edits_left = 1
        with self.assertRaises(pattern_map.MapError) as raised:
            self.apply()
        self.assertIn('could not be put back', str(raised.exception))
        self.assertFalse(raised.exception.unchanged)

    def test_rules_are_marked_only_when_the_map_without_them_is_in_use(self):
        self.rules.append((52, DOMAIN, '\\d+', DESTINATION, 'regex'))
        self.postfix.reload_fails = True
        with self.assertRaises(pattern_map.MapError):
            self.apply()
        self.assertEqual([], self.disabled)
        self.postfix.reload_fails = False
        self.apply()
        self.assertEqual([52], self.disabled)

    def test_failure_before_the_map_is_replaced_reports_it_unchanged(self):
        self.apply()
        self.rules.append((51, DOMAIN, 'sales_*', DESTINATION, 'wildcard'))
        self.postfix.fatal = 'unsupported dictionary type: regexp'
        with self.assertRaises(pattern_map.MapError) as raised:
            self.apply()
        self.assertTrue(raised.exception.unchanged)
        self.assertNotIn('put back', str(raised.exception))


class DatabaseAndResultTests(unittest.TestCase):
    def test_enabled_rules_are_read_in_priority_order(self):
        cursor = mock.Mock()
        cursor.fetchall.return_value = [[1, b'example.com', b'support_*', b'qa@example.com', b'wildcard']]
        rules = pattern_map.read_rules(cursor)
        query = cursor.execute.call_args[0][0]
        self.assertIn('FROM e_pattern_forwarding', query)
        self.assertIn('WHERE enabled = 1', query)
        self.assertTrue(query.endswith('ORDER BY priority, id'))
        self.assertEqual(([(1, '/^(support_[^@]*)@example\\.com$/ qa@example.com')], []), pattern_map.build(rules))

    def test_result_survives_other_output_of_the_helper(self):
        result = {'status': 1, 'state': 'updated', 'rejected': [{'id': 3, 'reason': 'x'}]}
        output = 'warning: something\n%s\n' % pattern_map.result_line(result)
        self.assertEqual(result, pattern_map.parse_result(output))
        self.assertEqual(result, pattern_map.parse_result(output.encode()))
        self.assertEqual(result, pattern_map.parse_result(pattern_map.result_line(result) + chr(1)))

    def test_missing_or_broken_result_is_a_failure(self):
        for output in (None, 0, '', 'Permission denied', pattern_map.RESULT_MARK + '{broken',
                       pattern_map.RESULT_MARK + '[1]', '1,None'):
            with self.subTest(output=output):
                self.assertEqual(0, pattern_map.parse_result(output)['status'])
                self.assertTrue(pattern_map.parse_result(output)['error_message'])


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.map = Path(self.directory.name, 'virtual_regexp')
        self.main_cf = Path(self.directory.name, 'main.cf')
        self.main_cf.write_text('virtual_alias_maps = %s\n' % AliasMapSettingTests.shipped)
        self.postfix = FakePostfix(AliasMapSettingTests.shipped)
        self.cursor = mock.Mock()
        self.cursor.fetchall.return_value = [(1, DOMAIN, 'support_*', DESTINATION, 'wildcard'),
                                             (2, DOMAIN, '\\d+', DESTINATION, 'regex')]
        self.connection = mock.Mock()
        self.log = []

    def upgrade(self, connect=None):
        return pattern_map.upgrade(connect or (lambda database: (self.connection, self.cursor)), self.log.append,
                                   self.postfix, str(self.map), str(self.main_cf))

    def test_saved_rules_get_their_map_once(self):
        self.assertEqual('updated', self.upgrade())
        self.assertIn('support_', self.map.read_text())
        self.assertTrue(self.postfix.value.endswith(', regexp:%s' % self.map))
        self.assertIn('Postfix uses them', self.log[0])
        self.assertIn('rule 2 is not in use', self.log[1])
        self.connection.close.assert_called_once_with()
        # The rule that is left out is marked in the database, and the mark is committed.
        self.assertEqual(mock.call('UPDATE e_pattern_forwarding SET enabled = 0 WHERE id IN (%s)', [2]),
                         self.cursor.execute.call_args)
        self.connection.commit.assert_called_once_with()
        self.assertIn('shown as such on its page', self.log[1])
        self.postfix.commands = []
        self.assertEqual('unchanged', self.upgrade())
        self.assertEqual(0, self.postfix.count('postconf', '-e'))
        self.assertEqual(0, self.postfix.count('postfix'))

    def test_panel_database_is_asked_for(self):
        connect = mock.Mock(return_value=(self.connection, self.cursor))
        self.upgrade(connect)
        connect.assert_called_once_with('cyberpanel')

    def test_no_rules_means_no_change(self):
        self.cursor.fetchall.return_value = []
        self.assertEqual('not in use', self.upgrade())
        self.assertFalse(self.map.exists())
        self.assertEqual([], self.log)

    def test_missing_database_connection_is_reported(self):
        self.assertEqual('no connection', self.upgrade(lambda database: (0, 0)))
        self.assertIn('no connection', self.log[0])
        self.assertEqual([], self.postfix.commands)

    def test_server_without_postfix_is_skipped_before_the_database(self):
        self.main_cf.unlink()
        connect = mock.Mock()
        self.assertEqual('no mail server', self.upgrade(connect))
        connect.assert_not_called()


def panel_methods(path, class_name, names, namespace):
    """The named methods of a panel class, compiled alone so that no database or settings are loaded."""
    tree = ast.parse((ROOT / path).read_text())
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    owner.body = [node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert sorted(node.name for node in owner.body) == sorted(names)
    for node in owner.body:
        node.decorator_list = [item for item in node.decorator_list
                               if isinstance(item, ast.Name) and item.id == 'staticmethod']
    owner.bases, owner.keywords, owner.decorator_list = [], [], []
    tree.body = [owner]
    exec(compile(tree, str(ROOT / path), 'exec'), namespace)
    return namespace[class_name]


class FakeRules:
    """The few model calls the page makes on its rules."""

    def __init__(self):
        self.rows = {}
        self.created = 0
        outer = self

        class Found(list):
            def count(self):
                return len(self)

        class Rule:
            def __init__(self, **fields):
                self.id = None
                self.enabled = True
                self.__dict__.update(fields)

            def save(self):
                if self.id is None:
                    outer.created += 1
                    self.id = outer.created
                outer.rows[self.id] = self

            def delete(self):
                del outer.rows[self.id]
                self.id = None

        def select(**conditions):
            found = Found()
            for rule in outer.rows.values():
                if 'domain' in conditions and rule.domain is not conditions['domain']:
                    continue
                if 'id__in' in conditions and rule.id not in conditions['id__in']:
                    continue
                if 'enabled' in conditions and rule.enabled != conditions['enabled']:
                    continue
                found.append(rule)
            return found

        self.model = Rule
        Rule.objects = NS(get=lambda id: self.rows[id], filter=select)


class PanelPageTests(unittest.TestCase):
    command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/mailUtilities.py applyPatternForwarding'
    failed = {'status': 0, 'error_message': 'The pattern map was written, but Postfix did not reload: x. '
                                            'The previous pattern map was put back.', 'map_unchanged': True}

    def setUp(self):
        self.rules = FakeRules()
        self.domain = NS(domain=DOMAIN)
        self.answers = [{'status': 1, 'state': 'updated', 'rejected': []}]
        self.listed = []
        self.process = NS(outputExecutioner=mock.Mock(side_effect=self.answer))
        self.acl = mock.Mock()
        self.acl.currentContextPermission.return_value = 1
        self.acl.checkOwnership.return_value = 1
        self.log = mock.Mock()
        namespace = {
            'json': json, 'HttpResponse': lambda text: NS(content=text), 'ACLManager': self.acl,
            'Administrator': NS(objects=NS(get=mock.Mock(return_value=NS(pk=1)))),
            'Domains': NS(objects=NS(get=mock.Mock(return_value=self.domain))),
            'PatternForwarding': self.rules.model, 'patternForwardingMap': pattern_map,
            'ProcessUtilities': self.process, 'virtualHostUtilities': NS(cyberPanel='/usr/local/CyberCP'),
            'logging': NS(CyberCPLogFileWriter=NS(writeToFile=self.log)),
        }
        self.manager = panel_methods(
            'mailServer/mailserverManager.py', 'MailServerManager',
            ('createPatternRule', 'deletePatternRule', '_applyPatternForwarding', '_patternRuleRefusal',
             '_unusedPatternRules', '_settlePatternForwarding'), namespace)()

    def answer(self, command):
        """The helper's next answer; the last one repeats. The patterns listed at that moment are kept."""
        self.listed.append(sorted(rule.pattern for rule in self.rules.rows.values()))
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        return answer if isinstance(answer, str) else pattern_map.result_line(answer) + '\n'

    def post(self, method, **data):
        self.manager.request = NS(session={'userID': 1}, body=json.dumps(data))
        return json.loads(getattr(self.manager, method)().content)

    def create(self, pattern='support_*', destination=DESTINATION, pattern_type='wildcard'):
        return self.post('createPatternRule', domain=DOMAIN, pattern=pattern, destination=destination,
                         pattern_type=pattern_type, priority=20)

    def test_created_rule_is_handed_to_the_root_helper(self):
        response = self.create(' support_* ', ' qa@example.com ')
        self.assertEqual(1, response['createStatus'])
        self.assertEqual('Pattern forwarding rule created successfully', response['message'])
        rule = self.rules.rows[1]
        self.assertEqual(('support_*', DESTINATION, 'wildcard', 20, True),
                         (rule.pattern, rule.destination, rule.pattern_type, rule.priority, rule.enabled))
        self.process.outputExecutioner.assert_called_once_with(self.command)
        self.assertEqual(self.command, pattern_map.HELPER_COMMAND)

    def test_rule_that_cannot_be_one_map_line_is_not_saved(self):
        for pattern, destination, pattern_type in (('a\n/.*/ thief@evil.test', DESTINATION, 'wildcard'),
                                                   ('.*@evil\\.test|x', DESTINATION, 'regex'),
                                                   ('a{0,255}{0,60}', DESTINATION, 'regex'),
                                                   ('(a{255})?{255}', DESTINATION, 'regex'),
                                                   ('support_*', 'qa@example.com, thief@evil.test', 'wildcard'),
                                                   ('support_*', DESTINATION, 'glob')):
            response = self.create(pattern, destination, pattern_type)
            self.assertEqual((0, 0), (response['status'], response['createStatus']))
            self.assertTrue(response['error_message'])
        self.assertEqual({}, self.rules.rows)
        self.process.outputExecutioner.assert_not_called()

    def test_domain_cannot_have_more_rules_than_the_limit(self):
        for number in range(pattern_map.MAX_RULES_PER_DOMAIN):
            self.rules.model(domain=self.domain, pattern='a%s' % number).save()
        self.rules.model(domain=self.domain, pattern='unused', enabled=False).save()
        response = self.create()
        self.assertEqual(0, response['createStatus'])
        self.assertIn('A domain can have 20 pattern forwarding rules', response['error_message'])
        self.assertEqual(pattern_map.MAX_RULES_PER_DOMAIN + 1, len(self.rules.rows))
        self.process.outputExecutioner.assert_not_called()
        # A rule that is not in use does not count.
        self.rules.rows[1].enabled = False
        self.assertEqual(1, self.create()['createStatus'])

    def test_server_cannot_have_more_rules_than_the_limit(self):
        for number in range(pattern_map.MAX_RULES):
            self.rules.model(domain=NS(domain='d%s.example' % (number % 50)), pattern='a%s' % number).save()
        response = self.create()
        self.assertEqual(0, response['createStatus'])
        self.assertIn('limit of 200 pattern forwarding rules', response['error_message'])
        self.assertEqual(pattern_map.MAX_RULES, len(self.rules.rows))
        self.process.outputExecutioner.assert_not_called()

    def test_rule_is_taken_back_when_the_map_was_not_written(self):
        self.answers = [self.failed]
        response = self.create()
        self.assertEqual((0, 0), (response['status'], response['createStatus']))
        self.assertIn('The rule was not created', response['error_message'])
        self.assertIn('did not reload', response['error_message'])
        self.assertIn('put back', response['error_message'])
        self.assertNotIn('may not follow', response['error_message'])
        self.assertEqual({}, self.rules.rows)
        # The helper left the map as it was, which is what the list says again: one run is enough.
        self.process.outputExecutioner.assert_called_once_with(self.command)
        self.log.assert_called_once()

    def test_map_is_rebuilt_for_the_corrected_list_when_its_state_is_not_known(self):
        for unknown in ('', 'Traceback (most recent call last):', '1,None',
                        {'status': 0, 'error_message': 'The previous pattern map could not be put back.',
                         'map_unchanged': False}):
            self.listed = []
            self.process.outputExecutioner.reset_mock()
            self.answers = [unknown, {'status': 1, 'state': 'updated', 'rejected': []}]
            response = self.create()
            self.assertEqual(0, response['createStatus'])
            self.assertIn('The rule was not created', response['error_message'])
            self.assertNotIn('may not follow', response['error_message'])
            self.assertEqual({}, self.rules.rows)
            # The second run reads the list after the rule was taken back.
            self.assertEqual([['support_*'], []], self.listed)

    def test_administrator_is_told_when_list_and_map_may_differ(self):
        self.answers = ['']
        response = self.create()
        self.assertEqual(0, response['createStatus'])
        self.assertIn('did not report a result', response['error_message'])
        self.assertIn('may not follow the rules listed here', response['error_message'])
        self.assertEqual({}, self.rules.rows)
        self.assertEqual(2, self.process.outputExecutioner.call_count)

    def test_rule_postfix_refuses_is_taken_back_with_its_reason(self):
        self.answers = [{'status': 1, 'state': 'updated',
                         'rejected': [{'id': 1, 'reason': 'The mail server cannot use this pattern: Invalid range end'}]}]
        response = self.create('[b-a]', pattern_type='regex')
        self.assertEqual(0, response['createStatus'])
        self.assertIn('Invalid range end', response['error_message'])
        self.assertEqual({}, self.rules.rows)
        # The map never held the rule, so it is not built again.
        self.process.outputExecutioner.assert_called_once_with(self.command)

    def test_other_rules_of_the_domain_that_are_not_in_use_are_named(self):
        earlier = self.rules.model(domain=self.domain, pattern='old\\d', destination=DESTINATION)
        earlier.save()
        foreign = self.rules.model(domain=NS(domain='other.example'), pattern='theirs', destination=DESTINATION)
        foreign.save()
        self.answers = [{'status': 1, 'state': 'updated', 'rejected': [{'id': earlier.id, 'reason': 'no escapes'},
                                                                        {'id': foreign.id, 'reason': 'private'}]}]
        response = self.create()
        self.assertEqual(1, response['createStatus'])
        self.assertIn('old\\d (no escapes)', response['message'])
        self.assertNotIn('theirs', response['message'])
        self.assertNotIn('private', response['message'])

    def test_deleted_rule_leaves_the_map_through_the_root_helper(self):
        self.create()
        self.process.outputExecutioner.reset_mock()
        response = self.post('deletePatternRule', ruleId=1)
        self.assertEqual(1, response['deleteStatus'])
        self.assertEqual({}, self.rules.rows)
        self.process.outputExecutioner.assert_called_once_with(self.command)

    def kept(self):
        kept = list(self.rules.rows.values())
        self.assertEqual(1, len(kept))
        return (kept[0].pattern, kept[0].destination, kept[0].pattern_type, kept[0].priority, kept[0].enabled,
                kept[0].domain)

    def test_rule_stays_listed_when_the_map_was_not_rewritten(self):
        self.create()
        self.process.outputExecutioner.reset_mock()
        self.answers = [self.failed]
        response = self.post('deletePatternRule', ruleId=1)
        self.assertEqual((0, 0), (response['status'], response['deleteStatus']))
        self.assertIn('The rule was not deleted', response['error_message'])
        self.assertIn('did not reload', response['error_message'])
        self.assertEqual(('support_*', DESTINATION, 'wildcard', 20, True, self.domain), self.kept())
        self.process.outputExecutioner.assert_called_once_with(self.command)

    def test_map_is_rebuilt_with_the_kept_rule_when_its_state_is_not_known(self):
        self.create()
        self.listed = []
        self.answers = ['', {'status': 1, 'state': 'updated', 'rejected': []}]
        response = self.post('deletePatternRule', ruleId=1)
        self.assertEqual(0, response['deleteStatus'])
        self.assertNotIn('may not follow', response['error_message'])
        self.assertEqual(('support_*', DESTINATION, 'wildcard', 20, True, self.domain), self.kept())
        # The second run reads the list after the rule was put back.
        self.assertEqual([[], ['support_*']], self.listed)


class RootHelperTests(unittest.TestCase):
    def setUp(self):
        self.log = mock.Mock()
        self.helper = panel_methods('plogical/mailUtilities.py', 'mailUtilities', ('applyPatternForwarding',),
                                    {'logging': NS(CyberCPLogFileWriter=NS(writeToFile=self.log))})

    def run_helper(self, **outcome):
        printed = io.StringIO()
        with mock.patch.object(pattern_map, 'apply_saved_rules', **outcome) as apply_saved_rules, \
                contextlib.redirect_stdout(printed):
            self.helper.applyPatternForwarding()
        apply_saved_rules.assert_called_once_with()
        return pattern_map.parse_result(printed.getvalue())

    def test_helper_applies_the_saved_rules_and_prints_the_result(self):
        self.assertEqual({'status': 1, 'state': 'updated', 'rejected': []},
                         self.run_helper(return_value={'state': 'updated', 'rejected': []}))
        self.log.assert_not_called()

    def test_helper_logs_rules_that_are_not_in_use(self):
        result = self.run_helper(return_value={'state': 'updated', 'unmarked': 'read only',
                                               'rejected': [{'id': 7, 'reason': 'not read within 3 seconds'}]})
        self.assertEqual(1, result['status'])
        self.assertIn('rule 7 is not in use: not read within 3 seconds', self.log.call_args_list[0][0][0])
        self.assertIn('could not be marked: read only', self.log.call_args_list[1][0][0])

    def test_helper_reports_whether_a_failed_map_is_as_it_was(self):
        for unchanged in (True, False):
            self.assertEqual({'status': 0, 'error_message': 'Postfix did not reload', 'map_unchanged': unchanged},
                             self.run_helper(side_effect=pattern_map.MapError('Postfix did not reload', unchanged)))
        self.assertEqual(2, self.log.call_count)

    def test_helper_reports_any_other_failure_without_a_map_state(self):
        self.assertEqual({'status': 0, 'error_message': 'database is gone'},
                         self.run_helper(side_effect=RuntimeError('database is gone')))

    def test_command_line_reaches_the_helper(self):
        source = (ROOT / 'plogical/mailUtilities.py').read_text()
        self.assertIn("elif args.function == 'applyPatternForwarding':\n"
                      "        mailUtilities.applyPatternForwarding()", source)


class FakePanelDatabase:
    """django.db as the map module uses it: a cursor, and work that waits for the commit."""

    def __init__(self, rows=()):
        self.cursor = mock.MagicMock()
        self.cursor.__enter__.return_value = self.cursor
        self.cursor.fetchall.return_value = list(rows)
        self.waiting = []
        self.connection = NS(cursor=lambda: self.cursor)
        self.transaction = NS(on_commit=self.waiting.append)

    def modules(self):
        return {'django': NS(db=self), 'django.db': self}

    def commit(self):
        while self.waiting:
            self.waiting.pop(0)()


class SavedRulesTests(unittest.TestCase):
    def test_rules_come_from_the_panel_database_and_unused_ones_are_marked_there(self):
        database = FakePanelDatabase([(1, DOMAIN, 'support_*', DESTINATION, 'wildcard')])
        with mock.patch.dict(sys.modules, database.modules()), \
                mock.patch.object(pattern_map, 'apply', return_value={'state': 'updated', 'rejected': []}) as apply:
            self.assertEqual({'state': 'updated', 'rejected': []}, pattern_map.apply_saved_rules())
        rules, run, map_path, main_cf, disable = apply.call_args[0]
        self.assertEqual((pattern_map.MAP_PATH, pattern_map.MAIN_CF), (map_path, main_cf))
        self.assertEqual([(1, DOMAIN, 'support_*', DESTINATION, 'wildcard')], rules())
        disable([7, 9])
        self.assertEqual(mock.call('UPDATE e_pattern_forwarding SET enabled = 0 WHERE id IN (%s, %s)', [7, 9]),
                         database.cursor.execute.call_args)


class RebuildAfterRemovalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.map = Path(self.directory.name, 'virtual_regexp')
        self.map.write_text(pattern_map.HEADER + '/^(support_[^@]*)@gone\\.example$/ old@owner.example\n')
        self.database = FakePanelDatabase()
        self.process = NS(outputExecutioner=mock.Mock(return_value=pattern_map.result_line(
            {'status': 1, 'state': 'updated', 'rejected': []})))
        modules = dict(self.database.modules())
        modules['plogical.processUtilities'] = NS(ProcessUtilities=self.process)
        self.root = True
        patches = (mock.patch.dict(sys.modules, modules),
                   mock.patch.object(pattern_map.os, 'geteuid', lambda: 0 if self.root else 986),
                   mock.patch.object(pattern_map, 'apply_saved_rules'),
                   mock.patch.object(pattern_map, '_log_failed_rebuild'))
        started = [item.start() for item in patches]
        for item in patches:
            self.addCleanup(item.stop)
        self.apply_saved_rules, self.log = started[2], started[3]

    def rebuild(self):
        pattern_map.rebuild_after_removal(str(self.map))

    def test_root_rebuilds_the_map_once_the_deletion_is_committed(self):
        self.rebuild()
        self.apply_saved_rules.assert_not_called()
        self.database.commit()
        self.apply_saved_rules.assert_called_once_with(map_path=str(self.map))
        self.process.outputExecutioner.assert_not_called()
        self.log.assert_not_called()

    def test_web_process_rebuilds_the_map_through_the_root_helper(self):
        self.root = False
        self.rebuild()
        self.process.outputExecutioner.assert_not_called()
        self.database.commit()
        self.process.outputExecutioner.assert_called_once_with(pattern_map.HELPER_COMMAND)
        self.apply_saved_rules.assert_not_called()
        self.log.assert_not_called()

    def test_server_without_a_map_is_left_alone(self):
        self.map.unlink()
        for root in (True, False):
            self.root = root
            self.rebuild()
            self.database.commit()
        self.apply_saved_rules.assert_not_called()
        self.process.outputExecutioner.assert_not_called()
        self.log.assert_not_called()

    def test_failed_rebuild_is_logged_and_never_fails_the_deletion(self):
        self.apply_saved_rules.side_effect = pattern_map.MapError('Postfix did not reload')
        self.rebuild()
        self.database.commit()
        self.assertEqual('Postfix did not reload', str(self.log.call_args[0][0]))
        self.root = False
        for answer in ('', pattern_map.result_line({'status': 0, 'error_message': 'no postmap'})):
            self.log.reset_mock()
            self.process.outputExecutioner.return_value = answer
            self.rebuild()
            self.database.commit()
            self.log.assert_called_once()
        self.process.outputExecutioner.side_effect = RuntimeError('the root helper cannot be reached')
        self.log.reset_mock()
        self.rebuild()
        self.database.commit()
        self.assertEqual('the root helper cannot be reached', str(self.log.call_args[0][0]))

    def test_deletion_survives_a_database_that_cannot_take_the_request(self):
        self.database.transaction.on_commit = mock.Mock(side_effect=RuntimeError('no connection'))
        self.rebuild()
        self.assertEqual('no connection', str(self.log.call_args[0][0]))
        self.apply_saved_rules.assert_not_called()

    def test_every_deletion_of_a_website_or_mail_domain_asks_for_the_rebuild(self):
        call = 'patternForwardingMap.rebuild_after_removal()'
        for path, deletion, times in (('plogical/vhost.py', 'delWebsite.delete()', 2),
                                      ('plogical/virtualHostUtilities.py', 'delWebsite.delete()', 1),
                                      ('plogical/mailDomainDeletion.py', 'domain.delete()', 1),
                                      ('websiteFunctions/website.py', 'staging_website.delete()', 2)):
            with self.subTest(path=path):
                lines = [text.split('#')[0].strip() for text in (ROOT / path).read_text().splitlines()]
                lines = [text for text in lines if text]
                after = [lines[index + 1] for index, text in enumerate(lines) if text == deletion]
                self.assertEqual([call] * times, after)
                self.assertEqual(times, lines.count(call))
                self.assertIn('from plogical import patternForwardingMap', lines)

    def test_child_domain_deletion_rebuilds_after_the_row_is_gone(self):
        events = []
        child = NS(path='/home/parent/child', delete=lambda: events.append('row deleted'))
        namespace = dict(
            Websites=NS(objects=NS(count=lambda: 1)),
            ChildDomains=NS(objects=NS(count=lambda: 1, get=lambda domain: child)),
            vhost=NS(deleteCoreConf=lambda domain, count: 1),
            patternForwardingMap=NS(rebuild_after_removal=lambda: events.append('map rebuilt')),
            installUtilities=NS(installUtilities=NS(reStartLiteSpeed=lambda: events.append('restart'))),
            sslUtilities=NS(removeSSLForDomain=lambda domain: None),
            logging=NS(CyberCPLogFileWriter=NS(writeToFile=mock.Mock())), ProcessUtilities=mock.Mock())
        helper = panel_methods('plogical/virtualHostUtilities.py', 'virtualHostUtilities', ('deleteDomain',),
                               namespace)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual((1, 'None'), helper.deleteDomain('child.example.test'))
        self.assertEqual(['row deleted', 'map rebuilt', 'restart'], events)
        # A deletion that stops before the row is removed leaves the map alone.
        del events[:]
        namespace['vhost'].deleteCoreConf = lambda domain, count: 0
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, helper.deleteDomain('child.example.test')[0])
        self.assertEqual([], events)


class PageTextTests(unittest.TestCase):
    def test_page_states_the_order_and_the_limits(self):
        page = (ROOT / 'mailServer/templates/mailServer/patternForwarding.html').read_text()
        for text in ('An exact forwarding and an existing mailbox for the address always come before a pattern.',
                     'the rule with the lowest priority number is used',
                     'A pattern comes before the catch-all of the domain.',
                     'a tagged address such as user+tag is compared with the patterns before the mailbox user',
                     'may add up to %s at most' % pattern_map.MAX_COUNTED,
                     'A domain can have %s rules and a pattern can be %s characters long.'
                     % (pattern_map.MAX_RULES_PER_DOMAIN, pattern_map.MAX_PATTERN_LENGTH),
                     'ng-if="!rule.enabled"'):
            self.assertIn(text, page)


class PlusAddressingRecordTests(unittest.TestCase):
    def test_setting_postfix_refused_is_not_recorded_as_enabled(self):
        settings = NS(save=mock.Mock())

        def refused(path, mode='r'):
            # As for the panel's web process: main.cf can be read and not written.
            if mode != 'r':
                raise PermissionError(13, 'Permission denied', path)
            return io.StringIO('virtual_alias_domains =\n')
        namespace = {
            'json': json, 'HttpResponse': lambda text: NS(content=text),
            'ACLManager': NS(loadedACL=lambda user: {'admin': 1}),
            'EmailServerSettings': NS(get_settings=lambda: settings),
            'os': NS(path=NS(exists=lambda path: True)), 'open': refused,
            'ProcessUtilities': NS(executioner=mock.Mock()),
        }
        manager = panel_methods('mailServer/mailserverManager.py', 'MailServerManager',
                                ('savePlusAddressingGlobal',), namespace)()
        manager.request = NS(session={'userID': 1}, body=json.dumps({'enabled': True, 'delimiter': '+'}))
        response = json.loads(manager.savePlusAddressingGlobal().content)
        self.assertEqual((0, 0), (response['status'], response['saveStatus']))
        self.assertIn('Permission denied', response['error_message'])
        settings.save.assert_not_called()
        self.assertFalse(hasattr(settings, 'plus_addressing_enabled'))


if __name__ == '__main__':
    unittest.main()
