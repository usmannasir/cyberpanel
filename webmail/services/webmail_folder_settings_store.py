import fcntl
import json
import os
from typing import Any, Dict, List

from .imap_defaults import IMAPDefaults


class WebmailFolderSettingsStore:
    """
    File-based storage for folder mappings and ordering.

    This avoids DB migrations for a fast server-side feature rollout.
    Data is stored per-email account inside /etc/cyberpanel/.
    """

    STORE_DIR = '/etc/cyberpanel'
    STORE_PATH = '/etc/cyberpanel/webmail_folder_settings.json'

    DEFAULT_SPECIAL_DISPLAY_MODE = 'top'

    def __init__(self, store_path: str = None):
        self.store_path = store_path or self.STORE_PATH

    def _ensure_store_dir(self) -> None:
        try:
            os.makedirs(self.STORE_DIR, mode=0o700, exist_ok=True)
        except Exception:
            # If we can't create the dir, we'll fail on write with a clear error later.
            pass

    def _defaults(self) -> Dict[str, Any]:
        # Semantic keys used by the UI.
        junk = IMAPDefaults.SPECIAL_FOLDERS.get('junk', 'INBOX.Junk E-mail')
        trash = IMAPDefaults.SPECIAL_FOLDERS.get('trash', 'INBOX.Deleted Items')
        drafts = IMAPDefaults.SPECIAL_FOLDERS.get('drafts', 'INBOX.Drafts')

        return {
            'specialDisplayMode': self.DEFAULT_SPECIAL_DISPLAY_MODE,  # 'top' or 'interleaved'
            'folderMappings': {
                'inbox': 'INBOX',
                'spam': junk,  # semantic alias for junk folder
                'deleted_items': trash,
                'junk_e_mail': junk,
                'drafts': drafts,
                'trash': trash,
            },
            # Order of all folders when specialDisplayMode='interleaved'.
            # When 'top', this order is still kept as: special group + other group.
            'folderOrder': [],
            # Semantic group order for the "top" special section.
            'specialOrder': ['inbox', 'spam', 'deleted_items', 'junk_e_mail', 'drafts', 'trash'],
            'enableDragDrop': True,
        }

    def _read_all(self) -> Dict[str, Any]:
        self._ensure_store_dir()
        if not os.path.isfile(self.store_path):
            return {}

        with open(self.store_path, 'r', encoding='utf-8', errors='replace') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                raw = f.read()
            finally:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass
        raw = raw.strip()
        if not raw:
            return {}
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def _write_all(self, all_data: Dict[str, Any]) -> None:
        self._ensure_store_dir()
        tmp_path = self.store_path + '.tmp'
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

        # Restrict permissions; file can contain folder names but no secrets.
        try:
            os.chmod(tmp_path, 0o600)
        except Exception:
            pass

        os.rename(tmp_path, self.store_path)

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

            if not isinstance(merged.get('folderOrder'), list):
                merged['folderOrder'] = []
            if not isinstance(merged.get('specialOrder'), list):
                merged['specialOrder'] = self._defaults()['specialOrder']
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

        all_data['accounts'][email_account] = merged
        self._write_all(all_data)

