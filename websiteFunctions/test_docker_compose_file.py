"""The compose file of a Docker site holds its passwords and is never readable by another account."""
import os
import shutil
import stat
import tempfile
import unittest
from unittest import mock

from plogical import DockerSites as docker_sites
from websiteFunctions.test_docker_apps import make_site


class ComposeFileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='docker-compose-file-')
        self.addCleanup(shutil.rmtree, self.directory)
        self.temporary = os.path.join(self.directory, 'example.com-docker-compose.yml')
        self.seen = []
        real_open = os.open
        real_remove = os.remove

        def redirected(path, *args, **kwargs):
            return os.path.join(self.directory, os.path.basename(path)) if str(path).startswith('/home/cyberpanel/') else path

        self.patches = [
            mock.patch.object(docker_sites.os, 'open',
                              side_effect=lambda path, *a, **k: real_open(redirected(path), *a, **k)),
            mock.patch.object(docker_sites.os, 'remove',
                              side_effect=lambda path: real_remove(redirected(path))),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def install(self, result=(1, ''), content='services: {}\n'):
        site = make_site('n8n')

        def output(command, *args):
            # What root finds at the moment it is asked to take the file over.
            details = os.stat(self.temporary)
            with open(self.temporary) as handle:
                self.seen.append((command, stat.S_IMODE(details.st_mode), handle.read()))
            return result

        with mock.patch.object(docker_sites.ProcessUtilities, 'outputExecutioner', side_effect=output), \
                mock.patch.object(docker_sites.ProcessUtilities, 'executioner') as execute:
            answer = site.install_compose_file(content)
        execute.assert_not_called()
        return answer

    def test_the_file_is_private_from_the_moment_it_exists(self):
        previous = os.umask(0)
        self.addCleanup(os.umask, previous)
        self.assertEqual((1, None), self.install(content='PASSWORD=secret\n'))
        command, mode, content = self.seen[0]
        self.assertEqual(0o600, mode)
        self.assertEqual('PASSWORD=secret\n', content)

    def test_root_takes_it_over_with_owner_and_mode_in_one_step(self):
        self.install()
        self.assertEqual(1, len(self.seen))
        self.assertEqual('install -m 600 -o root -g root /home/cyberpanel/example.com-docker-compose.yml '
                         '/home/docker/example.com/docker-compose.yml', self.seen[0][0])

    def test_nothing_is_left_behind(self):
        self.install()
        self.assertEqual([], os.listdir(self.directory))
        self.assertEqual((0, 'no space left'), self.install(result=(0, 'no space left')))
        self.assertEqual([], os.listdir(self.directory))

    def test_a_file_somebody_put_there_first_is_not_written_through(self):
        target = os.path.join(self.directory, 'elsewhere')
        with open(target, 'w') as handle:
            handle.write('untouched')
        os.symlink(target, self.temporary)
        self.assertEqual((1, None), self.install(content='PASSWORD=secret\n'))
        with open(target) as handle:
            self.assertEqual('untouched', handle.read())


if __name__ == '__main__':
    unittest.main(verbosity=2)
