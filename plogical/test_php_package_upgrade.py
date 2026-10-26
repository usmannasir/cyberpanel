import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock
from plogical.phpPackageUpgrade import installed_php_upgrade_command, upgrade_installed_php


class InstalledPHPUpgradeTests(unittest.TestCase):
    @mock.patch('plogical.phpPackageUpgrade.subprocess.check_output')
    def test_debian_only_requests_installed_exact_packages(self, query):
        query.return_value = ('lsphp81\tconfig-files\nlsphp81-common\tinstalled\nlsphp83\tinstalled\n'
                              'lsphp83-common\tinstalled\nlsphp83\tinstalled\n'
                              'other\tinstalled\nlsphp84\tnot-installed\n')
        command = installed_php_upgrade_command('apt-get')
        self.assertEqual(['apt-get','-y','--no-remove','--only-upgrade','install',
                          'lsphp83','lsphp83-common'], command)
        self.assertNotIn('lsphp81', command)

    @mock.patch('plogical.phpPackageUpgrade.subprocess.check_output')
    def test_rpm_uses_update_of_installed_names(self, query):
        query.return_value = 'lsphp83\nlsphp83-common\nother\nlsphp83\n'
        for manager in ('dnf','yum'):
            self.assertEqual([manager,'-y','update','lsphp83','lsphp83-common'],
                             installed_php_upgrade_command(manager))

    @mock.patch('plogical.phpPackageUpgrade.subprocess.check_output')
    def test_package_names_cannot_add_manager_options_or_shell_fragments(self, query):
        query.return_value = 'lsphp83;command\n--other\nlsphp83*\nlsphp83\nlsphp83-common\n'
        self.assertEqual(['dnf','-y','update','lsphp83','lsphp83-common'],installed_php_upgrade_command('dnf'))

    @mock.patch('plogical.phpPackageUpgrade.subprocess.check_output')
    def test_leftover_extension_does_not_reinstall_removed_rpm_runtime(self, query):
        query.return_value = 'lsphp81-common\nlsphp83\nlsphp83-common\n'
        self.assertEqual(['dnf','-y','update','lsphp83','lsphp83-common'],
                         installed_php_upgrade_command('dnf'))

    @mock.patch('plogical.phpPackageUpgrade.subprocess.check_output',return_value='')
    def test_no_packages_does_not_expand_to_general_os_upgrade(self, query):
        for manager in ('apt-get','dnf','yum'):
            self.assertEqual([],installed_php_upgrade_command(manager))

    @mock.patch('plogical.phpPackageUpgrade.subprocess.check_output',side_effect=subprocess.CalledProcessError(1,'query'))
    def test_query_failure_does_not_fallback_to_installing_branches(self, query):
        with self.assertRaises(subprocess.CalledProcessError):
            installed_php_upgrade_command('apt-get')

    @mock.patch('plogical.phpPackageUpgrade.subprocess.run')
    @mock.patch('plogical.phpPackageUpgrade.installed_php_upgrade_command',return_value=[])
    def test_empty_selection_performs_no_package_transaction(self, plan, run):
        self.assertEqual([],upgrade_installed_php());run.assert_not_called()

    @mock.patch('plogical.phpPackageUpgrade.subprocess.run',side_effect=subprocess.CalledProcessError(1,'apt-get'))
    @mock.patch('plogical.phpPackageUpgrade.installed_php_upgrade_command',return_value=['apt-get','-y','--only-upgrade','install','lsphp83'])
    def test_package_transaction_failure_propagates(self, plan, run):
        with self.assertRaises(subprocess.CalledProcessError):upgrade_installed_php()
        self.assertTrue(run.call_args[1]['check'])
        self.assertEqual('noninteractive',run.call_args[1]['env']['DEBIAN_FRONTEND'])

    def test_upgrade_entrypoint_preserves_required_panel_runtime_setup(self):
        source=(pathlib.Path(__file__).parents[1]/'plogical/upgrade.py').read_text()
        start=source.index('    def installPHP73():')
        end=source.index('    @staticmethod',start)
        self.assertIn('upgrade_installed_php()',source[start:end])
        self.assertNotIn(' install ',source[start:end])
        self.assertIn('Upgrade.setupPHPSymlink()',source)
        self.assertIn('Upgrade.installPanelPHP()',source)

    def test_legacy_development_repair_does_not_reinstall_absent_runtime(self):
        source=(pathlib.Path(__file__).parents[1]/'cyberpanel_upgrade.sh').read_text()
        start=source.index('  if [[ -x /usr/local/lsws/lsphp74/bin/php ]]')
        end=source.index('\n  fi',start)+len('\n  fi')
        snippet=source[start:end]
        self.assertIn('if [[ -x /usr/local/lsws/lsphp74/bin/php ]] ; then',source)
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory);binary=root/'php';trace=root/'trace'
            for name,body in [('apt-cache','exit 0'),('dpkg-query','exit 1'),
                              ('apt-get','printf "install-called\\n" >> "$TRACE"')]:
                executable=root/name;executable.write_text('#!/bin/sh\n'+body+'\n');executable.chmod(0o700)
            code=snippet.replace('/usr/local/lsws/lsphp74/bin/php',str(binary))
            env=dict(os.environ,PATH=str(root)+os.pathsep+os.environ['PATH'],TRACE=str(trace))
            subprocess.run(['bash','-c',code],env=env,check=True)
            self.assertFalse(trace.exists())
            binary.write_text('#!/bin/sh\n');binary.chmod(0o700)
            subprocess.run(['bash','-c',code],env=env,check=True)
            self.assertEqual('install-called\n',trace.read_text())

if __name__=='__main__':unittest.main()
