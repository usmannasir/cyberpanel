import secrets
import time


HANDOFF_SESSION_KEY = 'phpmyadmin_handoff'
HANDOFF_TTL = 120


def create_handoff(session, username, token, now=None, ttl=HANDOFF_TTL):
    if not isinstance(username, str) or not username or len(username) > 255:
        raise ValueError('Invalid phpMyAdmin handoff username')
    if not isinstance(token, str) or not token or len(token) > 512:
        raise ValueError('Invalid phpMyAdmin handoff token')
    if not isinstance(ttl, int) or ttl < 1 or ttl > 300:
        raise ValueError('Invalid phpMyAdmin handoff lifetime')

    now = int(time.time() if now is None else now)
    session[HANDOFF_SESSION_KEY] = {
        'username': username,
        'token': token,
        'expires': now + ttl,
    }
    session.modified = True


def consume_handoff(session, username, token, now=None):
    handoff = session.pop(HANDOFF_SESSION_KEY, None)
    session.modified = True

    if not isinstance(handoff, dict):
        return False
    if not isinstance(username, str) or not isinstance(token, str):
        return False

    expected_username = handoff.get('username')
    expected_token = handoff.get('token')
    expires = handoff.get('expires')
    now = int(time.time() if now is None else now)

    if not isinstance(expected_username, str):
        return False
    if not isinstance(expected_token, str):
        return False
    if not isinstance(expires, int) or expires <= now:
        return False

    return (
        secrets.compare_digest(expected_username, username)
        and secrets.compare_digest(expected_token, token)
    )
