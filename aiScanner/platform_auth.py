"""Select saved credentials belonging to the signed-in CyberPanel administrator."""


def saved_scanner_auth_headers(admin):
    if admin is None:
        return {}

    from .models import AIScannerSettings
    scanner = AIScannerSettings.objects.filter(admin=admin).first()
    if scanner and scanner.api_key:
        return {'X-API-Key': scanner.api_key}

    # A connected CyberMail installation has an independently authenticated
    # platform key. It can enroll the same owner's eligible server for scans.
    try:
        from emailDelivery.models import CyberMailAccount
    except ImportError:
        return {}
    account = CyberMailAccount.objects.filter(admin=admin, is_connected=True).first()
    if account and account.api_key and account.api_key.startswith('cpk_'):
        return {'X-CP-API-Key': account.api_key}
    return {}
