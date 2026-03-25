import socket
import ssl
import re
import base64


class SieveClient:
    """ManageSieve protocol client (RFC 5804) for managing mail filter rules."""

    def __init__(self, email_address, password, host='localhost', port=4190,
                 master_user=None, master_password=None):
        self.email_address = email_address
        self.host = host
        self.port = port
        self.sock = None
        self.buf = b''

        self.sock = socket.create_connection((host, port), timeout=30)
        self._read_welcome()
        self._starttls()

        if master_user and master_password:
            self._authenticate_master(email_address, master_user, master_password)
        else:
            self._authenticate(email_address, password)

    def _read_line(self):
        while b'\r\n' not in self.buf:
            data = self.sock.recv(4096)
            if not data:
                break
            self.buf += data
        if b'\r\n' in self.buf:
            line, self.buf = self.buf.split(b'\r\n', 1)
            return line.decode('utf-8', errors='replace')
        return ''

    def _read_response(self):
        lines = []
        while True:
            line = self._read_line()
            if not line and not self.buf:
                return False, lines, 'Connection closed'
            if line.startswith('OK'):
                return True, lines, line
            elif line.startswith('NO'):
                return False, lines, line
            elif line.startswith('BYE'):
                return False, lines, line
            else:
                lines.append(line)

    def _read_welcome(self):
        lines = []
        while True:
            line = self._read_line()
            lines.append(line)
            if line.startswith('OK'):
                break
        return lines

    def _send(self, command):
        self.sock.sendall(('%s\r\n' % command).encode('utf-8'))

    def _starttls(self):
        self._send('STARTTLS')
        ok, _, _ = self._read_response()
        if ok:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self.sock = ctx.wrap_socket(self.sock, server_hostname=self.host)
            self.buf = b''
            self._read_welcome()

    def _authenticate(self, user, password):
        auth_str = base64.b64encode(('\x00%s\x00%s' % (user, password)).encode('utf-8')).decode('ascii')
        self._send('AUTHENTICATE "PLAIN" "%s"' % auth_str)
        ok, _, msg = self._read_response()
        if not ok:
            raise Exception('Sieve authentication failed: %s' % msg)

    def _authenticate_master(self, user, master_user, master_password):
        # SASL PLAIN format per RFC 4616: <authz_id>\x00<authn_id>\x00<password>
        # authz_id = target user, authn_id = master user, password = master password
        auth_str = base64.b64encode(
            ('%s\x00%s\x00%s' % (user, master_user, master_password)).encode('utf-8')
        ).decode('ascii')
        self._send('AUTHENTICATE "PLAIN" "%s"' % auth_str)
        ok, _, msg = self._read_response()
        if not ok:
            raise Exception('Sieve master authentication failed: %s' % msg)

    def list_scripts(self):
        """List all Sieve scripts. Returns [(name, is_active), ...]"""
        self._send('LISTSCRIPTS')
        ok, lines, _ = self._read_response()
        if not ok:
            return []
        scripts = []
        for line in lines:
            match = re.match(r'"([^"]+)"(\s+ACTIVE)?', line)
            if match:
                scripts.append((match.group(1), bool(match.group(2))))
        return scripts

    @staticmethod
    def _safe_name(name):
        """Sanitize script name to prevent ManageSieve injection."""
        import re
        safe = re.sub(r'[^a-zA-Z0-9_.-]', '', name)
        if not safe:
            safe = 'default'
        return safe

    def get_script(self, name):
        """Get the content of a Sieve script."""
        self._send('GETSCRIPT "%s"' % self._safe_name(name))
        ok, lines, _ = self._read_response()
        if not ok:
            return ''
        return '\n'.join(lines)

    def put_script(self, name, content):
        """Upload a Sieve script."""
        safe = self._safe_name(name)
        encoded = content.encode('utf-8')
        self._send('PUTSCRIPT "%s" {%d+}' % (safe, len(encoded)))
        self.sock.sendall(encoded + b'\r\n')
        ok, _, msg = self._read_response()
        if not ok:
            raise Exception('Failed to put script: %s' % msg)
        return True

    def activate_script(self, name):
        """Set a script as the active script."""
        self._send('SETACTIVE "%s"' % self._safe_name(name))
        ok, _, msg = self._read_response()
        return ok

    def deactivate_scripts(self):
        """Deactivate all scripts."""
        self._send('SETACTIVE ""')
        ok, _, _ = self._read_response()
        return ok

    def delete_script(self, name):
        """Delete a Sieve script."""
        self._send('DELETESCRIPT "%s"' % self._safe_name(name))
        ok, _, _ = self._read_response()
        return ok

    def close(self):
        try:
            self._send('LOGOUT')
            self._read_response()
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @staticmethod
    def rules_to_sieve(rules):
        """Convert a list of rule dicts to a Sieve script.

        Each rule: {condition_field, condition_type, condition_value, action_type, action_value, name}
        """
        requires = set()
        rule_blocks = []

        for rule in rules:
            field = rule.get('condition_field', 'from')
            cond_type = rule.get('condition_type', 'contains')
            cond_value = rule.get('condition_value', '').replace('\\', '\\\\').replace('"', '\\"')
            action_type = rule.get('action_type', 'move')
            action_value = rule.get('action_value', '').replace('\\', '\\\\').replace('"', '\\"')

            # Map field to Sieve header
            if field == 'from':
                header = 'From'
            elif field == 'to':
                header = 'To'
            elif field == 'subject':
                header = 'Subject'
            else:
                header = field

            # Map condition type to Sieve test
            if cond_type == 'contains':
                test = 'header :contains "%s" "%s"' % (header, cond_value)
            elif cond_type == 'is':
                test = 'header :is "%s" "%s"' % (header, cond_value)
            elif cond_type == 'matches':
                test = 'header :matches "%s" "%s"' % (header, cond_value)
            elif cond_type == 'greater_than' and field == 'size':
                test = 'size :over %s' % cond_value
            else:
                test = 'header :contains "%s" "%s"' % (header, cond_value)

            # Map action
            if action_type == 'move':
                requires.add('fileinto')
                # Ensure folder uses INBOX. namespace prefix for dovecot
                folder = action_value
                if folder and not folder.startswith('INBOX.'):
                    folder = 'INBOX.%s' % folder
                action = 'fileinto "%s";' % folder
            elif action_type == 'forward':
                requires.add('redirect')
                action = 'redirect "%s";' % action_value
            elif action_type == 'discard':
                action = 'discard;'
            elif action_type == 'flag':
                requires.add('imap4flags')
                action = 'addflag "\\\\Flagged";'
            else:
                action = 'keep;'

            name = rule.get('name', 'Rule')
            rule_blocks.append('# %s\nif %s {\n    %s\n}' % (name, test, action))

        # Build full script
        parts = []
        if requires:
            parts.append('require [%s];' % ', '.join('"%s"' % r for r in sorted(requires)))
            parts.append('')
        parts.extend(rule_blocks)

        return '\n'.join(parts)

    @staticmethod
    def sieve_to_rules(script):
        """Best-effort parse of a Sieve script into rule dicts."""
        rules = []
        # Match if-blocks with comments as names
        pattern = re.compile(
            r'#\s*(.+?)\n\s*if\s+header\s+:(\w+)\s+"([^"]+)"\s+"([^"]+)"\s*\{([^}]+)\}',
            re.DOTALL
        )
        for match in pattern.finditer(script):
            name = match.group(1).strip()
            cond_type = match.group(2)
            field_name = match.group(3).lower()
            cond_value = match.group(4)
            action_block = match.group(5).strip()

            action_type = 'keep'
            action_value = ''
            if 'fileinto' in action_block:
                action_type = 'move'
                av = re.search(r'fileinto\s+"([^"]+)"', action_block)
                action_value = av.group(1) if av else ''
                # Strip INBOX. namespace prefix for display
                if action_value.startswith('INBOX.'):
                    action_value = action_value[6:]
            elif 'redirect' in action_block:
                action_type = 'forward'
                av = re.search(r'redirect\s+"([^"]+)"', action_block)
                action_value = av.group(1) if av else ''
            elif 'discard' in action_block:
                action_type = 'discard'
            elif 'addflag' in action_block:
                action_type = 'flag'

            rules.append({
                'name': name,
                'condition_field': field_name,
                'condition_type': cond_type,
                'condition_value': cond_value,
                'action_type': action_type,
                'action_value': action_value,
            })

        return rules
