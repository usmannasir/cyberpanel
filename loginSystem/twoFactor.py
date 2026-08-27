import json
import secrets
import time

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction

from loginSystem.models import Administrator


RECOVERY_CODES_KEY = 'twoFARecoveryCodes'
PENDING_CODES_KEY = 'pendingTwoFARecoveryCodes'
PENDING_CREATED_KEY = 'pendingTwoFARecoveryCodesCreated'
PENDING_LIFETIME_SECONDS = 900
RECOVERY_CODE_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'


def _load_config(account):
    try:
        config = json.loads(account.config)
        if isinstance(config, dict):
            return config
    except (TypeError, ValueError):
        pass
    return {}


def _normalize_recovery_code(code):
    return ''.join(
        character for character in str(code).upper()
        if character.isalnum()
    )


def _new_recovery_code():
    raw = ''.join(secrets.choice(RECOVERY_CODE_ALPHABET) for unused in range(10))
    return raw[:5] + '-' + raw[5:]


def prepare_recovery_codes(account, count=10):
    codes = [_new_recovery_code() for unused in range(count)]
    config = _load_config(account)
    config[PENDING_CODES_KEY] = [
        make_password(_normalize_recovery_code(code)) for code in codes
    ]
    config[PENDING_CREATED_KEY] = int(time.time())
    account.config = json.dumps(config)
    account.save(update_fields=['config'])
    return codes


def confirm_recovery_codes(account):
    config = _load_config(account)
    pending = config.get(PENDING_CODES_KEY)
    created = config.get(PENDING_CREATED_KEY, 0)
    try:
        pendingAge = int(time.time()) - int(created)
        pendingIsCurrent = 0 <= pendingAge <= PENDING_LIFETIME_SECONDS
    except (TypeError, ValueError):
        pendingIsCurrent = False

    if not isinstance(pending, list) or len(pending) != 10 or not pendingIsCurrent:
        return False

    config[RECOVERY_CODES_KEY] = pending
    config.pop(PENDING_CODES_KEY, None)
    config.pop(PENDING_CREATED_KEY, None)
    account.config = json.dumps(config)
    account.save(update_fields=['config'])
    return True


def clear_recovery_codes(account):
    config = _load_config(account)
    config.pop(RECOVERY_CODES_KEY, None)
    config.pop(PENDING_CODES_KEY, None)
    config.pop(PENDING_CREATED_KEY, None)
    account.config = json.dumps(config)
    account.save(update_fields=['config'])


def consume_recovery_code(account_id, code):
    normalized = _normalize_recovery_code(code)
    if not normalized:
        return False

    with transaction.atomic():
        account = Administrator.objects.select_for_update().get(pk=account_id)
        config = _load_config(account)
        recoveryCodes = config.get(RECOVERY_CODES_KEY, [])

        for index, storedCode in enumerate(recoveryCodes):
            if check_password(normalized, storedCode):
                del recoveryCodes[index]
                config[RECOVERY_CODES_KEY] = recoveryCodes
                account.config = json.dumps(config)
                account.save(update_fields=['config'])
                return True

    return False
