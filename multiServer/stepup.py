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

LOCKED = ('Too many wrong passwords or codes. Wait %d minutes, then try again.' % (WINDOW // 60))
WRONG = ('Enter your current password and a new code from your authenticator app. A code works once: if you '
         'have just used it, wait for the next one.')

_CODE = re.compile(r'[0-9]{6}')


def confirm(admin_id, password, code):
    """None when the password and the code are this account's and the code is new; otherwise why not.

    The reason is one the audit trail knows: 'password', 'two_factor',
    'not_allowed' while the account is shut out of this check, 'admin' when
    the account is not a full administrator with a second factor, 'internal'
    when its row cannot be read or written. Never raises.
    """
    try:
        from django.db import transaction
        with transaction.atomic():
            return _confirm(admin_id, password, code, int(time.time()))
    except Exception:
        return 'internal'


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


def message(reason):
    """What to tell the administrator for a reason confirm() gave; a fixed text."""
    return LOCKED if reason == 'not_allowed' else WRONG


def _confirm(admin_id, password, code, now, enrolling=False):
    from loginSystem.models import Administrator
    from multiServer import views
    from plogical import hashPassword
    if views.active_full_administrator(admin_id) is None:
        return 'admin'
    rows = Administrator.objects.filter(pk=admin_id)
    # The row is locked from here to the end of the transaction: attempts made at the same moment in
    # other workers wait, and each of them then sees the count this one leaves.
    administrator = rows.select_for_update().get()
    if views.two_factor_enrolled(administrator) == enrolling:
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
    reason, step = None, None
    if (type(password) is not str or not 0 < len(password) <= MAX_PASSWORD
            or not hashPassword.check_password(administrator.password, password)):
        reason = 'password'
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
