import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name('backupSSHKey.py')
spec = importlib.util.spec_from_file_location('subject', SOURCE)
subject = importlib.util.module_from_spec(spec); spec.loader.exec_module(subject)


class ExistingBackupKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory()
        cls.key = Path(cls.fixtures.name) / 'identity'
        subprocess.run(['ssh-keygen', '-q', '-t', 'rsa', '-b', '2048', '-N', '', '-f', str(cls.key)], check=True)
        cls.ed25519 = Path(cls.fixtures.name) / 'ed25519'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(cls.ed25519)], check=True)
        cls.ecdsa = Path(cls.fixtures.name) / 'ecdsa'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ecdsa', '-N', '', '-f', str(cls.ecdsa)], check=True)
        cls.encrypted = Path(cls.fixtures.name) / 'encrypted'
        subprocess.run(['ssh-keygen', '-q', '-t', 'rsa', '-b', '2048', '-N', 'fixture-only-passphrase', '-f', str(cls.encrypted)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.private = self.root / 'cyberpanel'; self.public = self.root / 'cyberpanel.pub'
        shutil.copy2(self.key, self.private)
        self.before = self.private.read_bytes(); self.metadata = subject._identity(self.private.stat())
        self.expected = ' '.join(Path(str(self.key)+'.pub').read_text().split()[:2])

    def unchanged_private(self):
        self.assertEqual(self.private.read_bytes(), self.before)
        self.assertEqual(subject._identity(self.private.stat()), self.metadata)

    def test_missing_public_is_derived_without_changing_private(self):
        result = subject.existing_backup_public_key(self.root)
        self.assertTrue(result['repaired']); self.assertEqual(result['public_key'], self.expected)
        self.assertEqual(self.public.read_text().strip(), self.expected)
        self.assertEqual(self.public.stat().st_mode & 0o777, 0o600)
        self.unchanged_private()

    def test_supported_non_rsa_identities_are_preserved(self):
        for identity in (self.ed25519, self.ecdsa):
            with self.subTest(identity=identity.name):
                if self.public.exists(): self.public.unlink()
                shutil.copy2(identity, self.private)
                before = self.private.read_bytes(); metadata = subject._identity(self.private.stat())
                expected = ' '.join(Path(str(identity)+'.pub').read_text().split()[:2])
                self.assertEqual(subject.existing_backup_public_key(self.root)['public_key'], expected)
                self.assertFalse(subject.existing_backup_public_key(self.root)['repaired'])
                self.assertEqual(self.private.read_bytes(), before)
                self.assertEqual(subject._identity(self.private.stat()), metadata)

    def test_fifo_private_public_and_lock_are_refused_without_waiting(self):
        for name in ('cyberpanel', 'cyberpanel.pub', '.cyberpanel-public-key.lock'):
            with self.subTest(path=name):
                target = self.root / name
                if target.exists(): target.unlink()
                os.mkfifo(str(target), 0o600)
                started = time.monotonic()
                with self.assertRaises(subject.BackupKeyError): subject.existing_backup_public_key(self.root)
                self.assertLess(time.monotonic()-started, 1)
                target.unlink()
                if name == 'cyberpanel': shutil.copy2(self.key, self.private)

    def test_private_drift_after_publication_stops_deployment_without_rollback(self):
        real_sync = subject._sync_directory
        def sync(directory):
            real_sync(directory)
            self.private.rename(self.root/'original-private')
            shutil.copy2(self.encrypted, self.private)
        with mock.patch.object(subject, '_sync_directory', side_effect=sync):
            with self.assertRaisesRegex(subject.BackupKeyError, 'after public-key publication'):
                subject.existing_backup_public_key(self.root)
        self.assertEqual(self.private.read_bytes(), self.encrypted.read_bytes())
        self.assertEqual((self.root/'original-private').read_bytes(), self.before)
        self.assertEqual(self.public.read_text().strip(), self.expected)

    def test_foreign_public_replacement_after_publication_is_not_rolled_back(self):
        real_sync = subject._sync_directory
        def sync(directory):
            real_sync(directory)
            self.public.unlink(); self.public.write_bytes(b'foreign replacement')
        with mock.patch.object(subject, '_sync_directory', side_effect=sync):
            with self.assertRaisesRegex(subject.BackupKeyError, 'after public-key publication'):
                subject.existing_backup_public_key(self.root)
        self.assertEqual(self.public.read_bytes(), b'foreign replacement'); self.unchanged_private()

    def test_valid_pair_is_unchanged_including_public_inode(self):
        shutil.copy2(Path(str(self.key)+'.pub'), self.public)
        before = subject._identity(self.public.stat()); data = self.public.read_bytes()
        result = subject.existing_backup_public_key(self.root)
        self.assertFalse(result['repaired']); self.assertEqual(self.public.read_bytes(), data)
        self.assertEqual(subject._identity(self.public.stat()), before); self.unchanged_private()

    def test_corrupt_public_is_backed_up_and_repaired(self):
        self.public.write_bytes(b'not a public key\n')
        result = subject.existing_backup_public_key(self.root)
        self.assertTrue(result['repaired']); self.assertEqual(self.public.read_text().strip(), self.expected)
        backups = list(self.root.glob('.cyberpanel.pub.before-repair-*'))
        self.assertEqual(len(backups), 1); self.assertEqual(backups[0].read_bytes(), b'not a public key\n')
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600); self.unchanged_private()

    def test_valid_mismatched_pair_is_refused(self):
        shutil.copy2(Path(str(self.encrypted)+'.pub'), self.public); before=self.public.read_bytes()
        with self.assertRaisesRegex(subject.BackupKeyError, 'do not match'):
            subject.existing_backup_public_key(self.root)
        self.assertEqual(self.public.read_bytes(),before); self.unchanged_private()

    def test_missing_private_never_generates_a_new_identity(self):
        self.private.unlink()
        with self.assertRaisesRegex(subject.BackupKeyError, 'missing'):
            subject.existing_backup_public_key(self.root)
        self.assertFalse(self.private.exists()); self.assertFalse(self.public.exists())

    def test_invalid_private_fails_without_public_change(self):
        self.private.write_bytes(b'invalid private fixture'); self.private.chmod(0o600)
        self.public.write_bytes(b'keep this public file')
        with self.assertRaisesRegex(subject.BackupKeyError, 'invalid, encrypted'):
            subject.existing_backup_public_key(self.root)
        self.assertEqual(self.public.read_bytes(),b'keep this public file')
        self.assertEqual(self.private.read_bytes(),b'invalid private fixture')

    def test_encrypted_private_is_noninteractive_and_preserved(self):
        shutil.copy2(self.encrypted, self.private); before=self.private.read_bytes()
        with self.assertRaisesRegex(subject.BackupKeyError, 'invalid, encrypted'):
            subject.existing_backup_public_key(self.root)
        self.assertEqual(self.private.read_bytes(),before); self.assertFalse(self.public.exists())

    def test_symlink_private_or_public_is_refused(self):
        self.private.unlink(); self.private.symlink_to(self.key)
        with self.assertRaises(subject.BackupKeyError):subject.existing_backup_public_key(self.root)
        self.private.unlink(); shutil.copy2(self.key,self.private)
        self.public.symlink_to(Path(str(self.key)+'.pub'))
        with self.assertRaises(subject.BackupKeyError):subject.existing_backup_public_key(self.root)
        self.assertTrue(self.public.is_symlink())

    def test_private_path_drift_during_derivation_refuses_publication(self):
        def runner(*args,**kwargs):
            result=subprocess.run(*args,**kwargs)
            self.private.rename(self.root/'original-private')
            shutil.copy2(self.encrypted,self.private)
            return result
        with self.assertRaisesRegex(subject.BackupKeyError,'paths changed'):
            subject.existing_backup_public_key(self.root,runner=runner)
        self.assertFalse(self.public.exists())
        self.assertEqual((self.root/'original-private').read_bytes(),self.before)

    def test_public_path_created_during_derivation_is_not_overwritten(self):
        def runner(*args,**kwargs):
            result=subprocess.run(*args,**kwargs);self.public.write_bytes(b'concurrent owner');return result
        with self.assertRaisesRegex(subject.BackupKeyError,'paths changed'):
            subject.existing_backup_public_key(self.root,runner=runner)
        self.assertEqual(self.public.read_bytes(),b'concurrent owner');self.unchanged_private()

    def test_timeout_does_not_leak_stderr_or_mutate_keys(self):
        def runner(*args,**kwargs):
            self.assertEqual(kwargs['timeout'],10);self.assertEqual(kwargs['stdin'],subprocess.DEVNULL)
            raise subprocess.TimeoutExpired('fixture',10,stderr='PRIVATE FIXTURE CONTENT')
        with self.assertRaises(subject.BackupKeyError) as error:
            subject.existing_backup_public_key(self.root,runner=runner)
        self.assertNotIn('PRIVATE FIXTURE',str(error.exception));self.unchanged_private()
        self.assertFalse(self.public.exists())

    def test_existing_private_permissions_are_not_chmodded(self):
        self.private.chmod(0o644)
        with self.assertRaisesRegex(subject.BackupKeyError,'permissions'):
            subject.existing_backup_public_key(self.root)
        self.assertEqual(self.private.stat().st_mode & 0o777,0o644)
        self.assertFalse(self.public.exists())


class DeploymentRuntimeTests(unittest.TestCase):
    def setUp(self):
        source=Path(__file__).parents[1]/'backup/backupManager.py'
        tree=ast.parse(source.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BackupManager')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='DeployAccount')
        self.key=mock.Mock();self.post=mock.Mock(return_value=SimpleNamespace(status_code=200,json=lambda:{'status':0,'error_message':'fixture platform response'}))
        self.plan=SimpleNamespace(state=0,subscription='fixture-sub',sftpUser='fixture-user',planName='500GB')
        orm=SimpleNamespace(objects=SimpleNamespace(get=lambda **kw:self.plan),DoesNotExist=type('Missing',(Exception,),{}))
        self.imports=mock.patch.dict('sys.modules',{'IncBackups.models':SimpleNamespace(OneClickBackups=orm)})
        self.imports.start();self.addCleanup(self.imports.stop)
        env={'json':json,'shlex':__import__('shlex'),'Administrator':SimpleNamespace(objects=SimpleNamespace(get=lambda **kw:object())),
             'ACLManager':SimpleNamespace(loadedACL=lambda _: {},fetchIP=lambda:'192.0.2.1'),
             'ProcessUtilities':SimpleNamespace(outputExecutioner=self.key),
             'virtualHostUtilities':SimpleNamespace(cyberPanel='/usr/local/CyberCP'),
             'requests':SimpleNamespace(post=self.post,exceptions=__import__('requests').exceptions),
             'HttpResponse':lambda text:json.loads(text),'logging':SimpleNamespace(CyberCPLogFileWriter=mock.Mock())}
        exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),env)
        self.deploy=lambda:env['DeployAccount'](object(),request=SimpleNamespace(session={'userID':1},body='{"id":2}'),userID=1)

    def test_real_deploy_path_submits_only_validated_public_key(self):
        self.key.return_value=json.dumps({'status':1,'public_key':'ssh-rsa fixture-public','repaired':True})
        self.deploy()
        self.assertEqual(self.key.call_args.args[0],'/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/backupSSHKey.py')
        self.assertEqual(json.loads(self.post.call_args.kwargs['data'])['key'],'ssh-rsa fixture-public')

    def test_real_deploy_path_preserves_ed25519_platform_contract(self):
        self.key.return_value=json.dumps({'status':1,'public_key':'ssh-ed25519 fixture-public','repaired':False})
        self.deploy()
        self.assertEqual(json.loads(self.post.call_args.kwargs['data'])['key'],'ssh-ed25519 fixture-public')

    def test_key_validation_failure_never_calls_platform_or_changes_plan(self):
        self.key.return_value=json.dumps({'status':0,'error_message':'Existing private key is encrypted; no keys were changed.'})
        result=self.deploy();self.assertEqual(result['status'],0)
        self.assertIn('encrypted',result['error_message']);self.post.assert_not_called();self.assertEqual(self.plan.state,0)

    def test_malformed_helper_response_never_calls_platform(self):
        self.key.return_value='invalid helper response'
        self.assertEqual(self.deploy()['status'],0);self.post.assert_not_called()

if __name__=='__main__':unittest.main()
