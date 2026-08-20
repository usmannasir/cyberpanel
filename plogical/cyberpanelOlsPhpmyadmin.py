# -*- coding: utf-8 -*-
"""
Ensure CyberPanel OpenLiteSpeed vhost executes /phpmyadmin/ and /snappymail/
via lsphp. Without explicit OLS contexts + scripthandler, Django proxy serves
.php as static downloads. Also keeps public/snappymail as a real tree under
CyberCP vhRoot (restrained=1 rejects symlinks into /usr/local/lscp).
"""
from __future__ import print_function

import os
import re
import subprocess

from plogical.cyberpanelOlsSnappymail import SNAPPY_PUBLIC, ensure_snappymail_public_tree

LSWS_ROOT = '/usr/local/lsws'
VHOST_DIR = os.path.join(LSWS_ROOT, 'conf', 'vhosts', 'CyberPanel')
VHOST_CONF = os.path.join(VHOST_DIR, 'vhost.conf')
VHOST_TXT = os.path.join(VHOST_DIR, 'vhost.conf.txt')
HTTPD_CONFIG = os.path.join(LSWS_ROOT, 'conf', 'httpd_config.conf')
BIND_CONF = '/usr/local/lscp/conf/bind.conf'
PMA_SIGNIN = '/usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php'
RAW_PHP_SIZE = 5800  # executed responses are < 500 bytes


def _log(msg):
    try:
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
        CyberCPLogFileWriter.writeToFile('[cyberpanelOlsPhpmyadmin] ' + str(msg))
    except Exception:
        pass
    print('[cyberpanelOlsPhpmyadmin] ' + str(msg))

def detect_lsphp_version():
    for ver in ('85', '84', '83', '82', '81', '80'):
        path = '/usr/local/lsws/lsphp%s/bin/lsphp' % ver
        if os.path.isfile(path):
            return ver
    return '83'


def build_vhost_conf(php_version=None):
    php_version = php_version or detect_lsphp_version()
    lsphp_path = '/usr/local/lsws/lsphp%s/bin/lsphp' % php_version
    log_format = '%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-Agent}i"'
    lines = [
        'docRoot                   $VH_ROOT',
        'vhDomain                  $VH_NAME',
        'vhAliases                 *',
        'adminEmails               root@localhost',
        'enableGzip                1',
        'enableIpGeo               1',
        '',
        'errorlog $VH_ROOT/logs/error.log {',
        '  useServer               0',
        '  logLevel                DEBUG',
        '  rollingSize             10M',
        '}',
        '',
        'accesslog $VH_ROOT/logs/access.log {',
        '  useServer               0',
        '  logFormat               "' + log_format + '"',
        '  logHeaders              5',
        '  rollingSize             10M',
        '  keepDays                30',
        '  compressArchive         1',
        '}',
        '',
        'scripthandler  {',
        '  add                     lsapi:cyberpanelphp php',
        '}',
        '',
        'extprocessor cyberpanelphp {',
        '  type                    lsapi',
        '  address                 UDS://tmp/lshttpd/cyberpanelphp.sock',
        '  maxConns                10',
        '  env                     LSAPI_CHILDREN=10',
        '  initTimeout             60',
        '  retryTimeout            0',
        '  persistConn             1',
        '  respBuffer              0',
        '  autoStart               2',
        '  path                    ' + lsphp_path,
        '  extUser                 lscpd',
        '  extGroup                lscpd',
        '  memSoftLimit            2047M',
        '  memHardLimit            2047M',
        '  procSoftLimit           400',
        '  procHardLimit           500',
        '}',
        '',
        'extprocessor cyberpanel {',
        '  type                    proxy',
        # HTTPS: lscpd on 5003 redirects plain HTTP to HTTPS (OLS proxy loop if http://).
        '  address                 https://127.0.0.1:5003',
        '  maxConns                100',
        '  pcKeepAliveTimeout      60',
        '  initTimeout             60',
        '  retryTimeout            0',
        '  respBuffer              0',
        '}',
        '',
        'context /phpmyadmin/ {',
        '  location                /usr/local/CyberCP/public/phpmyadmin/',
        '  allowBrowse             1',
        '  indexFiles              index.php',
        '  addDefaultCharset       off',
        '  scripthandler  {',
        '    add                     lsapi:cyberpanelphp php',
        '  }',
        '}',
        '',
        'context /snappymail/ {',
        '  location                /usr/local/CyberCP/public/snappymail/',
        '  allowBrowse             1',
        '  indexFiles              index.php',
        '  addDefaultCharset       off',
        '  scripthandler  {',
        '    add                     lsapi:cyberpanelphp php',
        '  }',
        '}',
        '',
        'context /static/ {',
        '  type                    null',
        '  location                /usr/local/CyberCP/static/',
        '  allowBrowse             1',
        '}',
        '',
        'context / {',
        '  type                    proxy',
        '  handler                 cyberpanel',
        '  addDefaultCharset       off',
        '}',
        '',
    ]
    return '\n'.join(lines)


def get_panel_port():
    """Public panel port for the OLS listener.

    bind.conf may be *:8090 (legacy public bind) or 127.0.0.1:5003 (lscpd
    WSGI backend). Only *:PORT means the public HTTPS port. A loopback bind
    is the backend; OLS stays on 8090.
    """
    try:
        if os.path.isfile(BIND_CONF):
            line = open(BIND_CONF, 'r').read().strip()
            if line.startswith('*:') and ':' in line:
                port = line.split(':', 1)[1].strip().split()[0]
                if port.isdigit():
                    return port
    except Exception:
        pass
    return '8090'


def _write_vhost_files(content):
    os.makedirs(VHOST_DIR, exist_ok=True)
    os.makedirs(os.path.join(VHOST_DIR, 'logs'), exist_ok=True)
    for path in (VHOST_CONF, VHOST_TXT):
        with open(path, 'w') as f:
            f.write(content)
    _log('Wrote %s and %s' % (VHOST_CONF, VHOST_TXT))


def _httpd_has_cyberpanel_vhost(lines):
    return any('virtualHost CyberPanel' in line for line in lines)


def _httpd_has_cyberpanel_listener(lines):
    return any(re.match(r'\s*listener\s+CyberPanel\s*\{', line) for line in lines)


def ensure_httpd_cyberpanel_blocks():
    if not os.path.isfile(HTTPD_CONFIG):
        _log('WARNING: %s missing; skipping httpd_config patch' % HTTPD_CONFIG)
        return True
    with open(HTTPD_CONFIG, 'r') as f:
        lines = f.readlines()
    changed = False
    if not _httpd_has_cyberpanel_vhost(lines):
        lines.append("""
virtualHost CyberPanel {
  vhRoot                  /usr/local/CyberCP/
  configFile              $SERVER_ROOT/conf/vhosts/CyberPanel/vhost.conf
  allowSymbolLink         1
  enableScript            1
  restrained              1
}
""")
        changed = True
    if not _httpd_has_cyberpanel_listener(lines):
        port = get_panel_port()
        lines.append("""
listener CyberPanel {
  address                 *:%s
  secure                  1
  keyFile                 /usr/local/lsws/admin/conf/webadmin.key
  certFile                /usr/local/lsws/admin/conf/webadmin.crt
  map                     CyberPanel *
}
""" % port)
        changed = True
    if changed:
        backup = HTTPD_CONFIG + '.bak-phpmyadmin-ols'
        try:
            import shutil
            shutil.copy2(HTTPD_CONFIG, backup)
        except Exception:
            pass
        with open(HTTPD_CONFIG, 'w') as f:
            f.writelines(lines)
        _log('Patched %s with CyberPanel vhost/listener' % HTTPD_CONFIG)
    return True


def _cyberpanelphp_ext_block(php_ver=None):
    php_ver = php_ver or detect_lsphp_version()
    return """
extprocessor cyberpanelphp {
  type                    lsapi
  address                 UDS://tmp/lshttpd/cyberpanelphp.sock
  maxConns                10
  env                     LSAPI_CHILDREN=10
  initTimeout             60
  retryTimeout            0
  persistConn             1
  respBuffer              0
  autoStart               2
  path                    /usr/local/lsws/lsphp%s/bin/lsphp
  extUser                 lscpd
  extGroup                lscpd
  memSoftLimit            2047M
  memHardLimit            2047M
  procSoftLimit           400
  procHardLimit           500
}
""" % php_ver


def _php_app_context(path_prefix, location):
    return """
context %s {
  location                %s
  allowBrowse             1
  indexFiles              index.php
  addDefaultCharset       off
  scripthandler  {
    add                     lsapi:cyberpanelphp php
  }
}
""" % (path_prefix, location)



def patch_hostname_vhost_php_contexts(vhost_path):
    """Serve /phpmyadmin/ and /snappymail/ with local lsphp on hostname panel proxies."""
    if not os.path.isfile(vhost_path):
        return False
    try:
        content = open(vhost_path, 'r').read()
    except Exception:
        return False

    # Skip non-panel vhosts (site docroots) that never proxy the panel.
    if 'extprocessor panelbackend' not in content and 'panel_proxy' not in content:
        if 'context /phpmyadmin/' not in content and 'context /snappymail/' not in content:
            return False

    changed = False
    php_ver = detect_lsphp_version()
    ext_block = _cyberpanelphp_ext_block(php_ver)

    if 'extprocessor cyberpanelphp' not in content:
        if 'extprocessor panelbackend' in content:
            content = content.replace('extprocessor panelbackend', ext_block + '\nextprocessor panelbackend', 1)
        elif 'context /phpmyadmin/' in content:
            content = content.replace('context /phpmyadmin/', ext_block + '\ncontext /phpmyadmin/', 1)
        else:
            content = ext_block + '\n' + content
        changed = True

    if 'context /snappymail/' not in content or 'context /phpmyadmin/' not in content:
        insert = ''
        if 'context /snappymail/' not in content:
            insert += _php_app_context('/snappymail/', SNAPPY_PUBLIC + '/')
        if 'context /phpmyadmin/' not in content:
            insert += _php_app_context('/phpmyadmin/', '/usr/local/CyberCP/public/phpmyadmin/')
        if 'extprocessor panelbackend' in content:
            content = content.replace('extprocessor panelbackend', insert + '\nextprocessor panelbackend', 1)
        elif 'context /.well-known/acme-challenge' in content:
            content = content.replace(
                'context /.well-known/acme-challenge',
                insert + '\ncontext /.well-known/acme-challenge',
                1,
            )
        else:
            content = insert + '\n' + content
        changed = True
    else:
        for pattern in (
            r'(context /phpmyadmin/ \{[^}]*?addDefaultCharset\s+off)\s*\n(\})',
            r'(context /snappymail/ \{[^}]*?addDefaultCharset\s+off)\s*\n(\})',
        ):
            new_content, n = re.subn(
                pattern,
                r'\1\n  scripthandler  {\n    add                     lsapi:cyberpanelphp php\n  }\n\2',
                content,
                count=1,
                flags=re.DOTALL,
            )
            if n:
                content = new_content
                changed = True

    if not changed and 'lsapi:cyberpanelphp php' in content:
        return True
    if not changed:
        return False

    with open(vhost_path, 'w') as f:
        f.write(content)
    _log('Patched hostname vhost PHP contexts: %s' % vhost_path)
    return True


def patch_all_hostname_vhosts():
    vhosts_root = os.path.join(LSWS_ROOT, 'conf', 'vhosts')
    if not os.path.isdir(vhosts_root):
        return
    for name in os.listdir(vhosts_root):
        if name == 'CyberPanel' or name == 'Example':
            continue
        vpath = os.path.join(vhosts_root, name, 'vhost.conf')
        patch_hostname_vhost_php_contexts(vpath)


def reload_lsws(restart=False):
    ctrl = os.path.join(LSWS_ROOT, 'bin', 'lswsctrl')
    if not os.path.isfile(ctrl):
        _log('WARNING: lswsctrl not found')
        return False
    action = 'restart' if restart else 'reload'
    try:
        r = subprocess.run([ctrl, action], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            _log('%s failed: %s' % (action, (r.stderr or r.stdout or '').strip()))
            return False
        return True
    except Exception as e:
        _log('LiteSpeed %s error: %s' % (action, e))
        return False


def verify_phpmyadmin_ols(port=None):
    port = port or get_panel_port()
    url = 'https://127.0.0.1:%s/phpmyadmin/phpmyadminsignin.php' % port
    try:
        r = subprocess.run(
            ['curl', '-sk', '-X', 'POST', url, '-d', 'username=t&token=t', '-o', '/tmp/cp_pma_verify.out', '-w', '%{size_download}'],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return False, 'curl failed'
        size = int((r.stdout or '0').strip() or '0')
        if size >= RAW_PHP_SIZE:
            return False, 'POST returned raw PHP (%s bytes)' % size
        hdr = subprocess.run(['curl', '-skI', url], capture_output=True, text=True, timeout=15)
        if 'x-powered-by: PHP' not in (hdr.stdout or '').lower():
            return False, 'missing x-powered-by PHP header'
        return True, 'OK (POST %s bytes)' % size
    except Exception as e:
        return False, str(e)


def verify_snappymail_ols(port=None):
    port = port or get_panel_port()
    url = 'https://127.0.0.1:%s/snappymail/index.php' % port
    try:
        r = subprocess.run(
            ['curl', '-sk', '-o', '/tmp/cp_snappy_verify.out', '-w', '%{http_code}', url],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return False, 'curl failed'
        code = (r.stdout or '').strip()
        body = ''
        try:
            body = open('/tmp/cp_snappy_verify.out', 'r', errors='replace').read(400)
        except Exception:
            pass
        if code != '200':
            return False, 'HTTP %s' % code
        low = body.lower()
        if 'not found' in low and 'snappymail' not in low and 'rainloop' not in low:
            return False, 'Django/OLS 404 body'
        if '<html' not in low and 'doctype' not in low:
            return False, 'unexpected body'
        return True, 'OK (HTTP %s)' % code
    except Exception as e:
        return False, str(e)


def ensure_cyberpanel_phpmyadmin_ols(reload=True, restart=False, verify=True):
    """Idempotent: write OLS vhost, patch httpd_config, reload LiteSpeed, optional self-test."""
    try:
        ensure_snappymail_public_tree()
        content = build_vhost_conf()
        _write_vhost_files(content)
        ensure_httpd_cyberpanel_blocks()
        patch_all_hostname_vhosts()
        if reload:
            reload_lsws(restart=restart)
        if verify:
            ok, detail = verify_phpmyadmin_ols()
            if ok:
                _log('Verified phpMyAdmin OLS: ' + detail)
            else:
                _log('WARNING: phpMyAdmin OLS verify failed: ' + detail)
                if not restart:
                    reload_lsws(restart=True)
                    ok2, detail2 = verify_phpmyadmin_ols()
                    _log('After restart: ' + (detail2 if ok2 else 'STILL FAILING: ' + detail2))
            sok, sdetail = verify_snappymail_ols()
            if sok:
                _log('Verified SnappyMail OLS: ' + sdetail)
            else:
                _log('WARNING: SnappyMail OLS verify failed: ' + sdetail)
        return True
    except Exception as e:
        _log('ERROR: ' + str(e))
        return False


if __name__ == '__main__':
    import sys
    restart = '--restart' in sys.argv
    ok = ensure_cyberpanel_phpmyadmin_ols(restart=restart)
    sys.exit(0 if ok else 1)
