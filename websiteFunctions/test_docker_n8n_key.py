"""Every new n8n site encrypts what it stores with a key of its own."""
import re
import unittest

from websiteFunctions.test_docker_apps import make_site

try:
    import yaml
except ImportError:
    yaml = None


def key_of(site):
    compose = yaml.safe_load(site.generate_compose_config())
    environment = dict(item.split('=', 1) for item in compose['services']['testapp']['environment'])
    return environment['N8N_ENCRYPTION_KEY']


@unittest.skipIf(yaml is None, 'PyYAML not installed')
class EncryptionKeyTests(unittest.TestCase):
    def test_the_key_is_random_text_and_not_a_fixed_word(self):
        key = key_of(make_site('n8n'))
        self.assertNotEqual('auto', key)
        self.assertTrue(re.fullmatch('[A-Za-z0-9]{32}', key), key)

    def test_two_sites_never_share_a_key(self):
        keys = {key_of(make_site('n8n')) for _ in range(20)}
        self.assertEqual(20, len(keys))

    def test_one_deployment_keeps_one_key_however_often_its_file_is_written(self):
        site = make_site('n8n')
        first = key_of(site)
        self.assertEqual(first, key_of(site))
        self.assertEqual(first, site.data['n8nEncryptionKey'])

    def test_a_key_made_for_the_deployment_is_the_one_used(self):
        site = make_site('n8n')
        site.data['n8nEncryptionKey'] = 'K' * 32
        self.assertEqual('K' * 32, key_of(site))


if __name__ == '__main__':
    unittest.main(verbosity=2)
