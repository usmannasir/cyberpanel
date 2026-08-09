"""Git webhook shared-secret verification for WebsiteManager."""
import hmac
import secrets
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl


def generate_webhook_secret():
    return secrets.token_urlsafe(32)


def extract_webhook_token(request, payload=None):
    if request is None:
        return ''
    token = ''
    try:
        token = (request.GET.get('token') or request.GET.get('webhook_token') or '').strip()
    except Exception:
        pass
    if not token and request is not None:
        token = (request.headers.get('X-CyberPanel-Webhook-Token') or '').strip()
    if not token and isinstance(payload, dict):
        token = (payload.get('webhookToken') or payload.get('token') or '').strip()
    return token


def verify_webhook_token(provided, stored):
    if not stored or not str(stored).strip():
        return False
    if not provided:
        return False
    return hmac.compare_digest(str(provided).strip(), str(stored).strip())


def append_token_to_webhook_url(url, token):
    if not url or not token:
        return url
    try:
        parts = urlparse(url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query['token'] = token
        new_query = urlencode(query)
        return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))
    except Exception:
        sep = '&' if '?' in url else '?'
        return '%s%stoken=%s' % (url, sep, token)

import json
import os


def _git_conf_dir(master_domain):
    return '/home/cyberpanel/git/%s' % (master_domain)


def find_git_conf_for_folder(master_domain, folder_path):
    conf_dir = _git_conf_dir(master_domain)
    if not os.path.isdir(conf_dir):
        return None
    for name in os.listdir(conf_dir):
        path = os.path.join(conf_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as handle:
                conf = json.loads(handle.read())
            if conf.get('folder') == folder_path:
                return conf
        except Exception:
            continue
    return None


def get_webhook_secret_for_folder(master_domain, folder_path):
    conf = find_git_conf_for_folder(master_domain, folder_path)
    if not conf:
        return ''
    return str(conf.get('webhookSecret') or '').strip()


def verify_git_webhook_for_domain(request, master_domain, folder_path, payload=None):
    stored = get_webhook_secret_for_folder(master_domain, folder_path)
    if not stored:
        return False
    provided = extract_webhook_token(request, payload)
    return verify_webhook_token(provided, stored)
