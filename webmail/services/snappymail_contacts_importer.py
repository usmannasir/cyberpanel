import configparser
import os
import re
from typing import Dict, List, Tuple

import MySQLdb


class SnappymailContactsImporter:
    """
    Import contacts from SnappyMail (RainLoop) DB into CyberPanel Webmail.

    SnappyMail stores addressbook data in RainLoop tables:
      - rainloop_users (rl_email -> id_user)
      - rainloop_ab_contacts
      - rainloop_ab_properties (prop_type == 30 => EMAIL, see RainLoop PropertyType::EMAIl)

    This importer returns plain contact records; CyberPanel persists them into wm_contacts.
    """

    # SnappyMail may use either install tree; contacts [pdo_*] is identical in practice.
    CANDIDATE_APP_INI = (
        '/usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/application.ini',
        '/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/configs/application.ini',
    )

    SNAPPYMAIL_APP_INI = CANDIDATE_APP_INI[0]

    # RainLoop PropertyType::EMAIl === 30
    RAINLOOP_PROP_EMAIL = 30

    def __init__(self, app_ini_path: str = None):
        self.app_ini_path = app_ini_path or self._first_existing_ini()

    @classmethod
    def _first_existing_ini(cls) -> str:
        for p in cls.CANDIDATE_APP_INI:
            if os.path.isfile(p):
                return p
        return cls.SNAPPYMAIL_APP_INI

    @staticmethod
    def _strip_quotes(value: str) -> str:
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1].strip()
        return value

    @staticmethod
    def _parse_pdo_dsn(pdo_dsn: str) -> Dict[str, str]:
        # Example:
        #   host=127.0.0.1;port=3306;dbname=snappymail
        parts = {}
        for chunk in pdo_dsn.split(';'):
            chunk = chunk.strip()
            if not chunk:
                continue
            if '=' not in chunk:
                continue
            k, v = chunk.split('=', 1)
            parts[k.strip()] = v.strip()
        return parts

    def _load_snappymail_db_config(self) -> Tuple[str, int, str, str, str]:
        if not os.path.isfile(self.app_ini_path):
            raise FileNotFoundError('SnappyMail config not found: %s' % self.app_ini_path)

        parser = configparser.ConfigParser()
        parser.read(self.app_ini_path)

        if not parser.has_section('contacts'):
            raise ValueError('SnappyMail config missing [contacts] section.')

        pdo_dsn = self._strip_quotes(parser.get('contacts', 'pdo_dsn', fallback=''))
        user = self._strip_quotes(parser.get('contacts', 'pdo_user', fallback=''))
        password = self._strip_quotes(parser.get('contacts', 'pdo_password', fallback=''))

        if not pdo_dsn or not user:
            raise ValueError('SnappyMail contacts config incomplete (missing DSN/user).')

        dsn_parts = self._parse_pdo_dsn(pdo_dsn)
        host = dsn_parts.get('host', '127.0.0.1')
        port_raw = dsn_parts.get('port', '3306')
        dbname = dsn_parts.get('dbname', '')

        if not dbname:
            raise ValueError('SnappyMail contacts config missing dbname in DSN.')

        try:
            port = int(port_raw)
        except Exception:
            port = 3306

        return host, port, dbname, user, password

    def import_contacts(self, owner_email: str) -> List[Dict[str, str]]:
        """
        Fetch contacts for a given owner email from RainLoop DB.

        Returns:
            [
              {'email_address': 'a@b.c', 'display_name': 'Name'},
              ...
            ]
        """
        owner_email = (owner_email or '').strip()
        if not owner_email:
            return []

        host, port, dbname, user, password = self._load_snappymail_db_config()

        conn = None
        try:
            # autocommit=True so we never hold locks
            conn = MySQLdb.connect(host=host, port=port, user=user, passwd=password, db=dbname, charset='utf8mb4')
            try:
                conn.autocommit(True)
            except Exception:
                pass
            cursor = conn.cursor()

            # Find RainLoop id_user for this email
            cursor.execute(
                'SELECT id_user FROM rainloop_users WHERE LOWER(rl_email) = LOWER(%s) LIMIT 1',
                (owner_email,)
            )
            row = cursor.fetchone()
            if not row:
                return []
            id_user = int(row[0])

            # Fetch emails + display values
            # Note: one contact can have multiple email entries. We create one webmail contact per email.
            cursor.execute(
                '''
                SELECT
                    c.id_contact,
                    c.display,
                    p.prop_value AS email_address
                FROM rainloop_ab_contacts AS c
                JOIN rainloop_ab_properties AS p
                    ON p.id_contact = c.id_contact
                    AND p.id_user = c.id_user
                    AND p.prop_type = %s
                WHERE c.id_user = %s
                  AND c.deleted = 0
                  AND p.prop_value IS NOT NULL
                  AND TRIM(p.prop_value) <> ''
                ORDER BY c.display ASC
                ''',
                (self.RAINLOOP_PROP_EMAIL, id_user)
            )

            results = []
            seen = set()
            while True:
                r = cursor.fetchone()
                if not r:
                    break
                display = r[1] or ''
                email_address = (r[2] or '').strip()
                if not email_address:
                    continue
                key = email_address.lower()
                if key in seen:
                    continue
                seen.add(key)

                if display:
                    display_name = display
                else:
                    display_name = email_address.split('@')[0] if '@' in email_address else email_address

                results.append({
                    'email_address': email_address,
                    'display_name': display_name,
                })

            return results
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

