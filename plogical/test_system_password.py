import json
import os
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical.systemPassword import (
    apply_system_password,
    consume_system_password_request,
    create_system_password_request,
)


class SystemPasswordTests(unittest.TestCase):

    def test_password_is_passed_over_stdin_without_a_shell(self):
        with mock.patch(
            'plogical.systemPassword.subprocess.run',
            return_value=SimpleNamespace(returncode=0, stderr=''),
        ) as run:
            apply_system_password('exampleuser', "a password'$(id):with punctuation")

        self.assertEqual(['/usr/sbin/chpasswd'], run.call_args.args[0])
        self.assertEqual(
            "exampleuser:a password'$(id):with punctuation\n",
            run.call_args.kwargs['input'],
        )
        self.assertFalse(run.call_args.kwargs['shell'])
        self.assertEqual(30, run.call_args.kwargs['timeout'])

    def test_non_string_and_multiline_passwords_are_rejected(self):
        for password in (['value'], {'value': 'password'}, None, 'line1\nroot:changed'):
            with self.subTest(password=password), self.assertRaises(ValueError):
                apply_system_password('exampleuser', password)

    def test_invalid_system_user_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_system_password('exampleuser;id', 'valid-password')

    def test_request_token_is_single_use_and_does_not_contain_the_password(self):
        with tempfile.TemporaryDirectory() as directory:
            token = create_system_password_request(
                'exampleuser',
                'valid-password',
                directory=directory,
            )

            self.assertNotIn('valid-password', token)
            payload = consume_system_password_request(token, directory=directory)
            self.assertEqual(
                {'username': 'exampleuser', 'password': 'valid-password'},
                payload,
            )
            with self.assertRaises(FileNotFoundError):
                consume_system_password_request(token, directory=directory)

    def test_malformed_request_is_rejected_after_consumption(self):
        with tempfile.TemporaryDirectory() as directory:
            token_path = os.path.join(directory, 'a' * 43)
            with open(token_path, 'w', encoding='utf-8') as request_file:
                json.dump({'username': 'root', 'password': ['invalid']}, request_file)
            os.chmod(directory, 0o700)
            os.chmod(token_path, 0o600)

            with self.assertRaises(ValueError):
                consume_system_password_request('a' * 43, directory=directory)
            self.assertFalse(os.path.exists(token_path))


class SystemPasswordIntegrationTests(unittest.TestCase):

    def test_real_subprocess_receives_password_only_on_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            capture_path = os.path.join(directory, 'captured')
            executable = os.path.join(directory, 'chpasswd')
            with open(executable, 'w', encoding='utf-8') as script:
                script.write(
                    '#!/bin/sh\n'
                    'IFS= read -r password_line\n'
                    'printf "%s" "$password_line" > "$PASSWORD_CAPTURE"\n'
                )
            os.chmod(executable, 0o700)
            real_run = subprocess.run

            with mock.patch.dict(
                os.environ,
                {'PASSWORD_CAPTURE': capture_path},
            ):
                with mock.patch(
                    'plogical.systemPassword.subprocess.run',
                    side_effect=lambda unused_command, **kwargs: real_run(
                        [executable],
                        **kwargs,
                    ),
                ):
                    apply_system_password('exampleuser', "safe'$(id):password")

            with open(capture_path, encoding='utf-8') as capture:
                self.assertEqual("exampleuser:safe'$(id):password", capture.read())
