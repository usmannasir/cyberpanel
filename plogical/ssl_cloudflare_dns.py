# -*- coding: utf-8 -*-
"""Let's Encrypt via Cloudflare DNS (dns_cf) for proxied domains."""
import os
import shlex
import subprocess

from plogical import CyberCPLogFileWriter as logging
from plogical.acl import ACLManager
from plogical.processUtilities import ProcessUtilities


def _sync_panel_cf_keys_to_acme():
    """Copy CyberPanel DNS API settings into acme.sh account.conf when present."""
    try:
        from plogical.dnsUtilities import DNS
        from loginSystem.models import Administrator

        for admin in Administrator.objects.filter(pk__gte=1)[:20]:
            cf_file = '%s%s' % (DNS.CFPath, admin.userName)
            if not os.path.isfile(cf_file):
                continue
            with open(cf_file, 'r') as handle:
                lines = [ln.strip() for ln in handle.readlines() if ln.strip()]
            if len(lines) < 2:
                continue
            email, token = lines[0], lines[1]
            if len(token) > 3:
                DNS.ConfigureCloudflareInAcme(token, email)
                return True
    except BaseException as exc:
        logging.writeToFile('sync_panel_cf_keys_to_acme: %s' % str(exc))
    return False


def find_domain_in_cloudflare(virtual_host_name):
    """Return (1, None) if the zone is active in Cloudflare and API keys work."""
    try:
        import tldextract
        from plogical.cloudflareClient import get_cloudflare_client

        _sync_panel_cf_keys_to_acme()
        ret_status, cf_key, cf_email = ACLManager.FetchCloudFlareAPIKeyFromAcme()
        if not ret_status:
            return 0, 'Cloudflare API keys are not configured in acme.sh (DNS API Settings).'

        extract = tldextract.TLDExtract(cache_dir=None)(virtual_host_name)
        top_level = '%s.%s' % (extract.domain, extract.suffix)
        cf = get_cloudflare_client(cf_email, cf_key)
        zones = cf.zones.get(params={'name': top_level, 'per_page': 50})
        for zone in zones or []:
            if zone.get('name') == top_level and zone.get('status') == 'active':
                return 1, None
        return 0, 'Zone not found or not active in Cloudflare'
    except BaseException as exc:
        return 0, str(exc)


def _acme_cloudflare_env():
    """Build env with CF_Key/CF_Email for acme.sh dns_cf (reads account.conf too)."""
    import os as _os
    env = dict(_os.environ)
    try:
        ret_status, cf_key, cf_email = ACLManager.FetchCloudFlareAPIKeyFromAcme()
        if ret_status:
            env['CF_Key'] = cf_key
            env['CF_Email'] = cf_email
    except BaseException:
        pass
    return env


def issue_le_via_cloudflare_dns(virtual_host_name, admin_email, is_hostname=False):
    """
    Issue or renew Let's Encrypt using acme.sh --dns dns_cf (works behind orange cloud).
    Returns True on success.
    """
    from plogical.sslUtilities import sslUtilities

    acme_path = '/root/.acme.sh/acme.sh'
    if not os.path.isfile(acme_path):
        logging.writeToFile('acme.sh not found for dns_cf issuance')
        return False

    _sync_panel_cf_keys_to_acme()
    cf_ok, cf_msg = find_domain_in_cloudflare(virtual_host_name)
    if not cf_ok:
        logging.writeToFile(
            'Cloudflare DNS issuance skipped for %s: %s' % (virtual_host_name, cf_msg))
        return False

    live_dir = '/etc/letsencrypt/live/' + virtual_host_name
    if not os.path.isdir(live_dir):
        subprocess.call(shlex.split('mkdir -p ' + live_dir))

    domain_list = ' -d ' + shlex.quote(virtual_host_name)
    if not is_hostname and sslUtilities.checkDNSRecords('www.%s' % virtual_host_name):
        domain_list += ' -d ' + shlex.quote('www.' + virtual_host_name)

    command = (
        '%s --issue %s --dns dns_cf --dnssleep 30 --force --server letsencrypt -k ec-256'
        ' --cert-file %s/cert.pem --key-file %s/privkey.pem --fullchain-file %s/fullchain.pem'
        % (acme_path, domain_list, live_dir, live_dir, live_dir)
    )
    logging.writeToFile('Cloudflare DNS SSL command: %s' % command, 0)

    acme_env = _acme_cloudflare_env()
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, shell=True, env=acme_env)
    except TypeError:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, shell=True, env=acme_env)

    if result.returncode != 0:
        err = (result.stderr or result.stdout or '').strip()
        logging.writeToFile(
            'dns_cf issue failed for %s: %s' % (virtual_host_name, err[:2500]))
        return False

    install_command = (
        '%s --install-cert -d %s --ecc'
        ' --cert-file %s/cert.pem --key-file %s/privkey.pem --fullchain-file %s/fullchain.pem'
        % (acme_path, shlex.quote(virtual_host_name), live_dir, live_dir, live_dir)
    )
    try:
        install_result = subprocess.run(
            install_command, capture_output=True, text=True, shell=True, env=acme_env)
    except TypeError:
        install_result = subprocess.run(
            install_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, shell=True, env=acme_env)

    if install_result.returncode != 0:
        logging.writeToFile(
            'dns_cf install-cert failed for %s' % virtual_host_name)
        return False

    try:
        os.chmod(live_dir + '/fullchain.pem', 0o644)
    except BaseException:
        pass

    logging.writeToFile(
        'Successfully issued SSL via Cloudflare DNS for %s' % virtual_host_name, 0)
    return True
