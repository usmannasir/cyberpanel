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


def scanner_payment_setup_request(admin, cyberpanel_host):
    """Build a callback request without trusting a caller-supplied account email."""
    from urllib.parse import urlsplit
    headers = saved_scanner_auth_headers(admin)
    if not headers:
        return None
    try:
        callback = urlsplit('https://' + cyberpanel_host)
        if not callback.hostname or callback.username or callback.password or callback.path or callback.query or callback.fragment:
            return None
        callback.port
    except (TypeError, ValueError):
        return None
    return {
        'domain': callback.hostname,
        'return_url': 'https://' + cyberpanel_host + '/aiscanner/setup-complete/',
    }, headers


PLATFORM_HOST = 'platform.cyberpersons.com'


def platform_page_url(url):
    """An address the platform returned for the browser to open, or None.

    The browser is sent only to an https page on the platform itself.
    """
    from urllib.parse import urlsplit
    if not isinstance(url, str) or not url or len(url) > 2048 or any(ord(char) <= 32 or char == '\\' for char in url):
        return None
    try:
        parts = urlsplit(url)
        if parts.hostname != PLATFORM_HOST or parts.username or parts.password or parts.port not in (None, 443):
            return None
    except ValueError:
        return None
    if parts.scheme == 'http':
        # Same host: only the scheme is raised.
        return 'https' + url[4:]
    return url if parts.scheme == 'https' else None
