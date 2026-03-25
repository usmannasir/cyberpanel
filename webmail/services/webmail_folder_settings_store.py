import fcntl
import json
import os
from typing import Any, Dict, List

from .imap_defaults import IMAPDefaults


class WebmailFolderSettingsStore:
    """
    File-based storage for folder mappings and ordering.

    This avoids DB migrations for a fast server-side feature rollout.

    Default path is under /usr/local/CyberCP/ (root:cyberpanel, 775) so the
    lswsgi/cyberpanel user can write. Older installs used /etc/cyberpanel/
    (root:root) which causes Permission denied for the app user; we migrate
    reads from that legacy path when the new file does not exist yet.

    Override with env CYBERPANEL_WEBMAIL_FOLDER_SETTINGS (absolute file path).
    """

    # Legacy location (often not writable by cyberpanel user)
    LEGACY_STORE_PATH = '/etc/cyberpanel/webmail_folder_settings.json'
    # Writable alongside CyberPanel code for typical CyberPanel deployments
    STORE_PATH = '/usr/local/CyberCP/webmail_folder_settings.json'

    DEFAULT_SPECIAL_DISPLAY_MODE = 'top'

    # If anything resolves here, force writes to this path (panel user can write CyberCP dir).
    _WRITABLE_FALLBACK = '/usr/local/CyberCP/webmail_folder_settings.json'

    @staticmethod
    def _is_under_etc_cyberpanel(path: str) -> bool:
        try:
            ap = os.path.realpath(os.path.abspath(path))
        except Exception:
            ap = os.path.abspath(path or '')
        pref = '/etc/cyberpanel' + os.sep
        return ap == '/etc/cyberpanel' or ap.startswith(pref)

    def __init__(self, store_path: str = None):
        """Primary file used for *read* first lookup. Never an unwritable /etc path."""
        env = (os.environ.get('CYBERPANEL_WEBMAIL_FOLDER_SETTINGS') or '').strip()
        explicit = (store_path or env or '').strip()
        self.store_path = self.STORE_PATH
        if explicit:
            try:
                ap = os.path.realpath(os.path.abspath(explicit))
            except Exception:
                ap = os.path.abspath(explicit)
            try:
                leg = os.path.realpath(os.path.abspath(self.LEGACY_STORE_PATH))
            except Exception:
                leg = os.path.abspath(self.LEGACY_STORE_PATH)
            etc_bad = self._is_under_etc_cyberpanel(ap) or ap == leg
            if not etc_bad:
                self.store_path = explicit

    def _write_store_path(self) -> str:
        """Persist only to a writable path (never /etc/cyberpanel)."""
        if self._is_under_etc_cyberpanel(self.STORE_PATH):
            return self._WRITABLE_FALLBACK
        try:
            sp = os.path.realpath(os.path.abspath((self.store_path or '').strip() or self.STORE_PATH))
        except Exception:
            sp = os.path.abspath(self.STORE_PATH)
        if self._is_under_etc_cyberpanel(sp):
            return self._WRITABLE_FALLBACK
        try:
            leg = os.path.realpath(os.path.abspath(self.LEGACY_STORE_PATH))
            if sp == leg:
                return self._WRITABLE_FALLBACK
        except Exception:
            pass
        return self.store_path

    def _write_all(self, all_data: Dict[str, Any]) -> None:
        out_path = self._write_store_path()
        if self._is_under_etc_cyberpanel(out_path):
            out_path = self._WRITABLE_FALLBACK
        self._ensure_store_dir(out_path)
        tmp_path = out_path + '.tmp'
        payload = json.dumps(all_data, indent=2, sort_keys=True, ensure_ascii=False)

        with open(tmp_path, 'w', encoding='utf-8') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            finally:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass

        try:
            os.chmod(tmp_path, 0o600)
        except Exception:
            pass

        os.rename(tmp_path, out_path)

    def _ensure_store_dir(self, target_file: str = None) -> None:
        t = target_file or self.store_path
        d = os.path.dirname(os.path.abspath(t))
        if not d:
            return
        try:
            os.makedirs(d, mode=0o750, exist_ok=True)
        except Exception:
            # If we can't create the dir, we'll fail on write with a clear error later.
            pass

    def _active_read_path(self) -> str:
        """Prefer new store path; fall back to legacy file for one-time migration reads."""
        if os.path.isfile(self.store_path):
            return self.store_path
        if os.path.isfile(self.LEGACY_STORE_PATH):
            return self.LEGACY_STORE_PATH
        return self.store_path

    # Older webmail default; migrate to SnappyMail-style order (Sent + Archive at top block).
    _LEGACY_SPECIAL_ORDER = (
        'inbox', 'spam', 'deleted_items', 'junk_e_mail', 'drafts', 'trash')

    # Previous default (8 keys); migrate to compact top bar: Inbox..Spam..Trash..Archive.
    _INTERMEDIATE_SPECIAL_ORDER = (
        'inbox', 'sent', 'drafts', 'spam', 'deleted_items', 'archive',
        'junk_e_mail', 'trash',
    )

    def _defaults(self) -> Dict[str, Any]:
        # Semantic keys used by the UI.
        junk = IMAPDefaults.SPECIAL_FOLDERS.get('junk', 'INBOX.Junk E-mail')
        trash = IMAPDefaults.SPECIAL_FOLDERS.get('trash', 'INBOX.Deleted Items')
        drafts = IMAPDefaults.SPECIAL_FOLDERS.get('drafts', 'INBOX.Drafts')
        sent = IMAPDefaults.SPECIAL_FOLDERS.get('sent', 'INBOX.Sent')
        archive = IMAPDefaults.SPECIAL_FOLDERS.get('archive', 'INBOX.Archive')

        return {
            'specialDisplayMode': self.DEFAULT_SPECIAL_DISPLAY_MODE,  # 'top' or 'interleaved'
            'folderMappings': {
                'inbox': 'INBOX',
                'sent': sent,
                'spam': junk,  # semantic alias for junk folder
                'deleted_items': trash,
                'junk_e_mail': junk,
                'drafts': drafts,
                'trash': trash,
                'archive': archive,
            },
            # Order of all folders when specialDisplayMode='interleaved'.
            # When 'top', this order is still kept as: special group + other group.
            'folderOrder': [],
            # Special bar (top mode): Inbox, Sent, Drafts, Spam, Trash, Archive.
            # Semantic keys deleted_items / junk_e_mail stay in folderMappings only.
            'specialOrder': [
                'inbox', 'sent', 'drafts', 'spam', 'trash', 'archive',
            ],
            'enableDragDrop': True,
        }

    def _read_all(self) -> Dict[str, Any]:
        self._ensure_store_dir()
        read_path = self._active_read_path()
        if not os.path.isfile(read_path):
            return {}

        try:
            with open(read_path, 'r', encoding='utf-8', errors='replace') as f:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    raw = f.read()
                finally:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
        except (OSError, PermissionError, IOError):
            return {}
        raw = raw.strip()
        if not raw:
            return {}
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def get_for_account(self, email_account: str) -> Dict[str, Any]:
        email_account = (email_account or '').strip()
        if not email_account:
            return self._defaults()

        all_data = self._read_all()
        accounts = all_data.get('accounts', {})
        if not isinstance(accounts, dict):
            accounts = {}

        if email_account in accounts and isinstance(accounts[email_account], dict):
            defaults = self._defaults()
            merged = defaults

            account_cfg = accounts[email_account]
            if not isinstance(account_cfg, dict):
                account_cfg = {}

            # Merge top-level keys (shallow).
            merged.update(account_cfg)

            # Merge folderMappings with defaults (ensures required semantic keys exist).
            if not isinstance(account_cfg.get('folderMappings'), dict):
                merged['folderMappings'] = defaults['folderMappings']
            else:
                merged['folderMappings'] = defaults['folderMappings'].copy()
                merged['folderMappings'].update(account_cfg['folderMappings'])

            # Single junk mailbox: Spam mapping drives junk_e_mail (no duplicate role).
            _sp = (merged['folderMappings'].get('spam') or '').strip()
            if _sp:
                merged['folderMappings']['junk_e_mail'] = _sp

            if not isinstance(merged.get('folderOrder'), list):
                merged['folderOrder'] = []
            if not isinstance(merged.get('specialOrder'), list):
                merged['specialOrder'] = self._defaults()['specialOrder']
            else:
                so = tuple(merged.get('specialOrder') or [])
                if so == self._LEGACY_SPECIAL_ORDER:
                    merged['specialOrder'] = list(self._defaults()['specialOrder'])
                elif so == self._INTERMEDIATE_SPECIAL_ORDER:
                    merged['specialOrder'] = list(self._defaults()['specialOrder'])
            edd = merged.get('enableDragDrop')
            if isinstance(edd, str):
                merged['enableDragDrop'] = edd.strip().lower() in ('1', 'true', 'yes', 'on')
            elif edd is None:
                merged['enableDragDrop'] = self._defaults()['enableDragDrop']
            else:
                merged['enableDragDrop'] = bool(edd)
            return merged

        # Initialize for this account in-memory (write happens on save).
        return self._defaults()

    def save_for_account(self, email_account: str, data: Dict[str, Any]) -> None:
        email_account = (email_account or '').strip()
        if not email_account:
            raise ValueError('email_account is required')

        if not isinstance(data, dict):
            raise ValueError('folder settings must be an object')

        all_data = self._read_all()
        if not isinstance(all_data, dict):
            all_data = {}

        if 'accounts' not in all_data or not isinstance(all_data['accounts'], dict):
            all_data['accounts'] = {}

        current = self._defaults()

        # Merge but only keep recognized top-level keys.
        merged = current
        for key in ['specialDisplayMode', 'folderMappings', 'folderOrder', 'specialOrder', 'enableDragDrop']:
            if key in data:
                merged[key] = data[key]

        # Normalize shapes
        if not isinstance(merged.get('folderMappings'), dict):
            merged['folderMappings'] = current['folderMappings']
        if not isinstance(merged.get('folderOrder'), list):
            merged['folderOrder'] = []
        if not isinstance(merged.get('specialOrder'), list):
            merged['specialOrder'] = current['specialOrder']
        edd = merged.get('enableDragDrop')
        if isinstance(edd, bool):
            merged['enableDragDrop'] = edd
        elif isinstance(edd, str):
            merged['enableDragDrop'] = edd.strip().lower() in ('1', 'true', 'yes', 'on')
        elif edd is None:
            merged['enableDragDrop'] = current['enableDragDrop']
        else:
            merged['enableDragDrop'] = bool(edd)
        if merged.get('specialDisplayMode') not in ['top', 'interleaved']:
            merged['specialDisplayMode'] = self.DEFAULT_SPECIAL_DISPLAY_MODE

        _sp = (merged.get('folderMappings') or {}).get('spam') or ''
        if isinstance(_sp, str) and _sp.strip():
            merged.setdefault('folderMappings', {})
            merged['folderMappings']['junk_e_mail'] = _sp.strip()

        all_data['accounts'][email_account] = merged
        self._write_all(all_data)

