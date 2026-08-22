import base64
import os
import pathlib
import stat
import struct
import tempfile
import unittest

from plogical.sshKeyUtilities import (
    authorized_key_records,
    delete_authorized_key,
    parse_authorized_key,
)


def public_key(key_type, payload=b'key-payload'):
    encoded_type = key_type.encode('ascii')
    blob = struct.pack('>I', len(encoded_type)) + encoded_type + payload
    return base64.b64encode(blob).decode('ascii')


class AuthorizedKeyParsingTests(unittest.TestCase):

    def test_current_openssh_key_algorithms_are_listed(self):
        key_types = (
            'ssh-rsa',
            'ssh-ed25519',
            'ecdsa-sha2-nistp256',
            'sk-ssh-ed25519@openssh.com',
            'sk-ecdsa-sha2-nistp256@openssh.com',
        )

        for key_type in key_types:
            with self.subTest(key_type=key_type):
                parsed = parse_authorized_key(
                    '%s %s user@host' % (key_type, public_key(key_type))
                )
                self.assertEqual(key_type, parsed['keyType'])
                self.assertEqual('user@host', parsed['comment'])
                self.assertRegex(parsed['keyId'], r'^[0-9a-f]{64}$')

    def test_options_and_multiword_comments_are_supported(self):
        key_type = 'ssh-ed25519'
        parsed = parse_authorized_key(
            'command="echo ready",no-pty %s %s deployment key@host'
            % (key_type, public_key(key_type))
        )

        self.assertEqual(key_type, parsed['keyType'])
        self.assertEqual('deployment key@host', parsed['comment'])

    def test_malformed_or_mismatched_key_data_is_rejected(self):
        self.assertIsNone(parse_authorized_key('ssh-ed25519 not-base64 user@host'))
        self.assertIsNone(parse_authorized_key(
            'ssh-rsa %s user@host' % public_key('ssh-ed25519')
        ))
        self.assertIsNone(parse_authorized_key('# ssh-ed25519 ignored'))

    def test_records_include_an_opaque_exact_deletion_identifier(self):
        key_type = 'ssh-ed25519'
        records = authorized_key_records([
            '%s %s deploy@example.com' % (key_type, public_key(key_type)),
        ])

        self.assertEqual(1, len(records))
        self.assertEqual('deploy', records[0]['userName'])
        self.assertTrue(records[0]['key'].startswith('ssh-ed25519 '))
        self.assertRegex(records[0]['keyId'], r'^[0-9a-f]{64}$')


class AuthorizedKeyDeletionTests(unittest.TestCase):

    def test_only_the_exact_key_is_deleted_atomically(self):
        key_type = 'ssh-ed25519'
        shared_prefix = b'x' * 160
        first_data = public_key(key_type, shared_prefix + b'first')
        second_data = public_key(key_type, shared_prefix + b'second')
        first_line = '%s %s first@host\n' % (key_type, first_data)
        second_line = '%s %s second@host\n' % (key_type, second_data)
        first_id = parse_authorized_key(first_line)['keyId']

        self.assertEqual(first_data[:50], second_data[:50])

        with tempfile.TemporaryDirectory() as temporary_directory:
            authorized_keys = pathlib.Path(temporary_directory) / 'authorized_keys'
            authorized_keys.write_text(
                '# retained comment\n' + first_line + second_line,
                encoding='utf-8',
            )
            authorized_keys.chmod(0o640)

            self.assertTrue(delete_authorized_key(str(authorized_keys), first_id))

            updated = authorized_keys.read_text(encoding='utf-8')
            self.assertIn('# retained comment\n', updated)
            self.assertNotIn(first_line, updated)
            self.assertIn(second_line, updated)
            self.assertEqual(0o640, stat.S_IMODE(authorized_keys.stat().st_mode))

    def test_invalid_identifier_leaves_file_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            authorized_keys = pathlib.Path(temporary_directory) / 'authorized_keys'
            original = 'ssh-ed25519 %s user@host\n' % public_key('ssh-ed25519')
            authorized_keys.write_text(original, encoding='utf-8')

            self.assertFalse(delete_authorized_key(str(authorized_keys), 'ssh-ed25519'))
            self.assertEqual(original, authorized_keys.read_text(encoding='utf-8'))

    def test_symlinks_and_hard_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = pathlib.Path(temporary_directory)
            target = directory / 'target'
            key_line = 'ssh-ed25519 %s user@host\n' % public_key('ssh-ed25519')
            target.write_text(key_line, encoding='utf-8')
            key_id = parse_authorized_key(key_line)['keyId']

            symlink = directory / 'symlink'
            symlink.symlink_to(target)
            with self.assertRaises(ValueError):
                delete_authorized_key(str(symlink), key_id)

            hard_link = directory / 'hard-link'
            os.link(target, hard_link)
            with self.assertRaises(ValueError):
                delete_authorized_key(str(hard_link), key_id)

            self.assertEqual(key_line, target.read_text(encoding='utf-8'))


class SSHKeyUIContractTests(unittest.TestCase):

    def test_both_ssh_key_pages_submit_the_exact_key_identifier(self):
        root = pathlib.Path(__file__).parents[1]
        for relative_path in (
            'firewall/templates/firewall/secureSSH.html',
            'websiteFunctions/templates/websiteFunctions/sshAccess.html',
        ):
            template = (root / relative_path).read_text(encoding='utf-8')
            self.assertIn('deleteKey(record.keyId)', template)
            self.assertNotIn('deleteKey(record.key)', template)

        for relative_path in (
            'firewall/static/firewall/firewall.js',
            'websiteFunctions/static/websiteFunctions/websiteFunctions.js',
        ):
            javascript = (root / relative_path).read_text(encoding='utf-8')
            self.assertIn('key: keyId', javascript)


if __name__ == '__main__':
    unittest.main()
