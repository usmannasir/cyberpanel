"""What has to be in place before a scan can start, and what to tell the user when it is not.

Every request to the scanner platform is made in the name of an account
connected to the signed-in panel account: a scanner key from an earlier
payment set-up or free scan, or a connected CyberMail account. Without one
the free scans of the server cannot be used, payment cannot be set up and
no scan starts. CyberMail accounts are connected on the Email Delivery
page, which only administrators can open.

This module only words the refusals and the page's notice. It decides
nothing about who may scan, reads nothing and sends nothing.
"""

ACCOUNT_REQUIRED = 'account_required'
PAYMENT_REQUIRED = 'payment_required'
SERVER_NOT_VERIFIED = 'server_not_verified'

NOTHING_STARTED = 'No scan was started.'
NO_ACCOUNT = 'No CyberMail or scanner account is connected to your panel account'
CONNECT = 'open Email Delivery, choose Get Started Free and connect a CyberMail account'
ASK_ADMINISTRATOR = ('Accounts are connected on the Email Delivery page, which only an administrator can open: '
                     'ask the server administrator.')


def account_missing(auth_headers):
    """Whether the panel account has no connected account to speak to the platform with."""
    return not auth_headers


def reason(auth_headers, free):
    """Why a step that needs the platform cannot go on.

    free: the step was the request for this server's free-scan key, which
    the platform did not issue. Otherwise it was a step that needs a
    payment method, and none is set up.
    """
    if account_missing(auth_headers):
        return ACCOUNT_REQUIRED
    return SERVER_NOT_VERIFIED if free else PAYMENT_REQUIRED


def message(why, may_connect, free=False, server_ip='', scan=True):
    """The sentence shown to the user: what is missing and what to do next.

    may_connect: the user may open the Email Delivery page (an administrator).
    scan: the refused step was a scan, so the user is told none started.
    """
    if why == ACCOUNT_REQUIRED:
        if not may_connect:
            text = '%s, and scans go through one. %s' % (NO_ACCOUNT, ASK_ADMINISTRATOR)
        elif free:
            text = ("%s, and this server's free scans can only be used through one. To use them, %s, "
                    "then start the scan again." % (NO_ACCOUNT, CONNECT))
        else:
            text = ('%s, and scans and payment set-up go through one. To set one up, %s, '
                    'then set up payment on this page.' % (NO_ACCOUNT, CONNECT))
    elif why == SERVER_NOT_VERIFIED:
        server = 'this server (%s)' % server_ip if server_ip else 'this server'
        text = ('The platform did not issue the free-scan key of %s to the connected account. '
                'The free scans belong to the account that owns this VPS' % server)
        if may_connect:
            text += ('; if another account is connected, connect the owner\'s account on the Email Delivery page. '
                     'If it is already connected, the platform may not have been reachable: try again in a few minutes.')
        else:
            text += ': ask the server administrator.'
    else:
        text = 'A paid scan needs a payment method, and none is set up for your panel account. Set up payment on this page first.'
    if scan:
        text += ' ' + NOTHING_STARTED
    return text


def refusal(why, may_connect, free=False, server_ip='', account_url='', scan=True):
    """The JSON body of a refused step: the sentence, its cause, and where the account is connected."""
    body = {'success': False, 'error': message(why, may_connect, free, server_ip, scan), 'reason': why}
    if why in (ACCOUNT_REQUIRED, SERVER_NOT_VERIFIED) and may_connect and account_url:
        body['account_url'] = account_url
    return body


def page_state(auth_headers, may_connect, account_url):
    """What the scanner page says about the account before anything is tried.

    account_missing: no account is connected, so the page asks for one
    first and offers free scans, scans and payment set-up only after it.
    account_setup_url: where an administrator connects one; empty for
    everyone else and when an account is connected.
    """
    missing = account_missing(auth_headers)
    return {
        'account_missing': missing,
        'account_setup_url': account_url if missing and may_connect else '',
    }
