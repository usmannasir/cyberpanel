import imaplib
import ssl
import email
import re
from email.header import decode_header


class IMAPClient:
    """Wrapper around imaplib.IMAP4_SSL for Dovecot IMAP operations.

    CyberPanel's Dovecot uses namespace: separator='.', prefix='INBOX.'
    So folders are: INBOX, INBOX.Sent, INBOX.Drafts, INBOX.Deleted Items,
    INBOX.Junk E-mail, INBOX.Archive, etc.
    """

    # Dovecot namespace config: separator='.', prefix='INBOX.'
    NS_PREFIX = 'INBOX.'
    NS_SEP = '.'

    # Map of standard folder purposes to actual Dovecot folder names
    # (CyberPanel creates these in mailUtilities.py)
    SPECIAL_FOLDERS = {
        'sent': 'INBOX.Sent',
        'drafts': 'INBOX.Drafts',
        'trash': 'INBOX.Deleted Items',
        'junk': 'INBOX.Junk E-mail',
        'archive': 'INBOX.Archive',
    }

    def __init__(self, email_address, password, host='localhost', port=993,
                 master_user=None, master_password=None):
        self.email_address = email_address
        self.host = host
        self.port = port
        self.conn = None

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        self.conn = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)

        if master_user and master_password:
            login_user = '%s*%s' % (email_address, master_user)
            self.conn.login(login_user, master_password)
        else:
            self.conn.login(email_address, password)

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
        try:
            self.conn.logout()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _decode_header_value(self, value):
        if value is None:
            return ''
        decoded_parts = decode_header(value)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or 'utf-8', errors='replace'))
            else:
                result.append(part)
        return ''.join(result)

    def _parse_folder_list(self, line):
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='replace')
        match = re.match(r'\(([^)]*)\)\s+"([^"]+)"\s+"?([^"]+)"?', line)
        if not match:
            match = re.match(r'\(([^)]*)\)\s+"([^"]+)"\s+(.+)', line)
        if match:
            flags = match.group(1)
            delimiter = match.group(2)
            name = match.group(3).strip('"')
            return {'name': name, 'delimiter': delimiter, 'flags': flags}
        return None

    def _display_name(self, folder_name):
        """Strip INBOX. prefix for display, keep INBOX as-is."""
        if folder_name == 'INBOX':
            return 'Inbox'
        if folder_name.startswith(self.NS_PREFIX):
            return folder_name[len(self.NS_PREFIX):]
        return folder_name

    def _folder_type(self, folder_name):
        """Identify special folder type for UI icon mapping."""
        for ftype, fname in self.SPECIAL_FOLDERS.items():
            if folder_name == fname:
                return ftype
        if folder_name == 'INBOX':
            return 'inbox'
        return 'folder'

    def list_folders(self):
        status, data = self.conn.list()
        if status != 'OK':
            return []
        folders = []
        for item in data:
            if item is None:
                continue
            parsed = self._parse_folder_list(item)
            if parsed is None:
                continue
            folder_name = parsed['name']
            unread = 0
            total = 0
            try:
                # Quote folder names with spaces for STATUS command
                quoted = '"%s"' % folder_name
                st, counts = self.conn.status(quoted, '(MESSAGES UNSEEN)')
                if st == 'OK' and counts[0]:
                    count_str = counts[0].decode('utf-8', errors='replace') if isinstance(counts[0], bytes) else counts[0]
                    m = re.search(r'MESSAGES\s+(\d+)', count_str)
                    u = re.search(r'UNSEEN\s+(\d+)', count_str)
                    if m:
                        total = int(m.group(1))
                    if u:
                        unread = int(u.group(1))
            except Exception:
                pass
            folders.append({
                'name': folder_name,
                'display_name': self._display_name(folder_name),
                'folder_type': self._folder_type(folder_name),
                'delimiter': parsed['delimiter'],
                'flags': parsed['flags'],
                'unread_count': unread,
                'total_count': total,
            })
        return folders

    def _select(self, folder):
        """Select a folder, quoting names with spaces."""
        return self.conn.select('"%s"' % folder)

    def list_messages(self, folder='INBOX', page=1, per_page=25, sort='date_desc'):
        self._select(folder)

        # Try IMAP SORT for proper date ordering (Dovecot supports this)
        uids = []
        try:
            if sort == 'date_desc':
                status, data = self.conn.uid('sort', '(REVERSE DATE)', 'UTF-8', 'ALL')
            else:
                status, data = self.conn.uid('sort', '(DATE)', 'UTF-8', 'ALL')
            if status == 'OK' and data[0]:
                uids = data[0].split()
        except Exception:
            pass

        # Fallback to search + reverse UIDs if SORT not supported
        if not uids:
            status, data = self.conn.uid('search', None, 'ALL')
            if status != 'OK':
                return {'messages': [], 'total': 0, 'page': page, 'pages': 0}
            uids = data[0].split() if data[0] else []
            if sort == 'date_desc':
                uids = list(reversed(uids))

        total = len(uids)
        pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, pages))

        start = (page - 1) * per_page
        end = start + per_page
        page_uids = uids[start:end]

        if not page_uids:
            return {'messages': [], 'total': total, 'page': page, 'pages': pages}

        uid_str = b','.join(page_uids)
        status, msg_data = self.conn.uid('fetch', uid_str,
                                          '(UID FLAGS ENVELOPE RFC822.SIZE BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])')
        if status != 'OK':
            return {'messages': [], 'total': total, 'page': page, 'pages': pages}

        messages = []
        i = 0
        while i < len(msg_data):
            item = msg_data[i]
            if isinstance(item, tuple) and len(item) == 2:
                meta_line = item[0].decode('utf-8', errors='replace') if isinstance(item[0], bytes) else item[0]
                header_bytes = item[1]

                uid_match = re.search(r'UID\s+(\d+)', meta_line)
                flags_match = re.search(r'FLAGS\s+\(([^)]*)\)', meta_line)
                size_match = re.search(r'RFC822\.SIZE\s+(\d+)', meta_line)

                uid = uid_match.group(1) if uid_match else '0'
                flags = flags_match.group(1) if flags_match else ''
                size = int(size_match.group(1)) if size_match else 0

                msg = email.message_from_bytes(header_bytes) if isinstance(header_bytes, bytes) else email.message_from_string(header_bytes)
                messages.append({
                    'uid': uid,
                    'from': self._decode_header_value(msg.get('From', '')),
                    'to': self._decode_header_value(msg.get('To', '')),
                    'subject': self._decode_header_value(msg.get('Subject', '(No Subject)')),
                    'date': msg.get('Date', ''),
                    'flags': flags,
                    'is_read': '\\Seen' in flags,
                    'is_flagged': '\\Flagged' in flags,
                    'has_attachment': False,
                    'size': size,
                })
            i += 1

        return {'messages': messages, 'total': total, 'page': page, 'pages': pages}

    def search_messages(self, folder='INBOX', query='', criteria='ALL'):
        self._select(folder)
        if query:
            # Escape quotes to prevent IMAP search injection
            safe_query = query.replace('\\', '\\\\').replace('"', '\\"')
            search_criteria = '(OR OR (FROM "%s") (TO "%s") (SUBJECT "%s"))' % (safe_query, safe_query, safe_query)
        else:
            search_criteria = criteria
        status, data = self.conn.uid('search', None, search_criteria)
        if status != 'OK':
            return []
        return data[0].split() if data[0] else []

    def get_message(self, folder, uid):
        self._select(folder)
        status, data = self.conn.uid('fetch', str(uid).encode(), '(RFC822 FLAGS)')
        if status != 'OK' or not data or not data[0]:
            return None

        raw = None
        flags = ''
        for item in data:
            if isinstance(item, tuple) and len(item) == 2:
                meta = item[0].decode('utf-8', errors='replace') if isinstance(item[0], bytes) else item[0]
                raw = item[1]
                flags_match = re.search(r'FLAGS\s+\(([^)]*)\)', meta)
                if flags_match:
                    flags = flags_match.group(1)
                break

        if raw is None:
            return None

        from .email_parser import EmailParser
        parsed = EmailParser.parse_message(raw)
        parsed['uid'] = str(uid)
        parsed['flags'] = flags
        parsed['is_read'] = '\\Seen' in flags
        parsed['is_flagged'] = '\\Flagged' in flags
        return parsed

    def get_attachment(self, folder, uid, part_id):
        self._select(folder)
        status, data = self.conn.uid('fetch', str(uid).encode(), '(RFC822)')
        if status != 'OK' or not data or not data[0]:
            return None

        raw = None
        for item in data:
            if isinstance(item, tuple) and len(item) == 2:
                raw = item[1]
                break

        if raw is None:
            return None

        msg = email.message_from_bytes(raw) if isinstance(raw, bytes) else email.message_from_string(raw)
        part_idx = 0
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type.startswith('multipart/'):
                continue
            disposition = str(part.get('Content-Disposition', ''))
            # Match the same indexing logic as email_parser.py:
            # count parts that are attachments or non-text with disposition
            if 'attachment' in disposition or (content_type not in ('text/html', 'text/plain') and disposition):
                if str(part_idx) == str(part_id):
                    filename = part.get_filename() or 'attachment'
                    filename = self._decode_header_value(filename)
                    payload = part.get_payload(decode=True)
                    return (filename, content_type, payload)
                part_idx += 1

        return None

    def move_messages(self, folder, uids, target_folder):
        self._select(folder)
        uid_str = ','.join(str(u) for u in uids)
        # Quote target folder name for folders with spaces (e.g. "INBOX.Deleted Items")
        quoted_target = '"%s"' % target_folder
        try:
            status, _ = self.conn.uid('move', uid_str, quoted_target)
            if status == 'OK':
                return True
        except Exception:
            pass
        status, _ = self.conn.uid('copy', uid_str, quoted_target)
        if status == 'OK':
            self.conn.uid('store', uid_str, '+FLAGS', '(\\Deleted)')
            self.conn.expunge()
            return True
        return False

    def delete_messages(self, folder, uids):
        self._select(folder)
        uid_str = ','.join(str(u) for u in uids)
        # CyberPanel/Dovecot uses "INBOX.Deleted Items" as trash
        trash_folders = ['INBOX.Deleted Items', 'INBOX.Trash', 'Trash']
        if folder not in trash_folders:
            for trash in trash_folders:
                try:
                    status, _ = self.conn.uid('copy', uid_str, '"%s"' % trash)
                    if status == 'OK':
                        self.conn.uid('store', uid_str, '+FLAGS', '(\\Deleted)')
                        self.conn.expunge()
                        return True
                except Exception:
                    continue
        # Already in trash or no trash folder found - permanently delete
        self.conn.uid('store', uid_str, '+FLAGS', '(\\Deleted)')
        self.conn.expunge()
        return True

    def set_flags(self, folder, uids, flags, action='add'):
        self._select(folder)
        uid_str = ','.join(str(u) for u in uids)
        flag_str = '(%s)' % ' '.join(flags)
        if action == 'add':
            self.conn.uid('store', uid_str, '+FLAGS', flag_str)
        elif action == 'remove':
            self.conn.uid('store', uid_str, '-FLAGS', flag_str)
        return True

    def mark_read(self, folder, uids):
        return self.set_flags(folder, uids, ['\\Seen'], 'add')

    def mark_unread(self, folder, uids):
        return self.set_flags(folder, uids, ['\\Seen'], 'remove')

    def mark_flagged(self, folder, uids):
        return self.set_flags(folder, uids, ['\\Flagged'], 'add')

    def create_folder(self, name):
        status, _ = self.conn.create(name)
        return status == 'OK'

    def rename_folder(self, old_name, new_name):
        status, _ = self.conn.rename(old_name, new_name)
        return status == 'OK'

    def delete_folder(self, name):
        status, _ = self.conn.delete(name)
        return status == 'OK'

    def append_message(self, folder, raw_message, flags=''):
        if isinstance(raw_message, str):
            raw_message = raw_message.encode('utf-8')
        flag_str = '(%s)' % flags if flags else None
        status, _ = self.conn.append('"%s"' % folder, flag_str, None, raw_message)
        return status == 'OK'
