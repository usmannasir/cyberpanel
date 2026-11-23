"""The upgrade unlocks website homes that a File Manager delete made immutable,
and leaves every other home exactly as it is. Real attributes, in temporary
folders; the attribute tests need root and a file system that keeps them."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

from plogical import fileManagerLockRepair as lock_repair

ROOT = Path(__file__).resolve().parents[1]


def chattr(flag, *paths):
    subprocess.run(['chattr', flag] + list(paths), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def immutable(path):
    return lock_repair.is_immutable(path) if os.path.isdir(path) else 'i' in subprocess.run(
        ['lsattr', '--', path], stdout=subprocess.PIPE, universal_newlines=True).stdout.split()[0]


def attributes_work():
    if os.geteuid() != 0 or not shutil.which('chattr') or not shutil.which('lsattr'):
        return False
    with tempfile.TemporaryDirectory() as directory:
        probe = os.path.join(directory, 'probe')
        open(probe, 'w').close()
        try:
            chattr('+i', probe)
        except (subprocess.CalledProcessError, OSError):
            return False
        chattr('-i', probe)
        return True


@unittest.skipUnless(attributes_work(), 'needs root and a file system with the immutable attribute')
class RealHomes(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.addCleanup(self.cleanup)
        # A home locked the way the File Manager delete locked it: everything.
        self.locked = os.path.join(self.base, 'locked.example')
        os.makedirs(os.path.join(self.locked, 'public_html', 'wp-content', 'uploads'))
        for name in ('public_html/index.php', 'public_html/wp-content/uploads/photo.jpg', 'app.env'):
            Path(self.locked, name).write_text('x')
        # Outside the home, protected on purpose, and reachable through a link.
        self.outside = os.path.join(self.base, 'protected.conf')
        Path(self.outside).write_text('keep')
        os.symlink(self.outside, os.path.join(self.locked, 'public_html', 'link-to-protected'))
        os.symlink(os.path.join(self.base, 'nowhere'), os.path.join(self.locked, 'dangling'))
        subprocess.run(['chattr', '-R', '+i', self.locked], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        chattr('+i', self.outside)
        # A home whose owner protected one file: the home folder is not immutable.
        self.protected = os.path.join(self.base, 'protected.example')
        os.makedirs(os.path.join(self.protected, 'public_html'))
        self.config = os.path.join(self.protected, 'public_html', 'wp-config.php')
        Path(self.config).write_text('x')
        chattr('+i', self.config)

    def cleanup(self):
        subprocess.run(['chattr', '-R', '-i', self.base], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        shutil.rmtree(self.base, ignore_errors=True)

    def repair(self):
        return lock_repair.repair(['locked.example', 'protected.example'],
                                  homes=lambda domains: [os.path.join(self.base, d) for d in domains])

    def test_a_home_locked_by_a_delete_is_unlocked_and_nothing_else_changes(self):
        self.assertTrue(immutable(self.locked))
        self.assertEqual(([self.locked], []), self.repair())
        for folder, folders, files in os.walk(self.locked):
            for name in [folder] + [os.path.join(folder, f) for f in files]:
                if not os.path.islink(name):
                    self.assertFalse(immutable(name), name)
        # Uploads work again: a new file in the uploads folder.
        Path(self.locked, 'public_html/wp-content/uploads/new.jpg').write_text('y')
        # The link was not followed; the protected file outside stays protected.
        self.assertTrue(immutable(self.outside))
        # The other home is exactly as its owner left it.
        self.assertTrue(immutable(self.config))
        self.assertFalse(immutable(self.protected))

    def test_a_second_run_changes_nothing(self):
        self.repair()
        self.assertEqual(([], []), self.repair())
        self.assertTrue(immutable(self.config))


class Decisions(unittest.TestCase):
    def test_only_the_home_folders_own_attribute_decides(self):
        def run(arguments, **options):
            self.assertEqual(['lsattr', '-d', '--', '/home/a.example'], arguments)
            return SimpleNamespace(returncode=0, stdout='----i---------e------- /home/a.example\n')
        self.assertTrue(lock_repair.is_immutable('/home/a.example', run))

        def plain(arguments, **options):
            return SimpleNamespace(returncode=0, stdout='--------------e------- /home/a.example\n')
        self.assertFalse(lock_repair.is_immutable('/home/a.example', plain))

        def failing(arguments, **options):
            return SimpleNamespace(returncode=1, stdout='')
        self.assertFalse(lock_repair.is_immutable('/home/a.example', failing))

    def test_unlocking_never_follows_links(self):
        seen = []

        def run(arguments, **options):
            seen.append(arguments)
            return SimpleNamespace(returncode=0, stdout='')
        self.assertTrue(lock_repair.unlock('/home/a.example', run))
        self.assertEqual(['find', '-P', '/home/a.example', '(', '-type', 'f', '-o', '-type', 'd', ')',
                          '-exec', 'chattr', '-i', '{}', '+'], seen[0])

    def test_only_real_website_folders_are_looked_at(self):
        with tempfile.TemporaryDirectory() as base:
            os.makedirs(os.path.join(base, 'real.example'))
            os.symlink(os.path.join(base, 'real.example'), os.path.join(base, 'link.example'))
            homes = list(lock_repair.website_homes(['real.example', 'link.example', 'missing.example',
                                                    '', '..', 'a/b'], root=base))
        self.assertEqual([os.path.join(base, 'real.example')], homes)

    def test_a_home_that_does_not_answer_is_reported_and_the_others_are_repaired(self):
        def run(arguments, **options):
            self.assertIn('timeout', options)
            if arguments[-1] == '/home/stale.example':
                raise subprocess.TimeoutExpired(arguments, options['timeout'])
            if arguments[0] == 'lsattr':
                return SimpleNamespace(returncode=0, stdout='----i--------- %s\n' % arguments[-1])
            return SimpleNamespace(returncode=0, stdout='')
        self.assertEqual((['/home/a.example'], ['/home/stale.example']),
                         lock_repair.repair(['stale.example', 'a.example'], run=run,
                                            homes=lambda domains: ['/home/' + d for d in domains]))

    def test_the_upgrade_runs_the_repair_and_never_fails_because_of_it(self):
        source = (ROOT / 'plogical' / 'upgrade.py').read_text()
        step = source[source.index('from plogical.fileManagerLockRepair import repair'):]
        step = step[:step.index('\n        ##')]
        self.assertIn('except Exception as error:', step)
        self.assertLess(source.index('Upgrade.fixPermissions()\n'),
                        source.index('from plogical.fileManagerLockRepair import repair'))


if __name__ == '__main__':
    unittest.main()
