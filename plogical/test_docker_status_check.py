"""A stopped Docker service is reported as not running, not as a failed check."""
from types import SimpleNamespace
import unittest

from plogical.test_child_domain_conversion import load_method


class DeploymentError(Exception):
    def __init__(self, message, error_code=None, recovery_possible=True):
        self.message = message
        super().__init__(message)


def check(is_active):
    """is_active: (exit status, output) of `systemctl is-active docker`."""
    def output(command, user=None, shell=None, dir=None, retRequired=None, okStatuses=(0,)):
        status, text = {'df': (0, '50\n'), 'systemctl': is_active,
                        'docker': (0, str(8 * 1024 ** 3) + '\n'), 'getent': (0, 'docker:x:998:\n')}[command.split()[0]]
        return (1 if status in okStatuses else 0), text

    verify = load_method('plogical/DockerSites.py', 'Docker_Sites', 'verify_system_resources',
                         dict(ProcessUtilities=SimpleNamespace(outputExecutioner=output),
                              DockerDeploymentError=DeploymentError))
    return verify(SimpleNamespace(data={'MemoryMySQL': '512', 'MemorySite': '512'}, ERROR_VOLUME_FAILED='VOLUME'))


class DockerStatusTests(unittest.TestCase):
    def test_running_docker_passes(self):
        self.assertTrue(check((0, 'active\n')))

    def test_stopped_or_missing_docker_is_not_running(self):
        for answer in ((3, 'inactive\n'), (3, 'failed\n'), (4, 'inactive\n')):
            with self.assertRaisesRegex(DeploymentError, 'Docker service is not running'):
                check(answer)

    def test_systemctl_that_cannot_answer_is_a_failed_check(self):
        with self.assertRaisesRegex(DeploymentError, 'Failed to check Docker status'):
            check((127, 'systemctl: command not found\n'))


if __name__ == '__main__':
    unittest.main()
