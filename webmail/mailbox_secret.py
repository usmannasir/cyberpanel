"""The mailbox password of a standalone webmail login.

A standalone login (/webmail/login) opens IMAP, SMTP and ManageSieve
connections with the mailbox password on every request, so the password has
to be kept for the length of the session.  The server-side session is a row
in the panel database; it holds only the password encrypted with a key that
exists nowhere but in the browser's cookie.  The database, or a copy of it,
alone gives no mailbox password.

Releases up to 3.0.21 kept the password itself in the session under
LEGACY_SESSION_KEY; scrub_stored_passwords() removes it from every stored
session (it runs after each "manage.py migrate", which every upgrade runs).
"""

from cryptography.fernet import Fernet, InvalidToken

SESSION_KEY = 'webmail_secret'
LEGACY_SESSION_KEY = 'webmail_password'
COOKIE_NAME = 'cyberpanel_webmail_key'
COOKIE_PATH = '/webmail'
LIFETIME = 43200


def store(request, response, password):
    """Keep password for this session; the key goes to the browser only."""
    key = Fernet.generate_key()
    token = Fernet(key).encrypt(password.encode('utf-8'))
    request.session.pop(LEGACY_SESSION_KEY, None)
    request.session[SESSION_KEY] = token.decode('ascii')
    # The rest of this request (and every later one) reads it from the cookie.
    request.COOKIES[COOKIE_NAME] = key.decode('ascii')
    response.set_cookie(
        COOKIE_NAME, key.decode('ascii'), max_age=LIFETIME, path=COOKIE_PATH,
        secure=True, httponly=True, samesite='Lax',
    )
    return response


def present(request):
    """True when this request can recover the session's mailbox password."""
    return bool(password(request))


def password(request):
    """The session's mailbox password, or '' when it cannot be recovered."""
    token = request.session.get(SESSION_KEY)
    key = request.COOKIES.get(COOKIE_NAME)
    if not token or not key:
        return ''
    try:
        return Fernet(key.encode('ascii')).decrypt(
            token.encode('ascii'), ttl=LIFETIME).decode('utf-8')
    except (InvalidToken, TypeError, ValueError):
        return ''


def forget(request, response):
    request.session.pop(SESSION_KEY, None)
    request.session.pop(LEGACY_SESSION_KEY, None)
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)
    return response


def scrub_stored_passwords(session_model=None, store_class=None):
    """Remove plain mailbox passwords that older releases kept in sessions.

    Expired sessions are never deleted by the panel, so the rows stay in the
    database (and its backups): expired ones are deleted, live ones rewritten
    without the password.  Returns the number of live sessions changed;
    never raises.
    """
    try:
        if session_model is None:
            from django.contrib.sessions.models import Session as session_model
        if store_class is None:
            from django.contrib.sessions.backends.db import SessionStore as store_class
        try:
            # Expired sessions are never loaded again; this is what Django's
            # clearsessions does, and it leaves only live rows to decode.
            store_class.clear_expired()
        except Exception:
            pass
        codec = store_class()
        changed = 0
        rows = session_model.objects.only('session_key', 'session_data').iterator()
        for row in rows:
            try:
                data = codec.decode(row.session_data)
            except Exception:
                continue
            if not isinstance(data, dict) or LEGACY_SESSION_KEY not in data:
                continue
            data.pop(LEGACY_SESSION_KEY, None)
            session_model.objects.filter(session_key=row.session_key).update(
                session_data=codec.encode(data))
            changed += 1
        return changed
    except Exception as error:
        try:
            import plogical.CyberCPLogFileWriter as logging
            logging.CyberCPLogFileWriter.writeToFile(
                'Webmail session password scrub did not complete: %s' % type(error).__name__)
        except Exception:
            pass
        return 0
