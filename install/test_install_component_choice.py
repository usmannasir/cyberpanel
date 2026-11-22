"""-m installs none of Email, DNS and FTP except the ones it names."""
import itertools
import subprocess
import unittest

from install.installer_test_harness import Installer, script_parts

COMPONENTS = {'postfix': 'Postfix_Switch', 'powerdns': 'PowerDNS_Switch', 'pureftpd': 'PureFTPd_Switch'}


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

    def test_a_word_that_only_contains_a_component_name_is_refused(self):
        for word in ('postfixx', 'nopowerdns', 'pureftpd;reboot', 'postfix,', ',postfix', 'postfix,nginx'):
            with self.subTest(word=word):
                status, output = self.switches('-v', 'ols', '-m', word)
                if word == 'postfix,':
                    # A trailing separator names nothing more.
                    self.assertEqual((0, 'On Off Off'), (status, output))
                else:
                    self.assertEqual(2, status)
                    self.assertIn('FAILED invalid_input 2', output)

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
