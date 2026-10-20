"""SSH changes tested on disposable files; service and firewall actions are stubs."""
import ast
import contextlib
import io
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

from plogical.sshConfigUtilities import SSHConfigError, render_ssh_config, update_ssh_config, validate_ssh_config, validate_ssh_service, ssh_service_is_listening


def service_result(arguments='/usr/sbin/sshd -D', path='/usr/sbin/sshd', environment_files='', environment='', pass_environment='', unset_environment=''):
    return subprocess.CompletedProcess([], 0, stdout=(
        'ExecStart={ path=' + path + ' ; argv[]=' + arguments + ' ; ignore_errors=no ; start_time=[n/a] ; stop_time=[n/a] ; pid=42 ; code=(null) ; status=0/0 }\n'
        + 'EnvironmentFiles='+environment_files+'\nEnvironment='+environment+'\nPassEnvironment='+pass_environment+'\nUnsetEnvironment='+unset_environment+'\n'
    ).encode(), stderr=b'')


class RenderTests(unittest.TestCase):
    def test_exact_global_directives_and_comments(self):
        source = b'#Port 22\nPort 2222 # main\n#GatewayPorts no\nGatewayPorts no\n# Port forwarding\nPermitRootLogin prohibit-password\n'
        result = render_ssh_config(source, '2200', 'no')
        self.assertIn(b'#Port 22\n', result)
        self.assertIn(b'Port 2200 # main\n', result)
        self.assertIn(b'#GatewayPorts no\nGatewayPorts no\n# Port forwarding\n', result)
        self.assertEqual(sum(line.startswith(b'Port ') for line in result.splitlines()), 1)
    def test_duplicates_consolidated_idempotently_and_inline_comments_retained(self):
        source=b'Port 22 # first\npOrT\t2222 # second\nPermitRootLogin no\nPermitRootLogin yes # old duplicate\n'
        result=render_ssh_config(source,2200,'yes')
        self.assertIn(b'# pOrT\t2222 # second\n',result)
        self.assertIn(b'# PermitRootLogin yes # old duplicate\n',result)
        self.assertEqual(result,render_ssh_config(result,2200,'yes'))
    def test_include_and_match_are_byte_preserved(self):
        source=b'Include /etc/ssh/sshd_config.d/*.conf\nMatch User backup\n  PermitRootLogin no\n  Include /etc/ssh/backup.conf\nMatch all\n  GatewayPorts no\n'
        result=render_ssh_config(source,2200,'yes')
        self.assertEqual(result,b'Port 2200\nPermitRootLogin yes\n'+source)
    def test_crlf_case_whitespace_and_missing_final_newline(self):
        source=b'  pOrT\t22  # note\r\nPermitRootLogin\tno'
        self.assertEqual(render_ssh_config(source,2200,'yes'),b'  pOrT\t2200  # note\r\nPermitRootLogin\tyes')
    def test_invalid_port_before_processing(self):
        for value in ('0','65536','22;touch x','22\nPort 25','abc'):
            with self.subTest(value=value),self.assertRaises(SSHConfigError):render_ssh_config(b'',value,'no')
    def test_invalid_root_login(self):
        with self.assertRaises(SSHConfigError):render_ssh_config(b'',22,'invalid')


@unittest.skipUnless(hasattr(os, 'listxattr'), 'Linux filesystem metadata tests run in native acceptance')
class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.directory=Path(self.temp.name).resolve();self.path=self.directory/'sshd_config'
        self.original=b'#Port 22\nPort 2222\nGatewayPorts no\nPermitRootLogin prohibit-password\n';self.path.write_bytes(self.original);self.path.chmod(0o640)
        self.prepare=mock.Mock();self.restart=mock.Mock(return_value=True);self.active=mock.Mock(return_value=True)
        self.runner=mock.Mock(return_value=subprocess.CompletedProcess([],3,stdout=b'',stderr=b''));self.validator=mock.Mock()
        self.service_result=service_result()
        self.runner.side_effect=lambda argv,**kwargs: self.service_result if '--property=ExecStart' in argv else self.runner.return_value
    def tearDown(self):self.temp.cleanup()
    def update(self):return update_ssh_config(self.path,2200,'no',self.prepare,self.restart,self.active,self.runner,self.validator,backup_directory=self.directory/'backups')
    def test_existing_xattrs_preserved(self):
        os.setxattr(self.path,'user.cp_fixture',b'private fixture attribute')
        self.update()
        self.assertEqual(os.getxattr(self.path,'user.cp_fixture'),b'private fixture attribute')
    def test_metadata_failure_leaves_original_before_activation(self):
        with mock.patch('plogical.sshConfigUtilities.os.setxattr',side_effect=OSError('fixture metadata failure')):
            # A source attribute makes the temporary metadata application fail.
            with mock.patch('plogical.sshConfigUtilities.os.listxattr',return_value=['user.fixture']),mock.patch('plogical.sshConfigUtilities.os.getxattr',return_value=b'fixture'):
                with self.assertRaises(OSError):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.restart.assert_not_called()
    def test_success_metadata_preserved_and_private_backup(self):
        before=self.path.stat();self.update();after=self.path.stat()
        self.assertEqual((before.st_uid,before.st_gid,stat.S_IMODE(before.st_mode)),(after.st_uid,after.st_gid,stat.S_IMODE(after.st_mode)))
        self.assertIn(b'Port 2200\n',self.path.read_bytes());self.restart.assert_called_once();self.active.assert_called_once();self.prepare.assert_called_once()
        backups=list((self.directory/'backups').glob('previous-*.conf'));self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_bytes(),self.original);self.assertEqual(backups[0].stat().st_mode&0o777,0o600)
    def test_validation_failure_before_firewall_or_replace(self):
        self.validator.side_effect=SSHConfigError('invalid')
        with self.assertRaises(SSHConfigError):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.prepare.assert_not_called();self.restart.assert_not_called()
    def test_restart_failure_restores_original_and_does_not_claim_success(self):
        self.restart.side_effect=[False,True]
        with self.assertRaisesRegex(SSHConfigError,'Previous configuration and service restored'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.assertEqual(self.restart.call_count,2)
    def test_wrong_requested_listener_rolls_back_using_original_service_state(self):
        listener=mock.Mock(return_value=False)
        with self.assertRaisesRegex(SSHConfigError,'Previous configuration and service restored'):
            update_ssh_config(self.path,2200,'no',self.prepare,self.restart,self.active,self.runner,self.validator,is_listening=listener,backup_directory=self.directory/'backups')
        self.assertEqual(self.path.read_bytes(),self.original)
        self.assertEqual(listener.call_count,1)
        self.assertEqual(self.restart.call_count,2)
    def test_inactive_service_restores_original(self):
        self.active.side_effect=[False,True]
        with self.assertRaisesRegex(SSHConfigError,'Previous configuration and service restored'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original)
    def test_failed_recovery_reports_console_attention(self):
        self.restart.return_value=False
        with self.assertRaisesRegex(SSHConfigError,'server console'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original)
    def test_socket_activation_refused_before_any_mutation(self):
        self.runner.return_value=subprocess.CompletedProcess([],0,stdout=b'',stderr=b'')
        with self.assertRaisesRegex(SSHConfigError,'socket activation'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.prepare.assert_not_called();self.restart.assert_not_called()
    def test_unknown_socket_status_refused_before_mutation(self):
        self.runner.return_value=subprocess.CompletedProcess([],1,stdout=b'',stderr=b'fixture query failure')
        with self.assertRaisesRegex(SSHConfigError,'Could not determine'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.prepare.assert_not_called();self.restart.assert_not_called()
    def test_service_override_refused_before_firewall_or_config_change(self):
        self.service_result=service_result('/usr/sbin/sshd -D -o PermitRootLogin=yes')
        with self.assertRaisesRegex(SSHConfigError,'custom launch arguments'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.prepare.assert_not_called();self.restart.assert_not_called()
        self.assertFalse((self.directory/'backups').exists())
    def test_new_override_during_prepare_keeps_original(self):
        self.prepare.side_effect=lambda:setattr(self,'service_result',service_result('/usr/sbin/sshd -D -f /alternate/config'))
        with self.assertRaisesRegex(SSHConfigError,'custom launch arguments'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.restart.assert_not_called()
    def test_new_override_after_restart_rolls_back_without_success(self):
        def restart():
            self.service_result=service_result('/usr/sbin/sshd -D -oPermitRootLogin=yes')
            return True
        self.restart.side_effect=restart
        with self.assertRaisesRegex(SSHConfigError,'Previous configuration and service restored'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.assertEqual(self.restart.call_count,2)
    def test_unchanged_file_does_not_hide_a_new_service_override(self):
        self.original=render_ssh_config(self.original,2200,'no');self.path.write_bytes(self.original)
        def active():
            self.service_result=service_result('/usr/sbin/sshd -D -o PermitRootLogin=yes')
            return True
        self.active.side_effect=active
        with self.assertRaisesRegex(SSHConfigError,'custom launch arguments'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.prepare.assert_not_called();self.restart.assert_not_called()
    def test_new_backup_ancestors_are_durable_before_replace(self):
        from plogical import sshConfigUtilities as helper
        events=[];real_sync=helper._sync_directory;real_replace=os.replace
        def sync(path):events.append(('sync',Path(path)));return real_sync(path)
        def replace(source,destination):events.append(('replace',Path(destination)));return real_replace(source,destination)
        with mock.patch.object(helper,'_sync_directory',side_effect=sync),mock.patch.object(helper.os,'replace',side_effect=replace):
            update_ssh_config(self.path,2200,'no',self.prepare,self.restart,self.active,self.runner,self.validator,backup_directory=self.directory/'new-parent'/'backups')
        replacement=events.index(('replace',self.path))
        self.assertIn(('sync',self.directory),events[:replacement])
        self.assertIn(('sync',self.directory/'new-parent'),events[:replacement])
        self.assertIn(('sync',self.directory/'new-parent'/'backups'),events[:replacement])
    def empty_options_fixture(self):
        from plogical import sshConfigUtilities as helper
        options=self.directory/'options';options.write_bytes(b'SSHD_OPTS=\n');options.chmod(0o644)
        self.service_result=service_result('/usr/sbin/sshd -D $SSHD_OPTS',environment_files='/etc/default/ssh (ignore_errors=yes)')
        reader=helper._empty_options_file
        patched=mock.patch.object(helper,'_empty_options_file',side_effect=lambda path,name:reader(options,name))
        patched.start();self.addCleanup(patched.stop)
        return options
    def test_standard_explicit_empty_options_allow_checked_update(self):
        self.empty_options_fixture();self.update();self.restart.assert_called_once()
        self.assertIn(b'Port 2200\n',self.path.read_bytes())
    def test_options_file_edit_during_prepare_refuses_before_replace(self):
        options=self.empty_options_fixture();self.prepare.side_effect=lambda:options.write_bytes(b'# changed\nSSHD_OPTS=\n')
        with self.assertRaisesRegex(SSHConfigError,'launch settings changed'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.restart.assert_not_called()
    def test_options_file_metadata_change_during_restart_restores_original(self):
        options=self.empty_options_fixture()
        def restart():options.chmod(0o600);return True
        self.restart.side_effect=restart
        with self.assertRaisesRegex(SSHConfigError,'Previous configuration and service restored'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.assertEqual(self.restart.call_count,2)
    def test_concurrent_edit_before_commit_is_preserved(self):
        self.prepare.side_effect=lambda:self.path.write_bytes(b'# concurrent change\n')
        with self.assertRaisesRegex(SSHConfigError,'changed during validation'):self.update()
        self.assertEqual(self.path.read_bytes(),b'# concurrent change\n');self.restart.assert_not_called()
    def test_concurrent_edit_during_activation_is_not_rolled_back(self):
        self.restart.side_effect=lambda:self.path.write_bytes(b'# newer admin change\n')
        with self.assertRaisesRegex(SSHConfigError,'changed concurrently'):self.update()
        self.assertEqual(self.path.read_bytes(),b'# newer admin change\n')
    def test_symlink_config_refused(self):
        target=self.directory/'target';target.write_bytes(self.original);self.path.unlink();self.path.symlink_to(target)
        with self.assertRaises(SSHConfigError):self.update()
        self.assertEqual(target.read_bytes(),self.original);self.prepare.assert_not_called()
    def test_concurrent_lock_refused(self):
        import fcntl
        with (self.directory/'.cyberpanel-sshd.lock').open('wb') as stream:
            os.chmod(stream.name,0o600);fcntl.flock(stream,fcntl.LOCK_EX)
            with self.assertRaisesRegex(SSHConfigError,'Another SSH'):self.update()
        self.assertEqual(self.path.read_bytes(),self.original);self.prepare.assert_not_called()


class ListenerTests(unittest.TestCase):
    def test_requires_active_service_pid_on_requested_port(self):
        runner=mock.Mock(side_effect=[subprocess.CompletedProcess([],0,stdout=b''),subprocess.CompletedProcess([],0,stdout=b'42\n'),subprocess.CompletedProcess([],0,stdout=b'LISTEN 0 128 *:2200 *:* users:(("sshd",pid=42,fd=3))')])
        self.assertTrue(ssh_service_is_listening(2200,runner))
        self.assertEqual(runner.call_args.args[0],['ss','-H','-ltnp','sport = :2200'])
    def test_other_process_listener_does_not_count(self):
        runner=mock.Mock(side_effect=[subprocess.CompletedProcess([],0,stdout=b''),subprocess.CompletedProcess([],0,stdout=b'42\n'),subprocess.CompletedProcess([],0,stdout=b'LISTEN 0 128 *:2200 *:* users:(("other",pid=142,fd=3))')])
        self.assertFalse(ssh_service_is_listening(2200,runner))
    def test_no_requested_listener_or_inactive_service_is_failure(self):
        runner=mock.Mock(side_effect=[subprocess.CompletedProcess([],0,stdout=b''),subprocess.CompletedProcess([],0,stdout=b'42\n'),subprocess.CompletedProcess([],0,stdout=b'')])
        self.assertFalse(ssh_service_is_listening(2200,runner))
        self.assertFalse(ssh_service_is_listening(2200,mock.Mock(return_value=subprocess.CompletedProcess([],3,stdout=b''))))


class ServiceCommandTests(unittest.TestCase):
    def test_standard_launch_flags_are_supported(self):
        for arguments in ('/usr/sbin/sshd', '/usr/sbin/sshd -D', '/usr/sbin/sshd -D -e', '/usr/sbin/sshd -D -4'):
            with self.subTest(arguments=arguments):
                self.assertEqual(tuple(arguments.split()),validate_ssh_service(mock.Mock(return_value=service_result(arguments)))[0])
    def test_config_port_and_root_login_overrides_are_refused(self):
        for arguments in ('-f /alternate/config','-p 2200','-o PermitRootLogin=yes','-oPermitRootLogin=yes','-oPort=2200'):
            with self.subTest(arguments=arguments),self.assertRaisesRegex(SSHConfigError,'custom launch arguments'):
                validate_ssh_service(mock.Mock(return_value=service_result('/usr/sbin/sshd -D '+arguments)))
    def test_environment_expansions_are_refused_even_if_current_process_may_be_empty(self):
        for arguments in ('$SSHD_OPTS','${OPTIONS}','$OPTIONS -D'):
            with self.subTest(arguments=arguments),self.assertRaisesRegex(SSHConfigError,'standard explicitly empty'):
                validate_ssh_service(mock.Mock(return_value=service_result('/usr/sbin/sshd '+arguments)))
    def test_custom_executable_multiple_commands_and_unreadable_unit_are_refused(self):
        results=[service_result('/bin/sh -c sshd',path='/bin/sh'),subprocess.CompletedProcess([],1,stdout=b'',stderr=b'no unit')]
        multiple=service_result();multiple.stdout+=service_result().stdout;results.append(multiple)
        for result in results:
            with self.subTest(result=result),self.assertRaises(SSHConfigError):validate_ssh_service(mock.Mock(return_value=result))


@unittest.skipUnless(hasattr(os, 'listxattr') and os.geteuid()==0, 'Root-owned native options fixtures only')
class EmptyOptionsTests(unittest.TestCase):
    def setUp(self):
        from plogical import sshConfigUtilities as helper
        self.helper=helper;self.temp=tempfile.TemporaryDirectory();self.directory=Path(self.temp.name).resolve();self.path=self.directory/'options'
        self.path.write_bytes(b'# Standard optional arguments\nSSHD_OPTS=\n');self.path.chmod(0o644)
        self.reader=helper._empty_options_file
        self.result=service_result('/usr/sbin/sshd -D $SSHD_OPTS',environment_files='/etc/default/ssh (ignore_errors=yes)')
    def tearDown(self):self.temp.cleanup()
    def validate(self):
        with mock.patch.object(self.helper,'_empty_options_file',side_effect=lambda path,name:self.reader(self.path,name)):
            return validate_ssh_service(mock.Mock(return_value=self.result))
    def test_explicit_empty_assignment_forms_and_standard_options_mapping(self):
        for value in (b'SSHD_OPTS=\n',b'SSHD_OPTS=""\n',b"SSHD_OPTS=''\n",b'; comment\n SSHD_OPTS = "" \n'):
            self.path.write_bytes(value);binding=self.validate();self.assertEqual(binding[2][0],'/etc/default/ssh')
        self.path.write_bytes(b'OPTIONS=""\n');self.result=service_result('/usr/sbin/sshd -D $OPTIONS',environment_files='/etc/sysconfig/sshd (ignore_errors=yes)')
        self.assertEqual(self.validate()[2][0],'/etc/sysconfig/sshd')
    def test_nonempty_shell_syntax_missing_duplicate_and_extra_assignments_refused(self):
        for value in (b'SSHD_OPTS="-o PermitRootLogin=yes"\n',b'SSHD_OPTS= # not a comment\n',b'SSHD_OPTS=$(anything)\n',b'export SSHD_OPTS=\n',b'# absent\n',b'SSHD_OPTS=\nSSHD_OPTS=\n',b'SSHD_OPTS=\nOTHER=\n',b'SSHD_OPTS=\\\n',b'SSHD_OPTS=\xff\n'):
            self.path.write_bytes(value)
            with self.subTest(value=value),self.assertRaises(SSHConfigError):self.validate()
    def test_inherited_inline_unset_multiple_or_wrong_file_options_refused(self):
        for changes in ({'environment':'SSHD_OPTS='},{'pass_environment':'SSHD_OPTS'},{'unset_environment':'SSHD_OPTS'},{'environment_files':'/etc/default/ssh (ignore_errors=yes) /extra (ignore_errors=yes)'},{'environment_files':'/another/file (ignore_errors=yes)'}, {'arguments':'/usr/sbin/sshd -D $SSHD_OPTS $CRYPTO_POLICY'}):
            values={'arguments':'/usr/sbin/sshd -D $SSHD_OPTS','environment_files':'/etc/default/ssh (ignore_errors=yes)'};values.update(changes);self.result=service_result(**values)
            with self.subTest(changes=changes),self.assertRaises(SSHConfigError):self.validate()
    def test_missing_symlink_hardlink_and_writable_file_refused(self):
        self.path.unlink()
        with self.assertRaises(SSHConfigError):self.validate()
        target=self.directory/'target';target.write_bytes(b'SSHD_OPTS=\n');self.path.symlink_to(target)
        with self.assertRaises(SSHConfigError):self.validate()
        self.path.unlink();os.link(target,self.path)
        with self.assertRaises(SSHConfigError):self.validate()
        self.path.unlink();self.path.write_bytes(b'SSHD_OPTS=\n');self.path.chmod(0o666)
        with self.assertRaises(SSHConfigError):self.validate()
    def test_content_and_metadata_bound_but_runtime_pid_and_atime_not_bound(self):
        initial=self.validate();self.result.stdout=self.result.stdout.replace(b'pid=42',b'pid=99')
        self.assertEqual(initial,self.validate())
        self.path.write_bytes(b'# New empty-file revision\nSSHD_OPTS=\n')
        self.assertNotEqual(initial,self.validate())
        initial=self.validate();self.path.chmod(0o600);self.assertNotEqual(initial,self.validate())


class WrapperTests(unittest.TestCase):
    def test_failure_token_reaches_manager_and_success_only_after_update(self):
        source=Path(__file__).with_name('firewallUtilities.py').read_text();tree=ast.parse(source)
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FirewallUtilities');fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='saveSSHConfigs');fn.decorator_list=[]
        module=ast.Module(body=[fn],type_ignores=[]);output=io.StringIO();update=mock.Mock(side_effect=SSHConfigError('SSH restart failed'))
        namespace={'update_ssh_config':update}
        exec(compile(ast.fix_missing_locations(module),'<SSH wrapper fixture>','exec'),namespace)
        with contextlib.redirect_stdout(output):namespace['saveSSHConfigs']('1','2200','0')
        self.assertEqual(output.getvalue(),'0,SSH restart failed\n');self.assertNotIn('1,None',output.getvalue())
        output=io.StringIO();update.side_effect=None
        with contextlib.redirect_stdout(output):namespace['saveSSHConfigs']('1','2200','0')
        self.assertEqual(output.getvalue(),'1,None\n')


@unittest.skipUnless(os.environ.get('CP_SSHD_FIXTURE_TESTS')=='1','Opt-in real parser with disposable key/config only')
class RealSSHDValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cp-sshd-parser-');self.directory=Path(self.temp.name).resolve();self.key=self.directory/'hostkey'
        subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-f',str(self.key)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.path=self.directory/'sshd_config';self.prefix=('HostKey '+str(self.key)+'\nPidFile '+str(self.directory/'pid')+'\nPasswordAuthentication no\nUsePAM no\n').encode()
    def tearDown(self):self.temp.cleanup()
    def test_real_parser_accepts_consolidated_global_and_preserved_match(self):
        source=self.prefix+b'#Port 22\nPort 2222\nGatewayPorts no\nPort 2222\nPermitRootLogin no\nMatch User nobody\n PermitRootLogin no\n'
        self.path.write_bytes(render_ssh_config(source,2200,'yes'));validate_ssh_config(self.path,2200,'yes')
        result=subprocess.run(['/usr/sbin/sshd','-T','-f',str(self.path),'-C','user=nobody,host=localhost,addr=127.0.0.1'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.assertIn(b'permitrootlogin no\n',result.stdout)
    def test_real_include_additional_port_refused_without_touching_include(self):
        include=self.directory/'extra.conf';include.write_text('Port 2222\n');before=include.read_bytes()
        self.path.write_bytes(render_ssh_config(self.prefix+('Include '+str(include)+'\n').encode(),2200,'no'))
        with self.assertRaisesRegex(SSHConfigError,'additional ports'):validate_ssh_config(self.path,2200,'no')
        self.assertEqual(include.read_bytes(),before)
    def test_real_include_root_login_override_refused(self):
        include=self.directory/'root-login.conf';include.write_text('PermitRootLogin no\n')
        source=self.prefix+('Include '+str(include)+'\n').encode()+b'Port 2200\nPermitRootLogin no\n'
        self.path.write_bytes(render_ssh_config(source,2200,'yes'))
        with self.assertRaisesRegex(SSHConfigError,'override root login'):validate_ssh_config(self.path,2200,'yes')
        self.assertEqual(include.read_text(),'PermitRootLogin no\n')
    def test_real_explicit_listen_address_other_port_refused(self):
        self.path.write_bytes(render_ssh_config(self.prefix+b'ListenAddress 127.0.0.1:2222\n',2200,'no'))
        with self.assertRaisesRegex(SSHConfigError,'ListenAddress'):validate_ssh_config(self.path,2200,'no')
    def test_real_invalid_config_refused(self):
        self.path.write_bytes(self.prefix+b'UnknownConfiguration invalid\n')
        with self.assertRaises(SSHConfigError):validate_ssh_config(self.path,2200,'no')

if __name__=='__main__':unittest.main()
