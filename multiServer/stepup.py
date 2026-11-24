"""The second check before a Multi-Server Manager action that is not easily taken back.

Pairing, ending a link, removing a server and changing the role each ask the
signed-in administrator again for the account's password and a fresh code of
its second factor (confirm). Two rules hold whichever worker process answers,
because what they rest on is kept in the administrator's own row, read and
written under a lock on that row:

  * after MAX_FAILURES wrong attempts within WINDOW seconds nothing more is
    checked for that account until the window has passed, so neither the
    password nor the code can be searched for through these forms;
  * a code is accepted once: a later check passes only with a code for a
    later half minute than the last one accepted.

The count and the last half minute are one small entry (KEPT_AS) in the JSON
text of Administrator.config. Nothing here writes a password or a code
anywhere, and no error holds one.

An administrator without two-factor login sets it up on the role page itself
(start, setup, enrol), as on Users > Modify User: every set-up gets a new key,
and two-factor is switched on only with a code from the app the key was added
to. Switching it on also takes the account's password and follows the two
rules above, so the code of the set-up is not accepted again afterwards.

Only the controller needs two-factor login, because it can open the panels of
all its servers. On a managed server, and for turning Multi-Server off, an
account without a second factor confirms with its password alone
(two_factor=False); an account that has one always gives a code too.

Once confirmed, an administrator is not asked again for RECENT seconds in the
same panel session (check, remember, recent). What is kept for that is in the
session, which lives on this server: whose check it was, when, whether a code
was part of it, and a stamp of the account that changes with its password, its
second factor and its access level. A check made with the password alone never
stands in for one that needs a code.
"""
import hmac
import json
import re
import time

MAX_FAILURES = 5
WINDOW = 15 * 60  # seconds
STEP = 30  # seconds one code stands for
KEPT_AS = 'multiServerStepUp'
MAX_PASSWORD = 4096
RECENT = 15 * 60  # seconds a confirmation counts for, in the session it was made in
SESSION_KEY = 'ms_checked'

LOCKED = ('Too many wrong passwords or codes. Wait %d minutes, then try again.' % (WINDOW // 60))
WRONG = ('Enter your current password and a new code from your authenticator app. A code works once: if you '
         'have just used it, wait for the next one.')
WRONG_PASSWORD = 'Enter your current password.'

_CODE = re.compile(r'[0-9]{6}')


def confirm(admin_id, password, code, two_factor=True):
    """None when the password and the code are this account's and the code is new; otherwise why not.

    With two_factor=False an account without a second factor passes with its
    password alone; an account with one still needs a new code.

    The reason is one the audit trail knows: 'password', 'two_factor',
    'not_allowed' while the account is shut out of this check, 'admin' when
    the account is not a full administrator (with a second factor, unless
    two_factor is False), 'internal' when its row cannot be read or written.
    Never raises.
    """
    try:
        from django.db import transaction
        with transaction.atomic():
            return _confirm(admin_id, password, code, int(time.time()), password_only=not two_factor)
    except Exception:
        return 'internal'


def check(request, admin, two_factor=True):
    """None when the signed-in administrator confirmed recently enough or does so now; otherwise why not.

    Asks for the password (and a code, see confirm) in request.POST only when
    no confirmation of this account counts any more in this session (recent).
    A new confirmation is remembered. On a controller, one made with a code
    also counts as a sign-in made with one (sso.remember_login), as on the
    sign-in page. Never raises.
    """
    try:
        if recent(request, admin, two_factor):
            return None
        reason = confirm(admin.pk, request.POST.get('password', ''), request.POST.get('code', ''), two_factor)
        if reason is None:
            from loginSystem.models import Administrator
            current = Administrator.objects.get(pk=admin.pk)
            from multiServer import views
            with_code = views.two_factor_enrolled(current)
            remember(request, current, with_code)
            if with_code:
                _signed_in_with_code(request, current)
        return reason
    except Exception:
        return 'internal'


def remember(request, admin, with_code):
    """Note in the session that this administrator has just confirmed, with a code or not. Never raises."""
    try:
        request.session[SESSION_KEY] = [admin.pk, int(time.time()), bool(with_code), _account(admin)]
    except Exception:
        pass


def recent(request, admin, two_factor=True):
    """Whether this administrator confirmed in this session less than RECENT seconds ago. Never raises.

    With two_factor, only a confirmation made with a code counts, and only
    for an account that still has a second factor.
    """
    try:
        from multiServer import views
        kept = request.session.get(SESSION_KEY)
        if type(kept) is not list or len(kept) != 4:
            return False
        admin_id, when, with_code, account = kept
        if type(admin_id) is not int or admin_id != admin.pk or type(when) is not int or type(with_code) is not bool:
            return False
        if not 0 <= int(time.time()) - when < RECENT:
            return False
        enrolled = views.two_factor_enrolled(admin)
        # An account with a second factor confirms with a code, whatever the check asks for.
        if (two_factor or enrolled) and not (with_code and enrolled):
            return False
        return type(account) is str and hmac.compare_digest(account, _account(admin))
    except Exception:
        return False


def forget(request):
    """Ask for the password again at the next check in this session. Never raises."""
    try:
        request.session.pop(SESSION_KEY, None)
    except Exception:
        pass


def _account(admin):
    from multiServer import sso
    return sso.account_stamp(admin)


def _signed_in_with_code(request, admin):
    from multiServer import keys, sso
    if keys.role() == keys.CONTROLLER and request.is_secure():
        sso.remember_login(request, admin)


def enrol(admin_id, password, code):
    """Switch on two-factor login with the key of its set-up: None when done, otherwise why not.

    The reasons are those of confirm(); 'admin' also when the account already
    has two-factor login or has no key of a set-up. Never raises.
    """
    try:
        from django.db import transaction
        with transaction.atomic():
            return _confirm(admin_id, password, code, int(time.time()), enrolling=True)
    except Exception:
        return 'internal'


def start(admin_id):
    """Give a full administrator without two-factor login the new key of a set-up; True when done. Never raises."""
    try:
        import pyotp
        from django.db import transaction
        from loginSystem.models import Administrator
        from multiServer import views
        with transaction.atomic():
            if views.active_full_administrator(admin_id) is None:
                return False
            rows = Administrator.objects.filter(pk=admin_id)
            if views.two_factor_enrolled(rows.select_for_update().get()):
                return False
            # Off until a code from the app proves the key was added: the account is not shut out meanwhile.
            return rows.update(twoFA=0, secretKey=pyotp.random_base32()) == 1
    except Exception:
        return False


def setup(admin, label):
    """(key, otpauth address) of the set-up of an account without two-factor login, or None. Never raises."""
    try:
        from multiServer import views
        if views.two_factor_enrolled(admin) or admin.twoFA == 1:
            return None
        import pyotp
        totp = pyotp.TOTP(admin.secretKey)
        totp.byte_secret()
        return admin.secretKey, totp.provisioning_uri(name=label, issuer_name='CyberPanel')
    except Exception:
        return None


def message(reason, admin=None):
    """What to tell the administrator for a reason confirm() gave; a fixed text.

    Given the account, one without two-factor login is not asked for a code.
    """
    if reason == 'not_allowed':
        return LOCKED
    if admin is not None:
        from multiServer import views
        if not views.two_factor_enrolled(admin):
            return WRONG_PASSWORD
    return WRONG


def _confirm(admin_id, password, code, now, enrolling=False, password_only=False):
    from loginSystem.models import Administrator
    from multiServer import views
    from plogical import hashPassword
    if views.active_full_administrator(admin_id) is None:
        return 'admin'
    rows = Administrator.objects.filter(pk=admin_id)
    # The row is locked from here to the end of the transaction: attempts made at the same moment in
    # other workers wait, and each of them then sees the count this one leaves.
    administrator = rows.select_for_update().get()
    enrolled = views.two_factor_enrolled(administrator)
    if enrolling and enrolled:
        return 'admin'
    if not enrolling and not enrolled and not password_only:
        return 'admin'
    if enrolling and setup(administrator, '') is None:
        return 'admin'
    config = json.loads(administrator.config or '{}')
    if type(config) is not dict:
        raise ValueError('The settings of the account are not a JSON object.')
    failures, since, last = _kept(config.get(KEPT_AS))
    if not 0 <= now - since < WINDOW:
        failures = 0
    if failures >= MAX_FAILURES:
        return 'not_allowed'
    reason, step = None, last
    if (type(password) is not str or not 0 < len(password) <= MAX_PASSWORD
            or not hashPassword.check_password(administrator.password, password)):
        reason = 'password'
    elif not enrolling and not enrolled:
        pass  # password_only: an account without a second factor has nothing more to give
    else:
        step = _step(administrator.secretKey, code, now, last)
        if step is None:
            reason = 'two_factor'
            if _step(administrator.secretKey, code, now, -1) is not None:
                # The right code, used for an earlier check: a form sent twice, or a second action in
                # the same half minute. Refused, but nobody guessed anything, so it is not counted.
                return reason
    if reason is None:
        config[KEPT_AS] = [0, 0, step]
    else:
        config[KEPT_AS] = [failures + 1, since if failures else now, last]
    if reason is None and enrolling:
        rows.update(config=json.dumps(config), twoFA=1)
    else:
        rows.update(config=json.dumps(config))
    return reason


def _kept(entry):
    """(wrong attempts, when the first of them was, the half minute of the last code accepted)."""
    if (type(entry) is list and len(entry) == 3
            and all(type(value) is int and 0 <= value < 10 ** 11 for value in entry)):
        return tuple(entry)
    return 0, 0, 0


def _step(secret, code, now, last):
    """The half minute `code` stands for when it is a code of this account that was not used before, else None."""
    if type(code) is not str or _CODE.fullmatch(code) is None:
        return None
    import pyotp
    totp = pyotp.TOTP(secret)
    current, found = now // STEP, None
    # The half minute before and after count too, as when signing in. Each is compared, whatever the others gave.
    for candidate in (current - 1, current, current + 1):
        if hmac.compare_digest(totp.generate_otp(candidate), code) and candidate > last:
            found = candidate
    return found
