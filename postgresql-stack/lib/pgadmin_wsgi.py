"""Gunicorn entry for pgAdmin with /usr/local site-package filter.

Also provides a small, self-contained Single-Sign-On (SSO) launcher mounted at
``/sso``. The CyberPanel "Open pgAdmin" tile points at ``/sso/?key=<token>``.
When the token matches the per-install secret, the launcher logs in to pgAdmin
server-side using the randomly generated pgAdmin credentials and hands the
browser an authenticated session cookie. The user never sees or types the
username/password.

The login is performed over the loopback HTTP interface (the same path a real
browser would take), which yields a session that is valid across all gunicorn
workers. In-process WSGI calls are intentionally avoided because the resulting
session is only cached in the worker that created it.

Security model:
  * The launcher only acts when the request carries the correct per-install
    token (constant-time compared). Without it the response is 403.
  * pgAdmin keeps its normal login page as a fallback (defense in depth): a
    direct visit without the token still requires the password.
  * The secret file (token + credentials) is readable only by the pgAdmin
    service user (apache), chmod 600.
"""
import http.client
import json
import os
import re
import sys

sys.path.insert(0, "/usr/pgadmin4/web")
sys.path = [p for p in sys.path if "/usr/local/" not in p]

from pgAdmin4 import app  # noqa: E402


def _install_pass_enc_key_hook():
    """Store the login password in session so saved server passwords decrypt on any worker.

    pgAdmin's internal login only sets keyManager in-process. With multiple
    gunicorn workers that breaks saved-password connect. OAuth/Kerberos auth sets
    session['pass_enc_key']; mirror that for password login (including SSO).
    """
    try:
        import config
        from flask import request, session
        from flask_login.signals import user_logged_in

        @user_logged_in.connect_via(app)
        def _store_pass_enc_key(sender, user):
            if not config.SERVER_MODE or config.MASTER_PASSWORD_REQUIRED:
                return
            pwd = request.form.get("password")
            if pwd:
                session["pass_enc_key"] = pwd
                session.force_write = True
    except Exception:
        pass


_install_pass_enc_key_hook()

SECRET_FILE = os.environ.get("PGSTACK_SSO_SECRET", "/var/lib/pgadmin/.pgstack-sso.json")
LOGIN_PAGE_PATH = "/login"
LOGIN_API_PATH = "/authenticate/login"
POST_LOGIN_PATH = "/browser/"
UTILS_JS_PATH = "/browser/js/utils.js"
CSRF_RE = re.compile(rb'"csrfToken":\s*"([^"]+)"')
CSRF_UTILS_RE = re.compile(r"pgAdmin\['csrf_token'\]\s*=\s*'([^']+)'")
CSRF_HEADER_RE = re.compile(r"pgAdmin\['csrf_token_header'\]\s*=\s*'([^']+)'")
SESSION_COOKIE_RE = re.compile(r"(pga4_session=[^;]+)")
HTTP_TIMEOUT = 15


def _load_secret():
    try:
        with open(SECRET_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("token") and data.get("email") and data.get("password"):
            return data
    except Exception:
        return None
    return None


def _const_eq(a, b):
    try:
        import hmac

        return hmac.compare_digest(str(a), str(b))
    except Exception:
        return False


def _backend(secret):
    host = (secret or {}).get("backend_host") or "127.0.0.1"
    port = int((secret or {}).get("backend_port") or 5050)
    return host, port


def _request(backend, method, path, host, headers=None, body=None):
    """Perform a loopback HTTP request to the pgAdmin backend."""
    conn = http.client.HTTPConnection(backend[0], backend[1], timeout=HTTP_TIMEOUT)
    try:
        req_headers = {"Host": host}
        if headers:
            req_headers.update(headers)
        conn.request(method, path, body=body, headers=req_headers)
        resp = conn.getresponse()
        data = resp.read()
        set_cookies = resp.getheader("Set-Cookie")
        # getheader collapses duplicates; use get_all-like access via msg
        try:
            all_cookies = resp.msg.get_all("Set-Cookie") or []
        except Exception:
            all_cookies = [set_cookies] if set_cookies else []
        return resp.status, all_cookies, resp.getheader("Location"), data
    finally:
        conn.close()


def _session_cookie(set_cookies):
    """Return (full_set_cookie_string, 'pga4_session=value') or (None, None)."""
    for cookie in set_cookies or []:
        if not cookie:
            continue
        m = SESSION_COOKIE_RE.search(cookie)
        if m:
            return cookie, m.group(1)
    return None, None


def _browser_referer(host):
    scheme = "https"
    hostname = (host or "localhost").split(":")[0]
    return "{0}://{1}/browser/".format(scheme, hostname)


def _fetch_browser_csrf(backend, host, session_kv, fwd):
    """Load authenticated /browser/js/utils.js and parse CSRF token + header."""
    headers = dict(fwd)
    headers["Cookie"] = session_kv
    status, _, _, body = _request(backend, "GET", UTILS_JS_PATH, host, headers=headers)
    if status != 200:
        return None, None
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        return None, None
    csrf_m = CSRF_UTILS_RE.search(text)
    hdr_m = CSRF_HEADER_RE.search(text)
    if not csrf_m or not hdr_m:
        return None, None
    return csrf_m.group(1), hdr_m.group(1)


def _connect_registered_server(backend, host, session_kv, fwd, secret):
    """Pre-connect the stack-registered PostgreSQL server after SSO login."""
    try:
        gid = int(secret.get("server_gid") or 0)
        sid = int(secret.get("server_sid") or 0)
    except Exception:
        return False
    if gid <= 0 or sid <= 0:
        return False

    csrf, csrf_header = _fetch_browser_csrf(backend, host, session_kv, fwd)
    if not csrf or not csrf_header:
        return False

    path = "/browser/server/connect/{0}/{1}".format(gid, sid)
    post_headers = dict(fwd)
    post_headers.update(
        {
            "Cookie": session_kv,
            csrf_header: csrf,
            "Referer": _browser_referer(host),
            "Content-Type": "application/json",
            "Content-Length": "2",
        }
    )
    status, _, _, body = _request(
        backend, "POST", path, host, headers=post_headers, body=b"{}"
    )
    if status != 200:
        return False
    try:
        payload = json.loads(body.decode("utf-8", errors="replace") or "{}")
    except Exception:
        return False
    return bool(payload.get("success"))


def _redirect(start_response, location, set_cookie=None):
    body = (
        b"<!doctype html><html><head><meta charset='utf-8'>"
        b"<title>Opening pgAdmin...</title></head><body>"
        b"<p>Opening pgAdmin... If you are not redirected, "
        b"<a href='" + location.encode("utf-8") + b"'>click here</a>.</p>"
        b"</body></html>"
    )
    headers = [
        ("Location", location),
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("Referrer-Policy", "no-referrer"),
        ("X-Content-Type-Options", "nosniff"),
    ]
    if set_cookie:
        headers.append(("Set-Cookie", set_cookie))
    start_response("302 Found", headers)
    return [body]


def _forbidden(start_response):
    body = b"403 Forbidden"
    start_response(
        "403 Forbidden",
        [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("Referrer-Policy", "no-referrer"),
        ],
    )
    return [body]


def _parse_query_key(query_string):
    try:
        from urllib.parse import parse_qs

        values = parse_qs(query_string or "")
        key = values.get("key", [""])
        return key[0] if key else ""
    except Exception:
        return ""


def _forwarded_headers(environ):
    """Headers that make the loopback login look like the real client.

    pgAdmin's Paranoid extension binds the session to
    sha256(X-Forwarded-For-first-IP + '|' + User-Agent). The loopback login must
    present the same User-Agent and client IP that the browser will send on its
    subsequent requests (via LiteSpeed), otherwise pgAdmin invalidates the
    session and bounces the user back to the login page.
    """
    headers = {}
    ua = environ.get("HTTP_USER_AGENT")
    if ua:
        headers["User-Agent"] = ua
    xff = environ.get("HTTP_X_FORWARDED_FOR") or environ.get("REMOTE_ADDR")
    if xff:
        headers["X-Forwarded-For"] = xff
    headers["X-Forwarded-Proto"] = environ.get("HTTP_X_FORWARDED_PROTO") or "https"
    return headers


def _perform_sso(environ, start_response):
    secret = _load_secret()
    host = environ.get("HTTP_HOST", "localhost")
    provided = _parse_query_key(environ.get("QUERY_STRING", ""))

    if not secret or not provided or not _const_eq(secret["token"], provided):
        return _forbidden(start_response)

    backend = _backend(secret)
    fwd = _forwarded_headers(environ)
    try:
        # Step 1: fetch login page for CSRF token + initial session cookie.
        get_headers = dict(fwd)
        _, sc1, _, body1 = _request(backend, "GET", LOGIN_PAGE_PATH, host, headers=get_headers)
        csrf_match = CSRF_RE.search(body1)
        cookie_full, session_kv = _session_cookie(sc1)
        if not csrf_match or not session_kv:
            return _redirect(start_response, LOGIN_PAGE_PATH)
        csrf = csrf_match.group(1).decode("utf-8")

        # Step 2: authenticate with credentials.
        from urllib.parse import urlencode

        form = urlencode(
            {
                "email": secret["email"],
                "password": secret["password"],
                "csrf_token": csrf,
            }
        ).encode("utf-8")
        post_headers = dict(fwd)
        post_headers.update(
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": session_kv,
                "X-CSRFToken": csrf,
                "Content-Length": str(len(form)),
            }
        )
        status2, sc2, _, _ = _request(
            backend,
            "POST",
            LOGIN_API_PATH,
            host,
            headers=post_headers,
            body=form,
        )
        if status2 not in (200, 302):
            return _redirect(start_response, LOGIN_PAGE_PATH)

        auth_cookie, auth_kv = _session_cookie(sc2)
        relay_cookie = auth_cookie or cookie_full
        session_kv = auth_kv or session_kv
        if session_kv:
            _connect_registered_server(backend, host, session_kv, fwd, secret)
        return _redirect(start_response, POST_LOGIN_PATH, set_cookie=relay_cookie)
    except Exception:
        # Never break access; fall back to the standard login page.
        return _redirect(start_response, LOGIN_PAGE_PATH)


class SSOMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path.rstrip("/") == "/sso":
            return _perform_sso(environ, start_response)
        return self.wsgi_app(environ, start_response)


application = SSOMiddleware(app)
