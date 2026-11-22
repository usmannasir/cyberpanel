"""The compose file of a Docker site holds its passwords and is never readable by another account."""
import json
import os
import re
import shutil
import stat
import tempfile
import unittest
from unittest import mock

from plogical import DockerSites as docker_sites
from websiteFunctions.test_docker_apps import make_site

try:
    import yaml
except ImportError:
    yaml = None


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

    def test_a_character_beyond_the_basic_plane_is_written_as_one_escape_yaml_reads(self):
        # An emoji written as the pair of escapes JSON has for it is not read by every Docker Compose.
        password = 'Pass\U0001F600w\u00f6rd\U0010FFFF1'
        content = docker_sites.compose_file({'services': {'app': {'environment': ['PASSWORD=' + password]}}})
        self.assertIn('"PASSWORD=Pass\\U0001F600w\\u00f6rd\\U0010FFFF1"', content)
        self.assertNotIn('\\ud83d', content.lower())
        content.encode('ascii')
        if yaml is not None:
            self.assertEqual(['PASSWORD=' + password], yaml.safe_load(content)['services']['app']['environment'])

    def test_text_that_only_looks_like_such_an_escape_stays_what_it_is(self):
        for value in ('a\\ud83d\\ude00b', 'a\\\\ud83d\\ude00', '\\', '\\\\\U0001F600', 'c:\\udata\\ude00',
                      'pass\x85- EXTRA=1', 'line\u2028break', 'tab\there "quoted"'):
            with self.subTest(value=value):
                content = docker_sites.compose_file({'value': value})
                if yaml is not None:
                    self.assertEqual({'value': value}, yaml.safe_load(content))
                # Back from the eight digit form, it is the JSON the panel wrote before.
                restored = re.sub(r'\\\\|\\U([0-9A-F]{8})', lambda found: found.group(0) if found.group(1) is None
                                  else json.dumps(chr(int(found.group(1), 16)))[1:-1], content)
                self.assertEqual({'value': value}, json.loads(restored))

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
