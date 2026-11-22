"""-m installs none of Email, DNS and FTP except the ones it names."""
import itertools
import subprocess
import unittest

from install.installer_test_harness import Installer, script_parts

COMPONENTS = {'postfix': 'Postfix_Switch', 'powerdns': 'PowerDNS_Switch', 'pureftpd': 'PureFTPd_Switch'}

# One argument, and the components it names.
ACCEPTED_LISTS = (
    ('postfix powerdns', ('postfix', 'powerdns')),
    ('postfix  pureftpd ', ('postfix', 'pureftpd')),
    (',postfix', ('postfix',)),
    ('postfix,', ('postfix',)),
    ('postfix,,powerdns', ('postfix', 'powerdns')),
    ('postfix, powerdns', ('postfix', 'powerdns')),
    ('PowerDNS/pureftpd', ('powerdns', 'pureftpd')),
    ('/postfix/', ('postfix',)),
    ('postfix,powerdns pureftpd', ('postfix', 'powerdns', 'pureftpd')),
)
# Arguments that name no component, though some hold the name of one.
REFUSED_WORDS = (
    'nopostfix', 'postfixx', '--postfix', '-postfix', 'postfix=on', 'postfix+powerdns', 'postfix;powerdns',
    'postfix|powerdns', 'nopowerdns', 'pureftpd;reboot', 'postfix,nginx', 'postfix nginx', ',', ' ', '/',
    'postfix\tpowerdns', 'postfix\npowerdns', 'postfix.', 'p0stfix',
)


def function(name):
    functions, _ = script_parts()
    start = functions.index('\n%s() {\n' % name) + 1
    return functions[start:functions.index('\n}\n', start) + 3]


class ComponentChoiceTests(unittest.TestCase):
    def switches(self, *arguments):
        """What the real argument reader makes of a command line."""
        script = ('exec 3>&1\nlog_function_start() { :; }\nDebug_Log2() { :; }\nShow_Help() { echo HELP; }\n'
                  'Fail_Install() { echo "FAILED $*" >&3; exit "${2:-1}"; }\n'
                  'Postfix_Switch="On"\nPowerDNS_Switch="On"\nPureFTPd_Switch="On"\n'
                  'Minimal_Install="Off"\nMinimal_Components=()\nAdmin_Pass_From_File=""\n'
                  + function('Named_Components') + function('Password_Problem') + function('Check_Argument') +
                  'Check_Argument "$@" >/dev/null\n'
                  'echo "$Postfix_Switch $PowerDNS_Switch $PureFTPd_Switch"\n')
        result = subprocess.run(['bash', '-c', script, 'bash'] + list(arguments), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True, timeout=20)
        self.assertEqual('', result.stderr)
        return result.returncode, result.stdout.strip()

    def expected(self, chosen):
        return ' '.join('On' if name in chosen else 'Off' for name in COMPONENTS)

    def test_without_minimal_everything_is_installed(self):
        self.assertEqual((0, 'On On On'), self.switches('-v', 'ols'))
        self.assertEqual((0, 'On On On'), self.switches('default'))
        self.assertEqual((0, 'On On On'), self.switches())

    def test_minimal_alone_installs_none(self):
        for arguments in (['-m'], ['--minimal'], ['-v', 'ols', '-m'], ['-m', '-v', 'ols', '-a']):
            with self.subTest(arguments=arguments):
                self.assertEqual((0, 'Off Off Off'), self.switches(*arguments))

    def test_every_subset_installs_exactly_what_it_names(self):
        for size in range(len(COMPONENTS) + 1):
            for chosen in itertools.permutations(COMPONENTS, size):
                for arguments in (
                        ['-v', 'ols', '-m'] + list(chosen),
                        ['-m'] + [name.upper() for name in chosen] + ['-v', 'ols'],
                        ['-m', '-v', 'ols'] + list(chosen),
                        list(chosen) + ['-v', 'ols', '-m']):
                    with self.subTest(arguments=arguments):
                        self.assertEqual((0, self.expected(chosen)), self.switches(*arguments))
                if chosen:
                    for separator in (',', '/'):
                        arguments = ['-v', 'ols', '-m', separator.join(chosen)]
                        with self.subTest(arguments=arguments):
                            self.assertEqual((0, self.expected(chosen)), self.switches(*arguments))

    def test_a_password_that_contains_a_component_name_installs_nothing_more(self):
        self.assertEqual((0, 'Off Off Off'), self.switches('-v', 'ols', '-m', '-p', 'postfix-powerdns'))
        self.assertEqual((0, 'Off On Off'), self.switches('-v', 'ols', '-p', 'pureftpd1', '-m', 'powerdns'))

    def test_a_word_that_is_no_component_name_is_refused(self):
        for word in REFUSED_WORDS:
            with self.subTest(word=word):
                status, output = self.switches('-v', 'ols', '-m', word)
                self.assertEqual(2, status)
                self.assertIn('FAILED invalid_input 2', output)

    def test_one_argument_may_hold_several_names(self):
        for word, chosen in ACCEPTED_LISTS:
            with self.subTest(word=word):
                self.assertEqual((0, self.expected(chosen)), self.switches('-v', 'ols', '-m', word))
                self.assertEqual((0, self.expected(chosen)), self.switches(word, '-m', '-v', 'ols'))

    def test_first_check_of_the_command_line_knows_the_same_names(self):
        usage = ('Show_Help() { echo HELP; }\nAdmin_Pass_From_File=""\n' + function('Named_Components')
                 + function('Branch_Problem') + function('License_Problem') + function('Password_Problem')
                 + function('Check_Usage') + 'Check_Usage "$@"\necho ACCEPTED\n')

        def check(*arguments):
            result = subprocess.run(['bash', '-c', usage, 'bash'] + list(arguments), stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, universal_newlines=True, timeout=20)
            self.assertEqual('', result.stderr)
            return result.returncode, result.stdout.strip().splitlines()[-1]

        for word, _ in ACCEPTED_LISTS:
            with self.subTest(word=word):
                self.assertEqual((0, 'ACCEPTED'), check('-v', 'ols', '-m', word))
        for word in REFUSED_WORDS:
            with self.subTest(word=word):
                self.assertEqual(2, check('-v', 'ols', '-m', word)[0])
        # An option that needs a value and has none is still refused.
        self.assertEqual(2, check('-m', 'postfix', '-v')[0])
        self.assertEqual(2, check('-v')[0])

    def test_name_before_minimal_counts_and_the_help_says_so(self):
        self.assertEqual((0, 'On Off Off'), self.switches('postfix', '-m'))
        self.assertEqual((0, 'Off On On'), self.switches('pureftpd', '-v', 'ols', '-m', 'powerdns'))
        help_text = Installer(self).run('--help').stdout
        self.assertIn('The names count wherever they stand on the command line, also before', help_text)

    def test_component_names_without_minimal_keep_the_full_installation(self):
        self.assertEqual((0, 'On On On'), self.switches('-v', 'ols', 'postfix'))

    def test_the_installer_is_told_each_choice(self):
        functions, _ = script_parts()
        for chosen in itertools.chain.from_iterable(
                itertools.combinations(COMPONENTS, size) for size in range(len(COMPONENTS) + 1)):
            with self.subTest(chosen=chosen):
                machine = Installer(self)
                harness = machine.harness()
                marker = 'phase Main_Installation\n'
                self.assertEqual(1, harness.count(marker))
                # The lines of the real Main_Installation that turn the switches
                # into the flags of install.py.
                start = functions.index('Final_Flags+=(--postfix')
                flags = functions[start:functions.index('\n', functions.index('Final_Flags+=(--ftp'))]
                harness = harness.replace(
                    marker, marker + 'Final_Flags=()\n' + flags + '\nprintf "%s\\n" "${Final_Flags[*]}" > "$QA_CALLS.flags"\n')
                machine.harness = lambda harness=harness: harness
                result = machine.run('-v', 'ols', '-m', *chosen)
                self.assertEqual(0, result.returncode, result.stderr)
                told = (machine.root / 'calls.flags').read_text().split()
                self.assertEqual(
                    ['--postfix', 'ON' if 'postfix' in chosen else 'OFF',
                     '--powerdns', 'ON' if 'powerdns' in chosen else 'OFF',
                     '--ftp', 'ON' if 'pureftpd' in chosen else 'OFF'], told)


if __name__ == '__main__':
    unittest.main()
