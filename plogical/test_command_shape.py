"""A command meant for one website account never carries a second command to the privileged helper."""
import ast
from pathlib import Path
import shlex
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import warnings

from plogical.commandShape import runs_one_command

ROOT = Path(__file__).resolve().parents[1]
WP = 'sudo -u examp1234 /usr/local/lsws/lsphp83/bin/php -d error_reporting=0 /usr/bin/wp '


class OneCommandTests(unittest.TestCase):
    def test_ordinary_commands_pass(self):
        for command in (
                WP + 'core version --skip-plugins --skip-themes --path=/home/example.com/public_html 2>/dev/null',
                WP + 'plugin list --format=json --path=/home/example.com/my shop',
                WP + 'option update blogname "Tom & Jerry\'s (new) shop; open <daily>" --path=/home/example.com/public_html',
                WP + "user update 1 --user_pass='p;a&s|s$(x)`y`' --path=/home/example.com/public_html",
                WP + 'search-replace http://a.example/?a=1\\&b=2 https://b.example --path=/home/example.com/public_html',
                'sudo -u postgres psql -c "ALTER USER postgres PASSWORD \'s3cret\';" ',
                'sudo -u examp1234 cat /home/example.com/public_html/wp-config.php',
                WP + "plugin list --path=/home/example.com/a' ; id '",
        ):
            self.assertTrue(runs_one_command(command), command)

    def test_second_command_is_refused(self):
        for value in (
                '/home/example.com/a; id', '/home/example.com/a & id', '/home/example.com/a && id',
                '/home/example.com/a | tee /etc/cron.d/x', '/home/example.com/a > /etc/cron.d/x',
                '/home/example.com/a < /etc/shadow', '/home/example.com/a\nid', '/home/example.com/a\rid',
                '/home/example.com/$(id)', '/home/example.com/`id`', '/home/example.com/(a)',
                '/home/example.com/a 2>/dev/null; id', "/home/example.com/a' ; id",
                '/home/example.com/a\\', '/home/example.com/a\x00b',
        ):
            command = WP + 'plugin list --path=%s 2>/dev/null' % value
            self.assertFalse(runs_one_command(command), value)

    def test_value_cannot_leave_the_quotes_it_was_placed_in(self):
        for value in ('x" ; id ; "', 'x$(id)', 'x`id`', 'x"'):
            self.assertFalse(runs_one_command(WP + 'option update blogname "%s"' % value), value)
        for value in ("x' ; id ; '", "x'"):
            self.assertFalse(runs_one_command(WP + "option update blogname '%s'" % value), value)
        self.assertTrue(runs_one_command(WP + 'option update blogname %s' % shlex.quote("x' ; id ; '$(id)`id`")))

    def test_text_that_is_not_a_command_line_is_refused(self):
        for command in (None, b'sudo -u a id', ['sudo', '-u', 'a', 'id']):
            self.assertFalse(runs_one_command(command))


class HelperTests(unittest.TestCase):
    def send(self, command, user=None):
        from plogical import processUtilities

        sent = []

        class Socket:
            def sendall(self, data):
                sent.append(data.decode())

            def recv(self, size):
                return b''

            def close(self):
                pass

        with patch.object(processUtilities.ProcessUtilities, 'setupUDSConnection', return_value=[Socket(), 'None']), \
                patch.object(processUtilities.ProcessUtilities, 'token', 'TOKEN'), \
                patch.object(processUtilities, 'logging', SimpleNamespace(writeToFile=lambda *a, **k: None)):
            reply = processUtilities.ProcessUtilities.sendCommand(command, user)
        return sent, reply

    def test_second_command_never_reaches_the_helper(self):
        sent, reply = self.send(WP + 'plugin list --path=/home/example.com/a & id')
        self.assertEqual([], sent)
        self.assertEqual(1, ord(reply[-1]))
        self.assertIn('refused', reply)

    def test_ordinary_command_is_sent_unchanged(self):
        command = WP + 'plugin list --path=/home/example.com/public_html 2>/dev/null'
        sent, reply = self.send(command)
        self.assertEqual(['TOKEN' + command], sent)

    def test_commands_for_the_helper_itself_and_for_a_named_account_are_not_judged(self):
        sent, reply = self.send('systemctl restart lsws && echo done')
        self.assertEqual(['TOKENsudo systemctl restart lsws && echo done'], sent)
        sent, reply = self.send('cat a | wc -l', 'examp1234')
        self.assertEqual(['TOKEN-u examp1234 cat a | wc -l'], sent)


def rendered(node):
    """The text a command template produces, with X in place of each value."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return ''.join(rendered(part) if isinstance(part, ast.Constant) else 'X' for part in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return rendered(node.left) + rendered(node.right)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        text = rendered(node.left)
        for marker in ('%s', '%d', '%i'):
            text = text.replace(marker, 'X')
        return text
    return 'X'


class TemplateTests(unittest.TestCase):
    def test_every_template_in_the_panel_is_a_single_command(self):
        checked = 0
        for path in sorted(ROOT.rglob('*.py')):
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith(('install/', '.')) or '/test_' in '/' + relative:
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    tree = ast.parse(path.read_text(encoding='utf-8', errors='replace'))
            except SyntaxError:
                continue
            covered = set()
            for node in ast.walk(tree):
                if not isinstance(node, (ast.BinOp, ast.JoinedStr, ast.Constant)) or id(node) in covered:
                    continue
                text = rendered(node)
                if not text.lstrip().startswith('sudo -u '):
                    continue
                covered.update(id(child) for child in ast.walk(node))
                checked += 1
                self.assertTrue(runs_one_command(text), '%s:%s %s' % (relative, node.lineno, text))
        # Fewer than before 3.0.13: the WordPress restore steps go through the runner that reports the
        # real exit status and are no longer `sudo -u` templates.
        self.assertGreater(checked, 60)


if __name__ == '__main__':
    unittest.main()
