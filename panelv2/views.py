import json
from django.shortcuts import redirect, HttpResponse
from plogical.httpProc import httpProc
from plogical.acl import ACLManager
from loginSystem.models import Administrator
from websiteFunctions.models import Websites, ChildDomains, Backups, WPSites
from databases.models import Databases
from ftp.models import Users as FTPUsers
from mailServer.models import Domains as EmailDomains, EUsers
from dns.models import Domains as DNSDomains, Records as DNSRecords


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth(request):
    """Return (userID, admin, currentACL) or raise KeyError."""
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)
    admin = Administrator.objects.get(pk=userID)
    return userID, admin, currentACL


def _get_site(site_id, admin, currentACL):
    """Fetch website by pk and verify ownership. Returns website or None."""
    try:
        website = Websites.objects.get(pk=site_id)
    except Websites.DoesNotExist:
        return None
    if ACLManager.checkOwnership(website.domain, admin, currentACL) != 1:
        return None
    return website


def _site_context(website):
    """Build the site_context dict passed to every site-scoped template."""
    return {'id': website.pk, 'domain': website.domain}


def _forbidden():
    return HttpResponse("Unauthorized", status=403)


def _not_found():
    return HttpResponse("Not Found", status=404)


def _login_redirect():
    from loginSystem.views import loadLoginPage
    return redirect(loadLoginPage)


def _json(status, message, **extra):
    data = {'status': status, 'error_message': message}
    data.update(extra)
    return HttpResponse(json.dumps(data), content_type='application/json')


# ---------------------------------------------------------------------------
# Page views
# ---------------------------------------------------------------------------

def site_list(request):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    websites = ACLManager.findWebsiteObjects(currentACL, userID)
    data = {
        'site_context': None,
        'websites': websites,
    }
    proc = httpProc(request, 'panelv2/site_list.html', data, 'listWebsites')
    return proc.render()


def site_dashboard(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    databases_count = Databases.objects.filter(website=website).count()
    ftp_count = FTPUsers.objects.filter(domain=website).count()
    email_domains = EmailDomains.objects.filter(domainOwner=website)
    email_count = EUsers.objects.filter(emailOwner__in=email_domains).count()
    child_count = ChildDomains.objects.filter(master=website).count()
    wp_count = WPSites.objects.filter(owner=website).count()
    backup_count = Backups.objects.filter(website=website).count()

    data = {
        'site_context': _site_context(website),
        'website': website,
        'databases_count': databases_count,
        'ftp_count': ftp_count,
        'email_count': email_count,
        'child_count': child_count,
        'wp_count': wp_count,
        'backup_count': backup_count,
    }
    proc = httpProc(request, 'panelv2/site_dashboard.html', data)
    return proc.render()


def site_databases(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    databases = Databases.objects.filter(website=website)
    data = {
        'site_context': _site_context(website),
        'website': website,
        'databases': databases,
    }
    proc = httpProc(request, 'panelv2/databases.html', data, 'createDatabase')
    return proc.render()


def site_email(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    email_domains = EmailDomains.objects.filter(domainOwner=website)
    emails = EUsers.objects.filter(emailOwner__in=email_domains)
    data = {
        'site_context': _site_context(website),
        'website': website,
        'email_domains': email_domains,
        'emails': emails,
    }
    proc = httpProc(request, 'panelv2/email.html', data, 'createEmail')
    return proc.render()


def site_ftp(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    ftp_accounts = FTPUsers.objects.filter(domain=website)
    data = {
        'site_context': _site_context(website),
        'website': website,
        'ftp_accounts': ftp_accounts,
    }
    proc = httpProc(request, 'panelv2/ftp.html', data, 'createFTPAccount')
    return proc.render()


def site_dns(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    try:
        dns_domain = DNSDomains.objects.get(name=website.domain)
        records = DNSRecords.objects.filter(domainOwner=dns_domain)
    except DNSDomains.DoesNotExist:
        dns_domain = None
        records = []

    data = {
        'site_context': _site_context(website),
        'website': website,
        'dns_domain': dns_domain,
        'records': records,
    }
    proc = httpProc(request, 'panelv2/dns.html', data, 'addDeleteDNSRecords')
    return proc.render()


def site_ssl(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    data = {
        'site_context': _site_context(website),
        'website': website,
    }
    proc = httpProc(request, 'panelv2/ssl.html', data, 'issueSSL')
    return proc.render()


def site_backup(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    backups = Backups.objects.filter(website=website).order_by('-id')
    data = {
        'site_context': _site_context(website),
        'website': website,
        'backups': backups,
    }
    proc = httpProc(request, 'panelv2/backup.html', data, 'createBackup')
    return proc.render()


def site_domains(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    child_domains = ChildDomains.objects.filter(master=website)
    data = {
        'site_context': _site_context(website),
        'website': website,
        'child_domains': child_domains,
    }
    proc = httpProc(request, 'panelv2/domains.html', data, 'listWebsites')
    return proc.render()


def site_files(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    data = {
        'site_context': _site_context(website),
        'website': website,
    }
    proc = httpProc(request, 'panelv2/files.html', data)
    return proc.render()


def site_logs(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    data = {
        'site_context': _site_context(website),
        'website': website,
    }
    proc = httpProc(request, 'panelv2/logs.html', data, 'listWebsites')
    return proc.render()


def site_config(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    data = {
        'site_context': _site_context(website),
        'website': website,
    }
    proc = httpProc(request, 'panelv2/config.html', data, 'listWebsites')
    return proc.render()


def site_apps(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    wp_sites = WPSites.objects.filter(owner=website)
    data = {
        'site_context': _site_context(website),
        'website': website,
        'wp_sites': wp_sites,
    }
    proc = httpProc(request, 'panelv2/apps.html', data, 'listWebsites')
    return proc.render()


def site_security(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _forbidden()

    data = {
        'site_context': _site_context(website),
        'website': website,
    }
    proc = httpProc(request, 'panelv2/security.html', data, 'listWebsites')
    return proc.render()


def server_management(request):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _login_redirect()

    if not currentACL['admin']:
        return _forbidden()

    data = {
        'site_context': None,
    }
    proc = httpProc(request, 'panelv2/server.html', data)
    return proc.render()


# ---------------------------------------------------------------------------
# API endpoints (AJAX)
# ---------------------------------------------------------------------------

def api_databases(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _json(0, 'Not logged in')

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _json(0, 'Unauthorized or site not found')

    if request.method == 'GET':
        dbs = Databases.objects.filter(website=website)
        db_list = [{'name': db.dbName, 'user': db.dbUser, 'id': db.pk} for db in dbs]
        return _json(1, 'None', databases=db_list)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            data['databaseWebsite'] = website.domain
            from plogical.mysqlUtilities import mysqlUtilities
            mysqlUtilities.createDatabase(data['dbName'], data['dbUser'], data['dbPassword'])
            newDB = Databases(website=website, dbName=data['dbName'], dbUser=data['dbUser'])
            newDB.save()
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            db = Databases.objects.get(pk=data['id'], website=website)
            from plogical.mysqlUtilities import mysqlUtilities
            mysqlUtilities.deleteDatabase(db.dbName, db.dbUser)
            db.delete()
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    return _json(0, 'Invalid method')


def api_email(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _json(0, 'Not logged in')

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _json(0, 'Unauthorized or site not found')

    if request.method == 'GET':
        email_domains = EmailDomains.objects.filter(domainOwner=website)
        emails = EUsers.objects.filter(emailOwner__in=email_domains)
        email_list = [{'email': e.email, 'domain': e.emailOwner.domain, 'diskUsage': e.DiskUsage} for e in emails]
        return _json(1, 'None', emails=email_list)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            from plogical.mailUtilities import mailUtilities
            mailUtilities.createEmailAccount(data['domain'], data['username'], data['password'])
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            from plogical.mailUtilities import mailUtilities
            mailUtilities.deleteEmailAccount(data['email'])
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    return _json(0, 'Invalid method')


def api_ftp(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _json(0, 'Not logged in')

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _json(0, 'Unauthorized or site not found')

    if request.method == 'GET':
        accounts = FTPUsers.objects.filter(domain=website)
        ftp_list = [{'id': a.pk, 'user': a.user, 'dir': a.dir, 'quota': a.quotasize, 'status': a.status} for a in accounts]
        return _json(1, 'None', ftp_accounts=ftp_list)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            from plogical.ftpUtilities import ftpUtilities
            ftpUtilities.createFTPAccount(data['ftpDomain'], data['ftpUser'], data['ftpPassword'])
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            ftp_user = FTPUsers.objects.get(pk=data['id'], domain=website)
            from plogical.ftpUtilities import ftpUtilities
            ftpUtilities.deleteFTPAccount(ftp_user.user)
            ftp_user.delete()
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    return _json(0, 'Invalid method')


def api_dns(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _json(0, 'Not logged in')

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _json(0, 'Unauthorized or site not found')

    if request.method == 'GET':
        try:
            dns_domain = DNSDomains.objects.get(name=website.domain)
            records = DNSRecords.objects.filter(domainOwner=dns_domain)
            rec_list = [{'id': r.pk, 'name': r.name, 'type': r.type, 'content': r.content, 'ttl': r.ttl, 'prio': r.prio} for r in records]
            return _json(1, 'None', records=rec_list)
        except DNSDomains.DoesNotExist:
            return _json(1, 'None', records=[])

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            from plogical.dnsUtilities import dnsUtilities
            dnsUtilities.createDNSRecord(website.domain, data['name'], data['type'], data['content'], data.get('prio', 0), data.get('ttl', 3600))
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            record = DNSRecords.objects.get(pk=data['id'])
            record.delete()
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    return _json(0, 'Invalid method')


def api_ssl(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _json(0, 'Not logged in')

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _json(0, 'Unauthorized or site not found')

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action', 'issue')
            if action == 'issue':
                from plogical.sslUtilities import sslUtilities
                sslUtilities.issueSSL(website.domain)
                return _json(1, 'None')
            elif action == 'upload':
                return _json(0, 'Upload SSL not yet implemented in v2 API')
            return _json(0, 'Unknown action')
        except BaseException as msg:
            return _json(0, str(msg))

    return _json(0, 'Invalid method')


def api_backup(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _json(0, 'Not logged in')

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _json(0, 'Unauthorized or site not found')

    if request.method == 'GET':
        backups = Backups.objects.filter(website=website).order_by('-id')
        backup_list = [{'id': b.pk, 'fileName': b.fileName, 'date': b.date, 'size': b.size, 'status': b.status} for b in backups]
        return _json(1, 'None', backups=backup_list)

    elif request.method == 'POST':
        try:
            from plogical.backupUtilities import backupUtilities
            backupUtilities.createBackup(website.domain)
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            backup = Backups.objects.get(pk=data['id'], website=website)
            from plogical.backupUtilities import backupUtilities
            backupUtilities.deleteBackup(backup.fileName)
            backup.delete()
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    return _json(0, 'Invalid method')


def api_logs(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _json(0, 'Not logged in')

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _json(0, 'Unauthorized or site not found')

    if request.method == 'GET':
        import os
        log_type = request.GET.get('type', 'access')
        lines = int(request.GET.get('lines', 50))
        if lines > 1000:
            lines = 1000

        if log_type == 'access':
            log_path = '/home/%s/logs/%s.access_log' % (website.domain, website.domain)
        else:
            log_path = '/home/%s/logs/%s.error_log' % (website.domain, website.domain)

        log_lines = []
        if os.path.exists(log_path):
            try:
                from plogical.processUtilities import ProcessUtilities
                result = ProcessUtilities.outputExecutioner('tail -n %d %s' % (lines, log_path))
                log_lines = result.strip().split('\n') if result.strip() else []
            except:
                pass

        return _json(1, 'None', logs=log_lines, log_type=log_type)

    return _json(0, 'Invalid method')


def api_config(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _json(0, 'Not logged in')

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _json(0, 'Unauthorized or site not found')

    if request.method == 'GET':
        config_type = request.GET.get('type', 'vhost')
        import os
        content = ''
        if config_type == 'vhost':
            vhost_path = '/usr/local/lsws/conf/vhosts/%s/vhconf.conf' % website.domain
            if os.path.exists(vhost_path):
                with open(vhost_path, 'r') as f:
                    content = f.read()
        elif config_type == 'rewrite':
            htaccess_path = '/home/%s/public_html/.htaccess' % website.domain
            if os.path.exists(htaccess_path):
                with open(htaccess_path, 'r') as f:
                    content = f.read()
        return _json(1, 'None', content=content, config_type=config_type)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            config_type = data.get('type', 'rewrite')
            content = data.get('content', '')
            if config_type == 'rewrite':
                htaccess_path = '/home/%s/public_html/.htaccess' % website.domain
                with open(htaccess_path, 'w') as f:
                    f.write(content)
                return _json(1, 'None')
            elif config_type == 'php':
                from plogical.virtualHostUtilities import virtualHostUtilities
                virtualHostUtilities.changePHP(website.domain, data['phpVersion'])
                website.phpSelection = data['phpVersion']
                website.save()
                return _json(1, 'None')
            return _json(0, 'Unknown config type')
        except BaseException as msg:
            return _json(0, str(msg))

    return _json(0, 'Invalid method')


def api_domains(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _json(0, 'Not logged in')

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _json(0, 'Unauthorized or site not found')

    if request.method == 'GET':
        children = ChildDomains.objects.filter(master=website)
        domain_list = [{'id': c.pk, 'domain': c.domain, 'path': c.path, 'ssl': c.ssl, 'php': c.phpSelection, 'isAlias': c.alais} for c in children]
        return _json(1, 'None', domains=domain_list)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            from plogical.childDomain import childDomain
            childDomain.createChildDomain(website.domain, data['domain'], data.get('path', ''), data.get('php', website.phpSelection), data.get('ssl', 0), data.get('isAlias', 0))
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            child = ChildDomains.objects.get(pk=data['id'], master=website)
            from plogical.childDomain import childDomain
            childDomain.deleteChildDomain(child.domain)
            return _json(1, 'None')
        except BaseException as msg:
            return _json(0, str(msg))

    return _json(0, 'Invalid method')


def api_security(request, site_id):
    try:
        userID, admin, currentACL = _auth(request)
    except KeyError:
        return _json(0, 'Not logged in')

    website = _get_site(site_id, admin, currentACL)
    if not website:
        return _json(0, 'Unauthorized or site not found')

    if request.method == 'GET':
        try:
            config = json.loads(website.config) if website.config else {}
        except:
            config = {}
        open_basedir = config.get('openBasedir', 1)
        return _json(1, 'None', openBasedir=open_basedir)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action', '')
            if action == 'toggleOpenBasedir':
                from plogical.virtualHostUtilities import virtualHostUtilities
                virtualHostUtilities.changeOpenBasedir(website.domain, data.get('value', 1))
                return _json(1, 'None')
            return _json(0, 'Unknown action')
        except BaseException as msg:
            return _json(0, str(msg))

    return _json(0, 'Invalid method')
