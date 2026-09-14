"""Session-bound phpMyAdmin grants; no database credentials are stored here."""
import hashlib
import ipaddress
import secrets


GRANT_KEY = 'phpmyadmin_signon_grant'


def panel_ip_allowed(session, client_ip, security_level):
    """Keep the panel's exact IPv4 and three-group IPv6 HIGH/LOW policy."""
    try:
        ipaddress.ip_address(client_ip)
    except (ValueError, TypeError):
        return False
    if security_level == 1:
        return True
    if security_level != 0:
        return False
    expected = client_ip if '.' in client_ip else ':'.join(client_ip.split(':')[:3])
    return session.get('ipAddr') == expected


def authorization_version(token):
    if not isinstance(token, str) or not token:
        raise ValueError('Missing database authorization')
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def issue_grant(session, user_id, username, token, is_admin):
    session_key = session.session_key
    if not isinstance(session_key, str) or not session_key:
        raise ValueError('Missing originating session')
    if session.get('userID') != user_id or not isinstance(user_id, int) or isinstance(user_id, bool):
        raise ValueError('Invalid principal')
    if not isinstance(username, str) or not username or len(username) > 255:
        raise ValueError('Invalid database username')
    grant = secrets.token_hex(32)
    session[GRANT_KEY] = {
        'grant': grant, 'session_key': session_key, 'user_id': user_id,
        'username': username, 'authorization': authorization_version(token),
        'is_admin': bool(is_admin),
    }
    session.modified = True
    return grant


def validate_grant(session, user_id, username, grant, token, is_admin):
    """Read only: validation neither renews nor extends the panel session."""
    saved = session.get(GRANT_KEY)
    if not isinstance(saved, dict) or session.get('userID') != user_id:
        return False
    expected = {
        'session_key': session.session_key, 'user_id': user_id,
        'username': username, 'is_admin': bool(is_admin),
    }
    if any(saved.get(key) != value for key, value in expected.items()):
        return False
    try:
        return (isinstance(grant, str) and len(grant) == 64
                and isinstance(saved.get('grant'), str)
                and secrets.compare_digest(saved['grant'], grant)
                and secrets.compare_digest(saved.get('authorization', ''), authorization_version(token)))
    except (TypeError, ValueError):
        return False
