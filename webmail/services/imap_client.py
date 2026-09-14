import imaplib
import ssl
import email
import re

from .mime_utils import decode_mime_header


class IMAPOperationError(Exception):
    """A mail operation could not be completed with a verified outcome."""


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
        # IMAP CLOSE expunges every message marked \Deleted in the selected
        # mailbox. Leaving a context, including a failed operation, must not
        # permanently remove messages selected by another client.
        try:
            self.conn.logout()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _decode_header_value(self, value):
        return decode_mime_header(value)

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
        uid_str = self._delete_uid_set(uids)
        quoted_folder = self._delete_mailbox(folder)
        quoted_target = self._delete_mailbox(target_folder)
        if folder == target_folder:
            raise IMAPOperationError('Select a different destination folder before moving messages.')
        uncertain = ('The mail server did not confirm the message move. '
                     'Refresh the source and destination folders before retrying.')
        try:
            capabilities = self._selected_message_capabilities(quoted_folder, uid_str)
            self._delete_require_ok(self.conn.status(quoted_target, '(UIDVALIDITY)'),
                                    'Unable to open the destination folder. Refresh before retrying.')
            self._move_selected_messages(uid_str, quoted_target, capabilities, uncertain)
            return True
        except IMAPOperationError:
            raise
        except Exception as error:
            raise IMAPOperationError(uncertain) from error

    @staticmethod
    def _delete_uid_set(uids):
        if not isinstance(uids, list) or not uids:
            raise ValueError('Select explicit message UIDs before changing messages.')
        selected = []
        for uid in uids:
            if (isinstance(uid, bool) or not isinstance(uid, (int, str))
                    or not re.fullmatch(r'[1-9][0-9]*', str(uid))
                    or not 1 <= int(uid) <= 4294967295):
                raise ValueError('Message UIDs must be positive integers.')
            value = str(int(uid))
            if value not in selected:
                selected.append(value)
        return ','.join(selected)

    @staticmethod
    def _delete_mailbox(folder):
        if (not isinstance(folder, str) or not folder
                or any(ord(char) < 32 or ord(char) == 127 for char in folder)):
            raise ValueError('Select a valid folder before changing messages.')
        return '"%s"' % folder.replace('\\', '\\\\').replace('"', '\\"')

    @staticmethod
    def _delete_require_ok(response, message):
        if not isinstance(response, tuple) or len(response) != 2 or response[0] != 'OK':
            raise IMAPOperationError(message)
        return response[1]

    def _selected_message_capabilities(self, quoted_folder, uid_str):
        self._delete_require_ok(self.conn.select(quoted_folder),
                                'Unable to open the selected folder. Refresh before retrying.')
        # Capabilities can change after login; older imaplib releases keep
        # only their pre-authentication capability list on the connection.
        data = self._delete_require_ok(self.conn.capability(),
                                       'Unable to verify the mail server capabilities.')
        capabilities = set()
        for line in data:
            if isinstance(line, bytes):
                line = line.decode('ascii', errors='strict')
            capabilities.update(line.upper().split())
        # Confirm that the explicit UIDs are still in this selected folder
        # before creating a Trash folder or changing any message state.
        data = self._delete_require_ok(self.conn.uid('search', None, 'UID', uid_str),
                                       'Unable to verify the selected messages. Refresh before retrying.')
        found = set()
        for line in data:
            if isinstance(line, bytes):
                line = line.decode('ascii', errors='strict')
            found.update(line.split())
        if found != set(uid_str.split(',')):
            raise IMAPOperationError('The selected messages changed. Refresh the folder before retrying.')

        return capabilities

    def _move_selected_messages(self, uid_str, target, capabilities, uncertain):
        if not capabilities.intersection({'MOVE', 'UIDPLUS'}):
            raise IMAPOperationError('The mail server does not support moving only the selected messages.')
        if 'MOVE' in capabilities:
            # A rejected or interrupted MOVE may be partially complete.
            # Never retry it as COPY or switch destinations automatically.
            self._delete_require_ok(self.conn.uid('move', uid_str, target), uncertain)
        else:
            self._delete_require_ok(self.conn.uid('copy', uid_str, target), uncertain)
            self._delete_require_ok(self.conn.uid('store', uid_str, '+FLAGS', '(\\Deleted)'), uncertain)
            self._delete_require_ok(self.conn.uid('expunge', uid_str), uncertain)

    def delete_messages(self, folder, uids):
        uid_str = self._delete_uid_set(uids)
        quoted_folder = self._delete_mailbox(folder)
        uncertain = ('The mail server did not confirm message deletion. '
                     'Refresh the source folder and Trash before retrying.')
        try:
            capabilities = self._selected_message_capabilities(quoted_folder, uid_str)

            trash_folders = ['INBOX.Deleted Items', 'INBOX.Trash', 'Trash']
            if folder in trash_folders:
                if 'UIDPLUS' not in capabilities:
                    raise IMAPOperationError('The mail server does not support deleting only the selected messages.')
                self._delete_require_ok(self.conn.uid('store', uid_str, '+FLAGS', '(\\Deleted)'), uncertain)
                self._delete_require_ok(self.conn.uid('expunge', uid_str), uncertain)
                return True

            if not capabilities.intersection({'MOVE', 'UIDPLUS'}):
                raise IMAPOperationError('The mail server does not support moving only the selected messages to Trash.')
            target = None
            for trash in trash_folders:
                quoted_trash = self._delete_mailbox(trash)
                status, _ = self.conn.status(quoted_trash, '(UIDVALIDITY)')
                if status == 'OK':
                    target = quoted_trash
                    break
                if status != 'NO':
                    raise IMAPOperationError('Unable to verify the Trash folder.')
            if target is None:
                target = self._delete_mailbox(trash_folders[0])
                self._delete_require_ok(self.conn.create(target),
                                        'Unable to create the Trash folder. No messages were deleted.')
                self._delete_require_ok(self.conn.status(target, '(UIDVALIDITY)'),
                                        'Unable to verify the Trash folder. No messages were deleted.')

            self._move_selected_messages(uid_str, target, capabilities, uncertain)
            return True
        except IMAPOperationError:
            raise
        except Exception as error:
            raise IMAPOperationError(uncertain) from error

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
