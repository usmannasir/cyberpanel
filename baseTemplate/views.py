# -*- coding: utf-8 -*-
from random import randint

from django.shortcuts import render, redirect
from django.http import HttpResponse
from plogical.getSystemInformation import SystemInformation
import json
from loginSystem.views import loadLoginPage
from .models import version, UserNotificationPreferences
import requests
import subprocess
import shlex
import os
import plogical.CyberCPLogFileWriter as logging
from plogical.acl import ACLManager
from manageServices.models import PDNSStatus
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from plogical.processUtilities import ProcessUtilities
from plogical.firewallUtilities import FirewallUtilities
from plogical.httpProc import httpProc
from websiteFunctions.models import Websites, WPSites
from databases.models import Databases
from mailServer.models import EUsers
from ftp.models import Users as FTPUsers
from loginSystem.models import Administrator
from packages.models import Package
from django.views.decorators.http import require_GET, require_POST
import pwd
import re

# Create your views here.

VERSION = '2.5.5'
BUILD = 1


def _version_compare(a, b):
    """Return 1 if a > b, -1 if a < b, 0 if equal."""
    def parse(v):
        parts = []
        for p in str(v).split('.'):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return parts
    pa, pb = parse(a), parse(b)
    for i in range(max(len(pa), len(pb))):
        va = pa[i] if i < len(pa) else 0
        vb = pb[i] if i < len(pb) else 0
        if va > vb:
            return 1
        if va < vb:
            return -1
    return 0


def _parse_github_origin(remote_out):
    """Return (owner, repo) or (None, None) if unparseable."""
    if not remote_out:
        return None, None
    m = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$', remote_out.strip())
    if not m:
        return None, None
    owner, repo = m.group(1), m.group(2).rstrip('.git')
    return owner, repo


def _github_branch_tip_sha(owner, repo, branch_ref):
    """First commit SHA on branch via GitHub API, or empty string on failure."""
    try:
        u = 'https://api.github.com/repos/%s/%s/commits?sha=%s' % (owner, repo, branch_ref)
        r = requests.get(u, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            return ''
        sha = data[0].get('sha', '') or ''
        return sha
    except (requests.RequestException, IndexError, KeyError, TypeError) as e:
        logging.CyberCPLogFileWriter.writeToFile(
            '[versionManagment] GitHub API %s/%s @%s failed: %s' % (owner, repo, branch_ref, str(e)))
        return ''


@ensure_csrf_cookie
def renderBase(request):
    template = 'baseTemplate/homePage.html'
    cpuRamDisk = SystemInformation.cpuRamDisk()
    finaData = {'ramUsage': cpuRamDisk['ramUsage'], 'cpuUsage': cpuRamDisk['cpuUsage'],
                'diskUsage': cpuRamDisk['diskUsage']}
    proc = httpProc(request, template, finaData)
    return proc.render()


@ensure_csrf_cookie
def versionManagement(request):
    """Legacy entrypoint; same UI as versionManagment (URLs use versionManagment)."""
    return versionManagment(request)


@ensure_csrf_cookie
def upgrade_cyberpanel(request):
    if request.method == 'POST':
        try:
            upgrade_command = 'sh <(curl https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh || wget -O - https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh)'
            result = subprocess.run(upgrade_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    universal_newlines=True)

            if result.returncode == 0:
                response_data = {'success': True, 'message': 'CyberPanel upgrade completed successfully.'}
            else:
                response_data = {'success': False,
                                 'message': 'CyberPanel upgrade failed. Error output: ' + result.stderr}
        except Exception as e:
            response_data = {'success': False, 'message': 'An error occurred during the upgrade: ' + str(e)}


def getAdminStatus(request):
    try:
        val = request.session['userID']
        currentACL = ACLManager.loadedACL(val)

        if os.path.exists('/home/cyberpanel/postfix'):
            currentACL['emailAsWhole'] = 1
        else:
            currentACL['emailAsWhole'] = 0

        if os.path.exists('/home/cyberpanel/pureftpd'):
            currentACL['ftpAsWhole'] = 1
        else:
            currentACL['ftpAsWhole'] = 0

        try:
            pdns = PDNSStatus.objects.get(pk=1)
            currentACL['dnsAsWhole'] = pdns.serverStatus
        except:
            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                pdnsPath = '/etc/powerdns'
            else:
                pdnsPath = '/etc/pdns'

            if os.path.exists(pdnsPath):
                PDNSStatus(serverStatus=1).save()
                currentACL['dnsAsWhole'] = 1
            else:
                currentACL['dnsAsWhole'] = 0

        json_data = json.dumps(currentACL)
        return HttpResponse(json_data)
    except KeyError:
        return HttpResponse("Can not get admin Status")


def getSystemStatus(request):
    default_fallback = {
        'cpuUsage': 0, 'ramUsage': 0, 'diskUsage': 0,
        'cpuCores': 2, 'ramTotalMB': 4096, 'diskTotalGB': 100,
        'diskFreeGB': 100, 'uptime': 'N/A'
    }
    try:
        val = request.session['userID']
        currentACL = ACLManager.loadedACL(val)
        admin = Administrator.objects.get(pk=val)
        
        # Admin users get full system information
        if currentACL.get('admin', 0):
            from django.core.cache import cache
            cache_key = 'cp_admin_sysstatus'
            cached = cache.get(cache_key)
            if cached is not None:
                return HttpResponse(json.dumps(cached))
            HTTPData = SystemInformation.getSystemInformation()
            try:
                cache.set(cache_key, HTTPData, 45)
            except Exception:
                pass
            json_data = json.dumps(HTTPData)
            return HttpResponse(json_data)
        else:
            # Non-admin users get user-specific resource information.
            # Cache briefly: per-site du is slow on every poll.
            from django.core.cache import cache
            cache_key = 'cp_user_sysstatus_%s' % val
            cached = cache.get(cache_key)
            if cached is not None:
                return HttpResponse(json.dumps(cached))

            import subprocess
            import os

            # Calculate user's disk usage
            total_disk_used = 0
            total_disk_limit = 0
            
            # Get websites owned by this user
            user_websites = admin.websites_set.all()
            
            # Also get websites owned by admins created by this user (reseller pattern)
            child_admins = Administrator.objects.filter(owner=admin.pk)
            for child_admin in child_admins:
                user_websites = user_websites | child_admin.websites_set.all()
            
            # Calculate disk usage for all user's websites
            for website in user_websites:
                website_path = f"/home/{website.domain}"
                if os.path.exists(website_path):
                    try:
                        # Get disk usage in MB
                        result = subprocess.check_output(['du', '-sm', website_path], stderr=subprocess.DEVNULL)
                        disk_used = int(result.decode().split()[0])
                        total_disk_used += disk_used
                    except:
                        pass
                
                # Get disk limit from package
                if website.package:
                    total_disk_limit += website.package.diskSpace
            
            # du -sm reports MB and package.diskSpace is stored in MB; convert both to GB for display
            total_disk_used_gb = round(total_disk_used / 1024, 2)
            total_disk_limit_gb = round(total_disk_limit / 1024, 2) if total_disk_limit > 0 else 100  # Default 100GB if no limit
            disk_free_gb = max(0, total_disk_limit_gb - total_disk_used_gb)
            disk_usage_percent = min(100, int((total_disk_used_gb / total_disk_limit_gb) * 100)) if total_disk_limit_gb > 0 else 0
            
            # Calculate bandwidth usage (simplified - you may want to implement actual bandwidth tracking)
            bandwidth_used = 0
            bandwidth_limit = 0
            for website in user_websites:
                if website.package:
                    bandwidth_limit += website.package.bandwidth
            
            bandwidth_limit_gb = round(bandwidth_limit / 1024, 2) if bandwidth_limit > 0 else 1000  # Default 1000GB if no limit
            bandwidth_usage_percent = 0  # You can implement actual bandwidth tracking here
            
            # Count resources
            total_websites = user_websites.count()
            total_databases = 0
            total_emails = 0
            
            website_names = list(user_websites.values_list('domain', flat=True))
            if website_names:
                total_databases = Databases.objects.filter(website__domain__in=website_names).count()
                total_emails = EUsers.objects.filter(emailOwner__domainOwner__domain__in=website_names).count()
            
            # Prepare response data matching the expected format
            user_data = {
                'cpuUsage': cpu_usage,
                'ramUsage': ram_usage,
                'diskUsage': disk_usage_percent,
                'cpuCores': cpu_cores,
                'ramTotalMB': ram_total_mb,
                'diskTotalGB': int(total_disk_limit_gb),
                'diskFreeGB': int(disk_free_gb),
                'uptime': 'User Account Active'
            }
            
            try:
                cache.set(cache_key, user_data, 300)
            except Exception:
                pass

            json_data = json.dumps(user_data)
            return HttpResponse(json_data)
            
    except KeyError as e:
        logging.CyberCPLogFileWriter.writeToFile(f'[getSystemStatus] KeyError - No session userID: {str(e)}')
        return HttpResponse(json.dumps(default_fallback))
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f'[getSystemStatus] Exception: {str(e)}')
        try:
            return HttpResponse(json.dumps(default_fallback))
        except Exception:
            return HttpResponse('{"cpuUsage":0,"ramUsage":0,"diskUsage":0,"cpuCores":2,"ramTotalMB":4096,"diskTotalGB":100,"diskFreeGB":100,"uptime":"N/A"}', content_type='application/json')


def getLoadAverage(request):
    try:
        val = request.session['userID']
        currentACL = ACLManager.loadedACL(val)
        
        # Only admins should see system load averages
        if not currentACL.get('admin', 0):
            return HttpResponse(json.dumps({'status': 0, 'error_message': 'Admin access required'}), content_type='application/json', status=403)
        
        loadAverage = SystemInformation.cpuLoad()
        loadAverage = list(loadAverage)
        one = loadAverage[0]
        two = loadAverage[1]
        three = loadAverage[2]
        loadAvg = {"one": one, "two": two, "three": three}
        json_data = json.dumps(loadAvg)
        return HttpResponse(json_data)
    except KeyError:
        return HttpResponse("Not allowed.")


@ensure_csrf_cookie
def versionManagment(request):
    currentVersion = VERSION
    currentBuild = str(BUILD)

    notechk = True
    Currentcomt = ''
    latestcomit = ''
    latestVersion = '0'
    latestBuild = '0'
    upstream_latest_sha = ''
    fork_latest_sha = ''
    show_fork_block = False
    fork_display = ''
    fork_commit_url = ''
    upstream_commit_url = ''
    fork_drift_upstream = False

    on_dev_branch = (currentVersion == '2.5.5' and currentBuild == 'dev')

    try:
        getVersion = requests.get('https://cyberpanel.net/version.txt', timeout=10)
        getVersion.raise_for_status()
        latest = getVersion.json()
        latestVersion = str(latest.get('version', '0'))
        latestBuild = str(latest.get('build', '0'))
    except (requests.RequestException, ValueError, KeyError) as e:
        logging.CyberCPLogFileWriter.writeToFile('[versionManagment] cyberpanel.net/version.txt failed: %s' % str(e))
        if on_dev_branch:
            latestVersion, latestBuild = '2.5.5', 'dev'

    if on_dev_branch:
        branch_ref = 'v2.5.5-dev'
        latestVersion, latestBuild = '2.5.5', 'dev'
    else:
        branch_ref = 'v%s.%s' % (latestVersion, latestBuild)

    head_cmd = 'git -C /usr/local/CyberCP rev-parse HEAD 2>/dev/null || true'
    Currentcomt = (ProcessUtilities.outputExecutioner(head_cmd) or '').rstrip('\n')

    remote_cmd = 'git -C /usr/local/CyberCP remote get-url origin 2>/dev/null || true'
    remote_out = (ProcessUtilities.outputExecutioner(remote_cmd) or '')
    origin_owner, origin_repo = _parse_github_origin(remote_out)
    if origin_owner and origin_repo:
        remote_display = '%s/%s' % (origin_owner, origin_repo)
        is_official = (origin_owner.lower() == 'usmannasir' and origin_repo.lower() == 'cyberpanel')
        show_fork_block = not is_official
        if show_fork_block:
            fork_display = remote_display
    else:
        remote_display = (remote_out.strip() or '—')
        logging.CyberCPLogFileWriter.writeToFile(
            '[versionManagment] Unparseable git origin, upstream-only UI: %s'
            % (remote_out[:200] if remote_out else '(empty)'))
        show_fork_block = False

    upstream_latest_sha = _github_branch_tip_sha('usmannasir', 'cyberpanel', branch_ref)
    latestcomit = upstream_latest_sha
    if upstream_latest_sha:
        upstream_commit_url = 'https://github.com/usmannasir/cyberpanel/commit/%s' % upstream_latest_sha

    if show_fork_block and origin_owner and origin_repo:
        fork_latest_sha = _github_branch_tip_sha(origin_owner, origin_repo, branch_ref)
        if fork_latest_sha:
            fork_commit_url = 'https://github.com/%s/%s/commit/%s' % (
                origin_owner, origin_repo, fork_latest_sha)

    if (fork_latest_sha and upstream_latest_sha and fork_latest_sha != upstream_latest_sha):
        fork_drift_upstream = True

    if not on_dev_branch and notechk and _version_compare(currentVersion, latestVersion) > 0:
        notechk = False
    elif notechk:
        cur = (Currentcomt or '').strip().lower()
        if show_fork_block:
            fk = (fork_latest_sha or '').strip().lower()
            up = (upstream_latest_sha or '').strip().lower()
            if fk:
                notechk = not (bool(cur) and cur == fk)
            elif up:
                notechk = not (bool(cur) and cur == up)
            else:
                notechk = False
        else:
            up = (upstream_latest_sha or '').strip().lower()
            if up:
                notechk = not (bool(cur) and cur == up)
            else:
                notechk = False

    is_usmannasir = not show_fork_block
    fork_remote_commit = fork_latest_sha if show_fork_block else ''
    upstream_commit = upstream_latest_sha
    notecheck_compare_remote = fork_display if show_fork_block else 'usmannasir/cyberpanel'
    local_behind_official = bool(
        on_dev_branch and Currentcomt and upstream_commit and Currentcomt != upstream_commit)

    def _short_sha(commit_hash):
        if not commit_hash or len(commit_hash) < 7:
            return commit_hash or ''
        return commit_hash[:7]

    template = 'baseTemplate/versionManagment.html'
    finalData = {
        'build': currentBuild,
        'currentVersion': currentVersion,
        'latestVersion': latestVersion,
        'latestBuild': latestBuild,
        'latestcomit': latestcomit,
        'Currentcomt': Currentcomt,
        'Notecheck': notechk,
        'show_fork_block': show_fork_block,
        'tracking_branch': branch_ref,
        'branch_ref': branch_ref,
        'fork_display': fork_display,
        'fork_latest_sha': fork_latest_sha,
        'upstream_latest_sha': upstream_latest_sha,
        'fork_commit_url': fork_commit_url,
        'upstream_commit_url': upstream_commit_url,
        'fork_drift_upstream': fork_drift_upstream,
        'remote_display': remote_display,
        'is_usmannasir': is_usmannasir,
        'fork_remote_commit': fork_remote_commit,
        'upstream_commit': upstream_commit,
        'notecheck_compare_remote': notecheck_compare_remote,
        'local_behind_official': local_behind_official,
        'on_dev_branch': on_dev_branch,
        'Currentcomt_short': _short_sha(Currentcomt),
        'latestcomit_short': _short_sha(latestcomit),
        'fork_remote_commit_short': _short_sha(fork_remote_commit),
        'upstream_commit_short': _short_sha(upstream_commit),
        'fork_latest_sha_short': _short_sha(fork_latest_sha),
        'upstream_latest_sha_short': _short_sha(upstream_latest_sha),
    }

    proc = httpProc(request, template, finalData, 'versionManagement')
    return proc.render()


def upgrade(request):
    try:
        admin = request.session['userID']
        currentACL = ACLManager.loadedACL(admin)

        data = json.loads(request.body)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        from plogical.applicationInstaller import ApplicationInstaller

        extraArgs = {}
        extraArgs['branchSelect'] = data["branchSelect"]
        background = ApplicationInstaller('UpgradeCP', extraArgs)
        background.start()

        adminData = {"upgrade": 1, "progress": 0}
        json_data = json.dumps(adminData)
        return HttpResponse(json_data)

    except KeyError:
        adminData = {"upgrade": 1, "error_message": "Please login or refresh this page."}
        json_data = json.dumps(adminData)
        return HttpResponse(json_data)


def _read_upgrade_progress_percent():
    """Read JSON sidecar written by plogical.upgrade.Upgrade.write_upgrade_progress."""
    try:
        from plogical.upgrade import Upgrade
        prog_path = getattr(Upgrade, 'ProgressPathNew', '/home/cyberpanel/upgrade_progress')
        if os.path.isfile(prog_path):
            with open(prog_path, 'r') as rf:
                data = json.loads(rf.read())
            v = int(data.get('pct', 0))
            return max(0, min(100, v))
    except (ValueError, TypeError, json.JSONDecodeError, OSError, KeyError):
        pass
    return 0


def upgradeStatus(request):
    try:
        val = request.session['userID']
        currentACL = ACLManager.loadedACL(val)
        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('FilemanagerAdmin', 0)

        try:
            if request.method == 'POST':
                from plogical.upgrade import Upgrade

                path = Upgrade.LogPathNew
                prog_path = getattr(Upgrade, 'ProgressPathNew', '/home/cyberpanel/upgrade_progress')
                pct = _read_upgrade_progress_percent()

                upgradeLog = None
                if os.path.isfile(path):
                    try:
                        upgradeLog = ProcessUtilities.outputExecutioner(f'cat {path}')
                    except BaseException:
                        upgradeLog = None

                if upgradeLog is None or not isinstance(upgradeLog, str):
                    upgradeLog = None
                elif upgradeLog.strip().startswith('cat:'):
                    upgradeLog = None

                if upgradeLog is None:
                    final_json = json.dumps({'finished': 0, 'upgradeStatus': 1,
                                             'error_message': "None",
                                             'upgradeLog': "Waiting for upgrade log…",
                                             'progress': pct})
                    return HttpResponse(final_json)

                if upgradeLog.find("Upgrade Completed") > -1:

                    command = f'rm -rf {path}'
                    ProcessUtilities.executioner(command)
                    try:
                        if os.path.isfile(prog_path):
                            os.remove(prog_path)
                    except OSError:
                        pass

                    final_json = json.dumps({'finished': 1, 'upgradeStatus': 1,
                                             'error_message': "None",
                                             'upgradeLog': upgradeLog,
                                             'progress': 100})
                    return HttpResponse(final_json)
                else:
                    pct = _read_upgrade_progress_percent()
                    final_json = json.dumps({'finished': 0, 'upgradeStatus': 1,
                                             'error_message': "None",
                                             'upgradeLog': upgradeLog,
                                             'progress': pct})
                    return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'upgradeStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'upgradeStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def upgradeVersion(request):
    try:

        vers = version.objects.get(pk=1)
        getVersion = requests.get('https://cyberpanel.net/version.txt')
        latest = getVersion.json()
        vers.currentVersion = latest['version']
        vers.build = latest['build']
        vers.save()
        return HttpResponse("Version upgrade OK.")
    except BaseException as msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        return HttpResponse(str(msg))


@ensure_csrf_cookie
def design(request):
    ### Load Custom CSS
    try:
        from baseTemplate.models import CyberPanelCosmetic
        cosmetic = CyberPanelCosmetic.objects.get(pk=1)
    except:
        from baseTemplate.models import CyberPanelCosmetic
        cosmetic = CyberPanelCosmetic()
        cosmetic.save()

    val = request.session['userID']
    currentACL = ACLManager.loadedACL(val)
    if currentACL['admin'] == 1:
        pass
    else:
        return ACLManager.loadErrorJson('reboot', 0)

    finalData = {}

    if request.method == 'POST':
        MainDashboardCSS = request.POST.get('MainDashboardCSS', '')
        cosmetic.MainDashboardCSS = MainDashboardCSS
        cosmetic.HidePromotions = 1 if request.POST.get('HidePromotions') else 0
        cosmetic.save()
        finalData['saved'] = 1

    ####### Fetch sha...

    sha_url = "https://api.github.com/repos/usmannasir/CyberPanel-Themes/commits"

    sha_res = requests.get(sha_url)

    sha = sha_res.json()[0]['sha']

    l = "https://api.github.com/repos/usmannasir/CyberPanel-Themes/git/trees/%s" % sha
    fres = requests.get(l)
    tott = len(fres.json()['tree'])
    finalData['tree'] = []
    for i in range(tott):
        if (fres.json()['tree'][i]['type'] == "tree"):
            finalData['tree'].append(fres.json()['tree'][i]['path'])

    template = 'baseTemplate/design.html'
    finalData['cosmetic'] = cosmetic

    proc = httpProc(request, template, finalData, 'versionManagement')
    return proc.render()


def getthemedata(request):
    try:
        val = request.session['userID']
        currentACL = ACLManager.loadedACL(val)
        data = json.loads(request.body)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('reboot', 0)

        # logging.CyberCPLogFileWriter.writeToFile(str(data) + "  [themedata]")

        url = "https://raw.githubusercontent.com/usmannasir/CyberPanel-Themes/main/%s/design.css" % data['Themename']

        res = requests.get(url)

        rsult = res.text
        final_dic = {'status': 1, 'csscontent': rsult}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)
    except BaseException as msg:
        final_dic = {'status': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def onboarding(request):
    template = 'baseTemplate/onboarding.html'

    proc = httpProc(request, template, None, 'admin')
    return proc.render()


@ensure_csrf_cookie
def cpHub(request, section):
    # Category landing pages ("hubs") that replace the old deep sidebar
    # accordions with a scannable grid of labelled tiles.
    section = (section or '').lower()
    adminOnly = {'server', 'security', 'settings'}
    func = 'admin' if section in adminOnly else None
    template = 'baseTemplate/hub.html'
    proc = httpProc(request, template, {'section': section}, func)
    return proc.render()


@ensure_csrf_cookie
def buildServices(request):
    # In-panel landing for CyberPanel development services (Android, iOS,
    # web and custom software). The full marketing page lives on
    # cyberpanel.net; this page introduces the offering and deep-links out.
    template = 'baseTemplate/buildServices.html'
    proc = httpProc(request, template, {})
    return proc.render()


def runonboarding(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        data = json.loads(request.body)
        hostname = data['hostname']

        try:
            rDNSCheck = str(int(data['rDNSCheck']))
        except:
            rDNSCheck = 0

        tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

        WriteToFile = open(tempStatusPath, 'w')
        WriteToFile.write('Starting')
        WriteToFile.close()

        command = f'/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/virtualHostUtilities.py OnBoardingHostName --virtualHostName {hostname} --path {tempStatusPath} --rdns {rDNSCheck}'
        ProcessUtilities.popenExecutioner(command)

        dic = {'status': 1, 'tempStatusPath': tempStatusPath}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


    except BaseException as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def RestartCyberPanel(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()


        command = 'systemctl restart lscpd'
        ProcessUtilities.popenExecutioner(command)

        dic = {'status': 1}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)


    except BaseException as msg:
        dic = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def getDashboardStats(request):
    try:
        val = request.session.get('userID')
        if val is None:
            return HttpResponse(
                json.dumps({'status': 0, 'error_message': 'Session required'}),
                content_type='application/json'
            )
        currentACL = ACLManager.loadedACL(val)
        admin = Administrator.objects.get(pk=val)
        
        # Check if user is admin
        if currentACL.get('admin', 0) == 1:
            # Admin can see all resources
            total_users = Administrator.objects.count()
            total_sites = Websites.objects.count()
            total_wp_sites = WPSites.objects.count()
            total_dbs = Databases.objects.count()
            total_emails = EUsers.objects.count()
            total_ftp_users = FTPUsers.objects.count()
        else:
            # Non-admin users can only see their own resources and resources of users they created
            
            # Count users created by this admin (resellers)
            total_users = Administrator.objects.filter(owner=admin.pk).count() + 1  # +1 for self
            
            # Get websites directly owned by this admin
            user_websites = admin.websites_set.all()
            website_names = list(user_websites.values_list('domain', flat=True))
            
            # Also get websites owned by admins created by this user (reseller pattern)
            child_admins = Administrator.objects.filter(owner=admin.pk)
            for child_admin in child_admins:
                child_websites = child_admin.websites_set.all()
                website_names.extend(list(child_websites.values_list('domain', flat=True)))
            
            total_sites = len(website_names)
            
            # Count WP sites associated with user's websites
            if website_names:
                total_wp_sites = WPSites.objects.filter(owner__domain__in=website_names).count()
                
                # Count databases associated with user's websites
                total_dbs = Databases.objects.filter(website__domain__in=website_names).count()
                
                # Count email accounts associated with user's domains
                from mailServer.models import Domains as EmailDomains
                total_emails = EUsers.objects.filter(emailOwner__domainOwner__domain__in=website_names).count()
                
                # Count FTP users associated with user's domains
                total_ftp_users = FTPUsers.objects.filter(domain__domain__in=website_names).count()
            else:
                total_wp_sites = 0
                total_dbs = 0
                total_emails = 0
                total_ftp_users = 0
        
        data = {
            'total_users': total_users,
            'total_sites': total_sites,
            'total_wp_sites': total_wp_sites,
            'total_dbs': total_dbs,
            'total_emails': total_emails,
            'total_ftp_users': total_ftp_users,
            'status': 1
        }
        return HttpResponse(json.dumps(data), content_type='application/json')
    except Exception as e:
        logging.writeToFile('getDashboardStats error: %s' % str(e))
        return HttpResponse(
            json.dumps({'status': 0, 'error_message': 'Failed to load dashboard stats'}),
            content_type='application/json'
        )

def getTrafficStats(request):
    try:
        val = request.session.get('userID')
        if val is None:
            return HttpResponse(
                json.dumps({'status': 0, 'error_message': 'Session required'}),
                content_type='application/json'
            )
        currentACL = ACLManager.loadedACL(val)
        if not currentACL.get('admin', 0):
            return HttpResponse(json.dumps({'status': 0, 'error_message': 'Admin access required', 'admin_only': True}), content_type='application/json')
        
        rx = tx = 0
        with open('/proc/net/dev', 'r') as f:
            for line in f.readlines():
                if 'lo:' in line:
                    continue
                if ':' in line:
                    parts = line.split()
                    try:
                        if len(parts) >= 10:
                            rx += int(parts[1])
                            tx += int(parts[9])
                    except (ValueError, IndexError):
                        continue
        data = {'rx_bytes': rx, 'tx_bytes': tx, 'status': 1}
        return HttpResponse(json.dumps(data), content_type='application/json')
    except Exception as e:
        logging.writeToFile('getTrafficStats error: %s' % str(e))
        return HttpResponse(
            json.dumps({'status': 0, 'error_message': 'Failed to load traffic stats'}),
            content_type='application/json'
        )

def getDiskIOStats(request):
    try:
        val = request.session.get('userID')
        if val is None:
            return HttpResponse(
                json.dumps({'status': 0, 'error_message': 'Session required'}),
                content_type='application/json'
            )
        currentACL = ACLManager.loadedACL(val)
        if not currentACL.get('admin', 0):
            return HttpResponse(json.dumps({'status': 0, 'error_message': 'Admin access required', 'admin_only': True}), content_type='application/json')
        
        read_sectors = 0
        write_sectors = 0
        sector_size = 512
        with open('/proc/diskstats', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) < 14:
                    continue
                dev = parts[2]
                if dev.startswith('loop') or dev.startswith('ram'):
                    continue
                try:
                    read_sectors += int(parts[5])
                    write_sectors += int(parts[9])
                except (ValueError, IndexError):
                    continue
        data = {
            'read_bytes': read_sectors * sector_size,
            'write_bytes': write_sectors * sector_size,
            'status': 1
        }
        return HttpResponse(json.dumps(data), content_type='application/json')
    except Exception as e:
        logging.writeToFile('getDiskIOStats error: %s' % str(e))
        return HttpResponse(
            json.dumps({'status': 0, 'error_message': 'Failed to load disk I/O stats'}),
            content_type='application/json'
        )

def getCPULoadGraph(request):
    try:
        val = request.session.get('userID')
        if val is None:
            return HttpResponse(
                json.dumps({'status': 0, 'error_message': 'Session required'}),
                content_type='application/json'
            )
        currentACL = ACLManager.loadedACL(val)
        if not currentACL.get('admin', 0):
            return HttpResponse(json.dumps({'status': 0, 'error_message': 'Admin access required', 'admin_only': True}), content_type='application/json')
        
        cpu_times = []
        with open('/proc/stat', 'r') as f:
            for line in f:
                if line.startswith('cpu '):
                    parts = line.strip().split()
                    try:
                        cpu_times = [float(x) for x in parts[1:]]
                    except (ValueError, IndexError):
                        pass
                    break
        data = {'cpu_times': cpu_times, 'status': 1}
        return HttpResponse(json.dumps(data), content_type='application/json')
    except Exception as e:
        logging.writeToFile('getCPULoadGraph error: %s' % str(e))
        return HttpResponse(
            json.dumps({'status': 0, 'error_message': 'Failed to load CPU stats'}),
            content_type='application/json'
        )

@csrf_exempt
@require_GET
def getRecentSSHLogins(request):
    try:
        user_id = request.session.get('userID')
        if not user_id:
            return HttpResponse(json.dumps({'error': 'Not logged in'}), content_type='application/json', status=403)
        currentACL = ACLManager.loadedACL(user_id)
        if not currentACL.get('admin', 0):
            return HttpResponse(json.dumps({'error': 'Admin only'}), content_type='application/json', status=403)

        import re, time
        from collections import OrderedDict

        # Pagination params
        try:
            page = max(1, int(request.GET.get('page', 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            per_page = min(100, max(5, int(request.GET.get('per_page', 20))))
        except (ValueError, TypeError):
            per_page = 20

        # Run 'last -n 500' to get enough entries for pagination
        try:
            output = ProcessUtilities.outputExecutioner('last -n 500')
        except Exception as e:
            return HttpResponse(json.dumps({'error': 'Failed to run last: %s' % str(e)}), content_type='application/json', status=500)

        lines = output.strip().split('\n')
        logins = []
        ip_cache = {}
        for line in lines:
            if not line.strip() or any(x in line for x in ['reboot', 'system boot', 'wtmp begins']):
                continue
            # Example: ubuntu   pts/0        206.84.168.7     Sun Jun  1 19:41   still logged in
            # or:     ubuntu   pts/0        206.84.169.36    Tue May 27 11:34 - 13:47  (02:13)
            parts = re.split(r'\s+', line, maxsplit=5)
            if len(parts) < 5:
                continue
            user, tty, ip, *rest = parts
            # Find date/time and session info
            date_session = rest[-1] if rest else ''
            # Try to extract date/session
            date_match = re.search(r'([A-Za-z]{3} [A-Za-z]{3} +\d+ [\d:]+)', line)
            date_str = date_match.group(1) if date_match else ''
            session_info = ''
            is_active = False
            if 'still logged in' in line:
                session_info = 'still logged in'
                is_active = True
            elif '-' in line:
                # Session ended - parse the end time and duration
                # Format: "Tue May 27 11:34 - 13:47  (02:13)" or "crash (00:40)"
                end_part = line.split('-')[-1].strip()
                # Check if it's a crash or normal logout
                if 'crash' in end_part.lower():
                    # Extract crash duration if available
                    crash_match = re.search(r'crash\s*\(([^)]+)\)', end_part, re.IGNORECASE)
                    if crash_match:
                        session_info = f"crash ({crash_match.group(1)})"
                    else:
                        session_info = 'crash'
                else:
                    # Normal session end - try to extract duration
                    duration_match = re.search(r'\(([^)]+)\)', end_part)
                    if duration_match:
                        session_info = f"ended ({duration_match.group(1)})"
                    else:
                        # Just show the end time
                        time_match = re.search(r'([A-Za-z]{3}\s+[A-Za-z]{3}\s+\d+\s+[\d:]+)', end_part)
                        if time_match:
                            session_info = f"ended at {time_match.group(1)}"
                        else:
                            session_info = 'ended'
                is_active = False
            # GeoIP lookup (cache per request) - support both IPv4 and IPv6
            country = flag = ''
            # Check if IP is IPv4
            is_ipv4 = re.match(r'^\d+\.\d+\.\d+\.\d+$', ip)
            # Check if IP is IPv6 (simplified check)
            is_ipv6 = ':' in ip and not is_ipv4
            
            if is_ipv4 and ip != '127.0.0.1':
                if ip in ip_cache:
                    country, flag = ip_cache[ip]
                else:
                    try:
                        geo = requests.get(f'http://ip-api.com/json/{ip}', timeout=1).json()
                        country = geo.get('countryCode', '')
                        flag = f"https://flagcdn.com/24x18/{country.lower()}.png" if country else ''
                        ip_cache[ip] = (country, flag)
                    except Exception:
                        country, flag = '', ''
            elif is_ipv6 and ip != '::1':
                # IPv6 - set flag to indicate IPv6 (GeoIP API may not support IPv6 well)
                country, flag = 'IPv6', ''
            elif ip == '127.0.0.1' or ip == '::1':
                country, flag = 'Local', ''
            logins.append({
                'user': user,
                'ip': ip,
                'country': country,
                'flag': flag,
                'date': date_str,
                'session': session_info,
                'is_active': is_active,
                'raw': line
            })
        total = len(logins)
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        page = min(page, total_pages) if total_pages > 0 else 1
        start = (page - 1) * per_page
        end = start + per_page
        paginated_logins = logins[start:end]
        return HttpResponse(json.dumps({
            'logins': paginated_logins,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        }), content_type='application/json')
    except Exception as e:
        return HttpResponse(json.dumps({'error': str(e)}), content_type='application/json', status=500)

@csrf_exempt
@require_GET
def getRecentSSHLogs(request):
    try:
        user_id = request.session.get('userID')
        if not user_id:
            return HttpResponse(json.dumps({'error': 'Not logged in'}), content_type='application/json', status=403)
        currentACL = ACLManager.loadedACL(user_id)
        if not currentACL.get('admin', 0):
            return HttpResponse(json.dumps({'error': 'Admin only'}), content_type='application/json', status=403)

        # Pagination params
        try:
            page = max(1, int(request.GET.get('page', 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            per_page = min(100, max(5, int(request.GET.get('per_page', 25))))
        except (ValueError, TypeError):
            per_page = 25

        from plogical.processUtilities import ProcessUtilities
        import re
        distro = ProcessUtilities.decideDistro()
        if distro in [ProcessUtilities.ubuntu, ProcessUtilities.ubuntu20]:
            log_path = '/var/log/auth.log'
        else:
            log_path = '/var/log/secure'
        try:
            output = ProcessUtilities.outputExecutioner(f'tail -n 500 {log_path}')
        except Exception as e:
            return HttpResponse(json.dumps({'error': f'Failed to read log: {str(e)}'}), content_type='application/json', status=500)
        lines = output.split('\n')
        logs = []
        # IP address regex patterns (IPv4)
        ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        
        for line in lines:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) > 4:
                timestamp = ' '.join(parts[:3])
                message = ' '.join(parts[4:])
            else:
                timestamp = ''
                message = line
            
            # Extract IP address from the log line
            ip_address = None
            ip_matches = re.findall(ipv4_pattern, line)
            if ip_matches:
                # Filter out localhost and common non-external IPs
                for ip in ip_matches:
                    if ip not in ['127.0.0.1', '0.0.0.0', '::1'] and not ip.startswith('192.168.') and not ip.startswith('10.') and not ip.startswith('172.'):
                        ip_address = ip
                        break
                # If no external IP found, use the first match anyway (might be needed for internal attacks)
                if not ip_address and ip_matches:
                    ip_address = ip_matches[0]
            
            logs.append({
                'timestamp': timestamp, 
                'message': message, 
                'raw': line,
                'ip_address': ip_address
            })
        # Reverse so newest logs appear first (page 1 = most recent)
        logs.reverse()
        total = len(logs)
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        page = min(page, total_pages) if total_pages > 0 else 1
        start = (page - 1) * per_page
        end = start + per_page
        paginated_logs = logs[start:end]
        return HttpResponse(json.dumps({
            'logs': paginated_logs,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        }), content_type='application/json')
    except Exception as e:
        return HttpResponse(json.dumps({'error': str(e)}), content_type='application/json', status=500)

@csrf_exempt
@require_POST
def analyzeSSHSecurity(request):
    try:
        user_id = request.session.get('userID')
        if not user_id:
            return HttpResponse(json.dumps({'error': 'Not logged in'}), content_type='application/json', status=403)
        currentACL = ACLManager.loadedACL(user_id)
        if not currentACL.get('admin', 0):
            return HttpResponse(json.dumps({'error': 'Admin only'}), content_type='application/json', status=403)
        
        # Check if user has CyberPanel addons
        if not ACLManager.CheckForPremFeature('all'):
            return HttpResponse(json.dumps({
                'status': 0,
                'addon_required': True,
                'feature_title': 'SSH Security Analysis',
                'feature_description': 'Advanced SSH security monitoring and threat detection that helps protect your server from brute force attacks, port scanning, and unauthorized access attempts.',
                'features': [
                    'Real-time detection of brute force attacks',
                    'Identification of dictionary attacks and invalid login attempts',
                    'Port scanning detection',
                    'Root login attempt monitoring',
                    'Automatic security recommendations',
                    'Integration with CSF and Firewalld',
                    'Detailed threat analysis and reporting'
                ],
                'addon_url': 'https://cyberpanel.net/cyberpanel-addons'
            }), content_type='application/json')
        
        from plogical.processUtilities import ProcessUtilities
        import re
        from collections import defaultdict
        from datetime import datetime, timedelta
        
        alerts = []
        
        # Use firewalld (CSF has been discontinued)
        firewall_cmd = 'firewalld'
        try:
            # Verify firewalld is active
            firewalld_check = ProcessUtilities.outputExecutioner('systemctl is-active firewalld')
            if not (firewalld_check and 'active' in firewalld_check):
                # Firewalld not active, but continue analysis with firewalld commands
                pass
        except:
            # Continue with firewalld as default
            pass
        
        # Determine log path
        distro = ProcessUtilities.decideDistro()
        if distro in [ProcessUtilities.ubuntu, ProcessUtilities.ubuntu20]:
            log_path = '/var/log/auth.log'
        else:
            log_path = '/var/log/secure'
        
        try:
            # Get last 500 lines for better analysis
            output = ProcessUtilities.outputExecutioner(f'tail -n 500 {log_path}')
        except Exception as e:
            return HttpResponse(json.dumps({'error': f'Failed to read log: {str(e)}'}), content_type='application/json', status=500)
        
        lines = output.split('\n')
        
        # Analysis patterns
        failed_logins = defaultdict(int)
        failed_passwords = defaultdict(int)
        invalid_users = defaultdict(int)
        port_scan_attempts = defaultdict(int)
        suspicious_commands = []
        root_login_attempts = []
        successful_after_failures = defaultdict(list)
        connection_closed = defaultdict(int)
        repeated_connections = defaultdict(int)
        
        # Track IPs with failures for brute force detection
        ip_failures = defaultdict(list)
        
        # Track time-based patterns
        recent_attempts = defaultdict(list)
        
        for line in lines:
            if not line.strip():
                continue
            
            # Failed password attempts
            if 'Failed password' in line:
                match = re.search(r'Failed password for (?:invalid user )?(\S+) from (\S+)', line)
                if match:
                    user, ip = match.groups()
                    failed_passwords[ip] += 1
                    ip_failures[ip].append(('password', user, line))
                    
                    # Check for root login attempts
                    if user == 'root':
                        root_login_attempts.append({
                            'ip': ip,
                            'line': line
                        })
            
            # Invalid user attempts
            elif 'Invalid user' in line or 'invalid user' in line:
                match = re.search(r'[Ii]nvalid user (\S+) from (\S+)', line)
                if match:
                    user, ip = match.groups()
                    invalid_users[ip] += 1
                    ip_failures[ip].append(('invalid', user, line))
            
            # Port scan detection
            elif 'Did not receive identification string' in line or 'Bad protocol version identification' in line:
                match = re.search(r'from (\S+)', line)
                if match:
                    ip = match.group(1)
                    port_scan_attempts[ip] += 1
            
            # Successful login after failures
            elif 'Accepted' in line and 'for' in line:
                match = re.search(r'Accepted \S+ for (\S+) from (\S+)', line)
                if match:
                    user, ip = match.groups()
                    if ip in ip_failures:
                        successful_after_failures[ip].append({
                            'user': user,
                            'failures': len(ip_failures[ip]),
                            'line': line
                        })
            
            # Suspicious commands or activities
            elif any(pattern in line for pattern in ['COMMAND=', 'sudo:', 'su[', 'authentication failure']):
                if any(cmd in line for cmd in ['/etc/passwd', '/etc/shadow', 'chmod 777', 'rm -rf /', 'wget', 'curl', 'base64']):
                    suspicious_commands.append(line)
            
            # Connection closed by authenticating user
            elif 'Connection closed by authenticating user' in line:
                match = re.search(r'Connection closed by authenticating user \S+ (\S+)', line)
                if match:
                    ip = match.group(1)
                    connection_closed[ip] += 1
            
            # Repeated connection attempts
            elif 'Connection from' in line or 'Connection closed by' in line:
                match = re.search(r'from (\S+)', line)
                if match:
                    ip = match.group(1)
                    repeated_connections[ip] += 1
        
        # Generate alerts based on analysis
        
        # High severity: Brute force attacks
        for ip, count in failed_passwords.items():
            if count >= 10:
                recommendation = f'Block this IP immediately:\nfirewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address={ip} drop" && firewall-cmd --reload'
                
                alerts.append({
                    'title': 'Brute Force Attack Detected',
                    'description': f'IP address {ip} has made {count} failed password attempts. This indicates a potential brute force attack.',
                    'severity': 'high',
                    'details': {
                        'IP Address': ip,
                        'Failed Attempts': count,
                        'Attack Type': 'Brute Force'
                    },
                    'recommendation': recommendation
                })
        
        # High severity: Root login attempts
        if root_login_attempts:
            alerts.append({
                'title': 'Root Login Attempts Detected',
                'description': f'Direct root login attempts detected from {len(set(r["ip"] for r in root_login_attempts))} IP addresses. Root SSH access should be disabled.',
                'severity': 'high',
                'details': {
                    'Unique IPs': len(set(r["ip"] for r in root_login_attempts)),
                    'Total Attempts': len(root_login_attempts),
                    'Top IP': max(set(r["ip"] for r in root_login_attempts), key=lambda x: sum(1 for r in root_login_attempts if r["ip"] == x))
                },
                'recommendation': 'Disable root SSH login by setting "PermitRootLogin no" in /etc/ssh/sshd_config'
            })
        
        # Medium severity: Dictionary attacks
        for ip, count in invalid_users.items():
            if count >= 5:
                if firewall_cmd == 'csf':
                    recommendation = f'Consider blocking this IP:\ncsf -d {ip} "Dictionary attack - {count} invalid users"\n\nAlso configure CSF Login Failure Daemon (lfd) for automatic blocking.'
                else:
                    recommendation = f'Consider blocking this IP:\nfirewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address={ip} drop" && firewall-cmd --reload\n\nAlso consider implementing fail2ban for automatic blocking.'
                
                alerts.append({
                    'title': 'Dictionary Attack Detected',
                    'description': f'IP address {ip} attempted to login with {count} non-existent usernames. This indicates a dictionary attack.',
                    'severity': 'medium',
                    'details': {
                        'IP Address': ip,
                        'Invalid User Attempts': count,
                        'Attack Type': 'Dictionary Attack'
                    },
                    'recommendation': recommendation
                })
        
        # Medium severity: Port scanning
        for ip, count in port_scan_attempts.items():
            if count >= 3:
                alerts.append({
                    'title': 'Port Scan Detected',
                    'description': f'IP address {ip} appears to be scanning SSH port with {count} connection attempts without proper identification.',
                    'severity': 'medium',
                    'details': {
                        'IP Address': ip,
                        'Scan Attempts': count,
                        'Attack Type': 'Port Scan'
                    },
                    'recommendation': 'Monitor this IP for further suspicious activity. Consider using port knocking or changing SSH port.'
                })
        
        # Low severity: Successful login after failures
        for ip, successes in successful_after_failures.items():
            if successes:
                max_failures = max(s['failures'] for s in successes)
                if max_failures >= 3:
                    alerts.append({
                        'title': 'Successful Login After Multiple Failures',
                        'description': f'IP address {ip} successfully logged in after {max_failures} failed attempts. This could be legitimate or a successful breach.',
                        'severity': 'low',
                        'details': {
                            'IP Address': ip,
                            'Failed Attempts Before Success': max_failures,
                            'Successful User': successes[0]['user']
                        },
                        'recommendation': 'Verify if this login is legitimate. Check user activity and consider enforcing stronger passwords.'
                    })
        
        # High severity: Rapid connection attempts (DDoS/flooding)
        for ip, count in repeated_connections.items():
            if count >= 50:
                if firewall_cmd == 'csf':
                    recommendation = f'Block this IP immediately to prevent resource exhaustion:\ncsf -d {ip} "SSH flooding - {count} connections"'
                else:
                    recommendation = f'Block this IP immediately to prevent resource exhaustion:\nfirewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address={ip} drop" && firewall-cmd --reload'
                
                alerts.append({
                    'title': 'SSH Connection Flooding Detected',
                    'description': f'IP address {ip} has made {count} rapid connection attempts. This may be a DDoS attack or connection flooding.',
                    'severity': 'high',
                    'details': {
                        'IP Address': ip,
                        'Connection Attempts': count,
                        'Attack Type': 'Connection Flooding'
                    },
                    'recommendation': recommendation
                })
        
        # Medium severity: Suspicious command execution
        if suspicious_commands:
            alerts.append({
                'title': 'Suspicious Command Execution Detected',
                'description': f'Detected {len(suspicious_commands)} suspicious command executions that may indicate system compromise.',
                'severity': 'medium',
                'details': {
                    'Suspicious Commands': len(suspicious_commands),
                    'Command Types': 'System file access, downloads, or dangerous operations',
                    'Sample': suspicious_commands[0] if suspicious_commands else ''
                },
                'recommendation': 'Review these commands immediately. If unauthorized, investigate the affected user accounts and consider:\n• Changing all passwords\n• Reviewing sudo access\n• Checking for backdoors or rootkits'
            })
        
        # Add general recommendations if no specific alerts
        if not alerts:
            # Check for best practices
            ssh_config_recommendations = []
            try:
                sshd_config = ProcessUtilities.outputExecutioner('grep -E "^(PermitRootLogin|PasswordAuthentication|Port)" /etc/ssh/sshd_config')
                if 'PermitRootLogin yes' in sshd_config:
                    ssh_config_recommendations.append('• Disable root login: Set "PermitRootLogin no" in /etc/ssh/sshd_config')
                if 'Port 22' in sshd_config:
                    ssh_config_recommendations.append('• Change default SSH port from 22 to reduce automated attacks')
            except:
                pass
            
            if ssh_config_recommendations:
                alerts.append({
                    'title': 'SSH Security Best Practices',
                    'description': 'While no immediate threats were detected, consider implementing these security enhancements.',
                    'severity': 'info',
                    'details': {
                        'Status': 'No Active Threats',
                        'Logs Analyzed': len(lines),
                        'Firewall': firewall_cmd.upper() if firewall_cmd else 'Unknown'
                    },
                    'recommendation': '\n'.join(ssh_config_recommendations)
                })
            else:
                alerts.append({
                    'title': 'No Immediate Threats Detected',
                    'description': 'No significant security threats were detected in recent SSH logs. Your SSH configuration follows security best practices.',
                    'severity': 'info',
                    'details': {
                        'Status': 'Secure',
                        'Logs Analyzed': len(lines),
                        'Firewall': firewall_cmd.upper() if firewall_cmd else 'Unknown'
                    },
                    'recommendation': 'Keep your system updated and continue regular security monitoring.'
                })
        
        # Sort alerts by severity
        severity_order = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}
        alerts.sort(key=lambda x: severity_order.get(x['severity'], 3))
        
        return HttpResponse(json.dumps({
            'status': 1,
            'alerts': alerts
        }), content_type='application/json')
        
    except Exception as e:
        return HttpResponse(json.dumps({'error': str(e)}), content_type='application/json', status=500)

@csrf_exempt
@require_POST
def blockIPAddress(request):
    """
    Block an IP address using the appropriate firewall (CSF or firewalld)
    """
    try:
        user_id = request.session.get('userID')
        if not user_id:
            return HttpResponse(json.dumps({'error': 'Not logged in'}), content_type='application/json', status=403)
        
        currentACL = ACLManager.loadedACL(user_id)
        if not currentACL.get('admin', 0):
            return HttpResponse(json.dumps({'error': 'Admin only'}), content_type='application/json', status=403)
        
        # Check if user has CyberPanel addons
        if not ACLManager.CheckForPremFeature('all'):
            return HttpResponse(json.dumps({
                'status': 0,
                'error': 'Premium feature required'
            }), content_type='application/json', status=403)
        
        # Parse request body - Django request.body is always bytes
        try:
            if not request.body:
                return HttpResponse(json.dumps({
                    'status': 0,
                    'error': 'Request body is empty'
                }), content_type='application/json', status=400)
            
            body_str = request.body.decode('utf-8')
            if not body_str or body_str.strip() == '':
                return HttpResponse(json.dumps({
                    'status': 0,
                    'error': 'Request body is empty'
                }), content_type='application/json', status=400)
            
            data = json.loads(body_str)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            import plogical.CyberCPLogFileWriter as logging
            logging.CyberCPLogFileWriter.writeToFile(f'JSON decode error in blockIPAddress: {str(e)}, body: {request.body[:200] if request.body else "empty"}')
            return HttpResponse(json.dumps({
                'status': 0,
                'error': f'Invalid request format: {str(e)}'
            }), content_type='application/json', status=400)
        
        ip_address = data.get('ip_address', '').strip()
        
        if not ip_address:
            return HttpResponse(json.dumps({
                'status': 0,
                'error': 'IP address is required'
            }), content_type='application/json', status=400)
        
        # Validate IP address format and check for private/reserved ranges
        import re
        import ipaddress
        ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        if not re.match(ip_pattern, ip_address):
            return HttpResponse(json.dumps({
                'status': 0,
                'error': 'Invalid IP address format'
            }), content_type='application/json', status=400)
        
        # Check for private/reserved IP ranges to prevent self-blocking
        try:
            ip_obj = ipaddress.ip_address(ip_address)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                return HttpResponse(json.dumps({
                    'status': 0,
                    'error': 'Cannot block private, loopback, link-local, or reserved IP addresses'
                }), content_type='application/json', status=400)
            
            # Additional check for common problematic ranges
            if (ip_address.startswith('127.') or  # Loopback
                ip_address.startswith('169.254.') or  # Link-local
                ip_address.startswith('224.') or  # Multicast
                ip_address.startswith('255.') or  # Broadcast
                ip_address in ['0.0.0.0', '::1']):  # Invalid/loopback
                return HttpResponse(json.dumps({
                    'status': 0,
                    'error': 'Cannot block system or reserved IP addresses'
                }), content_type='application/json', status=400)
                
        except ValueError:
            return HttpResponse(json.dumps({
                'status': 0,
                'error': 'Invalid IP address'
            }), content_type='application/json', status=400)
        
        # Use FirewallUtilities so firewall-cmd runs with proper privileges (root/lscpd)
        firewall_cmd = 'firewalld'
        reason = data.get('reason', 'Security alert detected from dashboard')
        try:
            success, msg = FirewallUtilities.blockIP(ip_address, reason)
        except Exception as e:
            success = False
            msg = str(e)
        
        if success:
            # Add to banned IPs JSON file for consistency with firewall page
            try:
                import os
                import time
                primary_file = '/usr/local/CyberCP/data/banned_ips.json'
                legacy_file = '/etc/cyberpanel/banned_ips.json'
                banned_ips_file = primary_file if os.path.exists(primary_file) else legacy_file if os.path.exists(legacy_file) else primary_file
                banned_ips = []
                
                if os.path.exists(banned_ips_file):
                    try:
                        with open(banned_ips_file, 'r') as f:
                            banned_ips = json.load(f)
                    except:
                        banned_ips = []
                
                # Check if IP is already banned
                ip_already_banned = False
                for banned_ip in banned_ips:
                    if banned_ip.get('ip') == ip_address and banned_ip.get('active', True):
                        ip_already_banned = True
                        break
                
                if not ip_already_banned:
                    # Get reason from request data
                    reason = data.get('reason', 'Security alert detected from dashboard')
                    
                    # Add new banned IP
                    new_banned_ip = {
                        'id': int(time.time()),
                        'ip': ip_address,
                        'reason': reason,
                        'duration': 'permanent',
                        'banned_on': time.time(),
                        'expires': 'Never',
                        'active': True
                    }
                    banned_ips.append(new_banned_ip)
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(primary_file), exist_ok=True)
                    
                    # Save to file
                    with open(primary_file, 'w') as f:
                        json.dump(banned_ips, f, indent=2)
                    
                    # Also add to firewall DB so it shows on Firewall > Banned IPs
                    try:
                        from firewall.models import BannedIP
                        from django.utils import timezone
                        user_id = request.session.get('userID')
                        if user_id:
                            admin = Administrator.objects.get(pk=user_id)
                            BannedIP.objects.get_or_create(
                                ip_address=ip_address,
                                defaults={
                                    'reason': reason,
                                    'duration': 'permanent',
                                    'banned_on': timezone.now(),
                                    'expires': None,
                                    'active': True,
                                    'admin': admin,
                                }
                            )
                    except Exception as db_e:
                        logging.CyberCPLogFileWriter.writeToFile(f'Warning: Failed to add banned IP to firewall DB: {str(db_e)}')
            except Exception as e:
                # Log but don't fail the request if JSON update fails
                import plogical.CyberCPLogFileWriter as logging
                logging.CyberCPLogFileWriter.writeToFile(f'Warning: Failed to update banned_ips.json: {str(e)}')
            
            # Log the action
            import plogical.CyberCPLogFileWriter as logging
            logging.CyberCPLogFileWriter.writeToFile(f'IP address {ip_address} blocked via CyberPanel dashboard by user {user_id}')
            
            return HttpResponse(json.dumps({
                'status': 1,
                'message': f'Successfully blocked IP address {ip_address}',
                'firewall': firewall_cmd
            }), content_type='application/json')
        else:
            return HttpResponse(json.dumps({
                'status': 0,
                'error': msg or 'Failed to block IP address'
            }), content_type='application/json', status=500)
        
    except json.JSONDecodeError as e:
        import plogical.CyberCPLogFileWriter as logging
        logging.CyberCPLogFileWriter.writeToFile(f'JSON decode error in blockIPAddress: {str(e)}, body: {request.body}')
        return HttpResponse(json.dumps({
            'status': 0,
            'error': f'Invalid JSON in request: {str(e)}'
        }), content_type='application/json', status=400)
    except Exception as e:
        import plogical.CyberCPLogFileWriter as logging
        import traceback
        error_trace = traceback.format_exc()
        logging.CyberCPLogFileWriter.writeToFile(f'Error in blockIPAddress: {str(e)}\n{error_trace}')
        return HttpResponse(json.dumps({
            'status': 0,
            'error': f'Server error: {str(e)}'
        }), content_type='application/json', status=500)

@csrf_exempt
@require_POST
def getSSHUserActivity(request):
    import json, os
    from plogical.processUtilities import ProcessUtilities
    try:
        user_id = request.session.get('userID')
        if not user_id:
            return HttpResponse(json.dumps({'error': 'Not logged in'}), content_type='application/json', status=403)
        currentACL = ACLManager.loadedACL(user_id)
        if not currentACL.get('admin', 0):
            return HttpResponse(json.dumps({'error': 'Admin only'}), content_type='application/json', status=403)
        data = json.loads(request.body.decode('utf-8'))
        user = data.get('user')
        tty = data.get('tty')
        login_ip = data.get('ip', '')
        if not user:
            return HttpResponse(json.dumps({'error': 'Missing user'}), content_type='application/json', status=400)
        # Get 'w' output first (fastest, most important for session status)
        w_lines = []
        try:
            w_cmd = f"w -h {user} 2>/dev/null | head -10"
            w_output = ProcessUtilities.outputExecutioner(w_cmd)
            if w_output:
                for line in w_output.strip().split('\n'):
                    if line.strip():
                        w_lines.append(line)
        except Exception:
            w_lines = []
        
        # Get processes for the user (limit to 50 for speed)
        # If TTY is specified, filter by TTY; otherwise get all user processes
        processes = []
        try:
            if tty:
                # Filter by specific TTY
                ps_cmd = f"ps -u {user} -o pid,ppid,tty,time,cmd --no-headers 2>/dev/null | grep '{tty}' | head -50"
            else:
                # Get all processes for user
                ps_cmd = f"ps -u {user} -o pid,ppid,tty,time,cmd --no-headers 2>/dev/null | head -50"
            ps_output = ProcessUtilities.outputExecutioner(ps_cmd)
            if ps_output:
                for line in ps_output.strip().split('\n'):
                    if not line.strip():
                        continue
                    parts = line.split(None, 4)
                    if len(parts) >= 5:
                        pid, ppid, tty_val, time_val, cmd = parts[0], parts[1], parts[2], parts[3], parts[4]
                        # Additional TTY check if tty was specified
                        if tty and tty not in tty_val:
                            continue
                        # Skip CWD lookup for speed
                        proc = {
                            'pid': pid,
                            'ppid': ppid,
                            'tty': tty_val,
                            'time': time_val,
                            'cmd': cmd[:200] if len(cmd) > 200 else cmd,  # Limit command length
                            'cwd': ''  # Skip for speed
                        }
                        processes.append(proc)
        except Exception:
            processes = []
        
        # Skip slow operations for fast response:
        # - Process tree (can be computed client-side if needed)
        # - Shell history (not critical for initial load)
        # - Disk usage (not critical for initial load)
        # - GeoIP (can be fetched async later if needed)
        return HttpResponse(json.dumps({
            'processes': processes,
            'process_tree': [],  # Empty for speed
            'shell_history': [],  # Empty for speed
            'disk_usage': '',  # Empty for speed
            'geoip': {},  # Empty for speed
            'w': w_lines
        }), content_type='application/json')
    except Exception as e:
        return HttpResponse(json.dumps({'error': str(e)}), content_type='application/json', status=500)

@csrf_exempt
@require_GET
def getTopProcesses(request):
    try:
        user_id = request.session.get('userID')
        if not user_id:
            return HttpResponse(json.dumps({'error': 'Not logged in'}), content_type='application/json', status=403)
        
        currentACL = ACLManager.loadedACL(user_id)
        if not currentACL.get('admin', 0):
            return HttpResponse(json.dumps({'error': 'Admin only'}), content_type='application/json', status=403)

        from django.core.cache import cache
        cache_key = 'cp_top_processes'
        cached = cache.get(cache_key)
        if cached is not None:
            return HttpResponse(json.dumps(cached), content_type='application/json')
        
        import subprocess
        import tempfile
        
        # Create a temporary file to capture top output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Get top processes data
            with open(temp_path, "w") as outfile:
                subprocess.call("top -n1 -b", shell=True, stdout=outfile)
            
            with open(temp_path, 'r') as infile:
                data = infile.readlines()
            
            processes = []
            counter = 0
            
            for line in data:
                counter += 1
                if counter <= 7:  # Skip header lines
                    continue
                
                if len(processes) >= 10:  # Limit to top 10 processes
                    break
                
                points = line.split()
                points = [a for a in points if a != '']
                
                if len(points) >= 12:
                    process = {
                        'pid': points[0],
                        'user': points[1],
                        'cpu': points[8],
                        'memory': points[9],
                        'command': points[11]
                    }
                    processes.append(process)
            
            payload = {
                'status': 1,
                'processes': processes
            }
            try:
                cache.set(cache_key, payload, 8)
            except Exception:
                pass
            return HttpResponse(json.dumps(payload), content_type='application/json')
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        return HttpResponse(json.dumps({'error': str(e)}), content_type='application/json', status=500)

@csrf_exempt
@require_POST
def dismiss_backup_notification(request):
    """API endpoint to permanently dismiss the backup notification for the current user"""
    try:
        user_id = request.session.get('userID')
        if not user_id:
            return HttpResponse(json.dumps({'status': 0, 'error': 'Not logged in'}), content_type='application/json', status=403)
        
        # Get or create user notification preferences
        user = Administrator.objects.get(pk=user_id)
        preferences, created = UserNotificationPreferences.objects.get_or_create(
            user=user,
            defaults={
                'backup_notification_dismissed': False,
                'ai_scanner_notification_dismissed': False
            }
        )
        
        # Mark backup notification as dismissed
        preferences.backup_notification_dismissed = True
        preferences.save()
        
        return HttpResponse(json.dumps({'status': 1, 'message': 'Backup notification dismissed permanently'}), content_type='application/json')
        
    except Exception as e:
        return HttpResponse(json.dumps({'status': 0, 'error': str(e)}), content_type='application/json', status=500)

@csrf_exempt
@require_POST
def dismiss_ai_scanner_notification(request):
    """API endpoint to permanently dismiss the AI scanner notification for the current user"""
    try:
        user_id = request.session.get('userID')
        if not user_id:
            return HttpResponse(json.dumps({'status': 0, 'error': 'Not logged in'}), content_type='application/json', status=403)
        
        # Get or create user notification preferences
        user = Administrator.objects.get(pk=user_id)
        preferences, created = UserNotificationPreferences.objects.get_or_create(
            user=user,
            defaults={
                'backup_notification_dismissed': False,
                'ai_scanner_notification_dismissed': False
            }
        )
        
        # Mark AI scanner notification as dismissed
        preferences.ai_scanner_notification_dismissed = True
        preferences.save()
        
        return HttpResponse(json.dumps({'status': 1, 'message': 'AI scanner notification dismissed permanently'}), content_type='application/json')
        
    except Exception as e:
        return HttpResponse(json.dumps({'status': 0, 'error': str(e)}), content_type='application/json', status=500)

@csrf_exempt
@require_GET
def get_notification_preferences(request):
    """API endpoint to get current user's notification preferences"""
    try:
        user_id = request.session.get('userID')
        if not user_id:
            return HttpResponse(json.dumps({'status': 0, 'error': 'Not logged in'}), content_type='application/json', status=403)
        
        # Get user notification preferences
        user = Administrator.objects.get(pk=user_id)
        try:
            preferences = UserNotificationPreferences.objects.get(user=user)
            return HttpResponse(json.dumps({
                'status': 1,
                'backup_notification_dismissed': preferences.backup_notification_dismissed,
                'ai_scanner_notification_dismissed': preferences.ai_scanner_notification_dismissed
            }), content_type='application/json')
        except UserNotificationPreferences.DoesNotExist:
            # Return default values if preferences don't exist yet
            return HttpResponse(json.dumps({
                'status': 1,
                'backup_notification_dismissed': False,
                'ai_scanner_notification_dismissed': False
            }), content_type='application/json')
        
    except Exception as e:
        return HttpResponse(json.dumps({'status': 0, 'error': str(e)}), content_type='application/json', status=500)


def _ssh_whitelist_admin_gate(request):
    """Return (user_id, error_response). error_response is HttpResponse or None."""
    user_id = request.session.get('userID')
    if not user_id:
        return None, HttpResponse(
            json.dumps({'status': 0, 'error': 'Not logged in'}),
            content_type='application/json',
            status=403,
        )
    currentACL = ACLManager.loadedACL(user_id)
    if not currentACL.get('admin', 0):
        return None, HttpResponse(
            json.dumps({'status': 0, 'error': 'Admin only'}),
            content_type='application/json',
            status=403,
        )
    return user_id, None


def _ssh_whitelist_parse_body(request):
    try:
        if not request.body:
            return {}, None
        body_str = request.body.decode('utf-8')
        if not body_str or not body_str.strip():
            return {}, None
        data = json.loads(body_str)
        if not isinstance(data, dict):
            return None, HttpResponse(
                json.dumps({'status': 0, 'error': 'Invalid request format'}),
                content_type='application/json',
                status=400,
            )
        return data, None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, HttpResponse(
            json.dumps({'status': 0, 'error': 'Invalid request format: %s' % str(e)}),
            content_type='application/json',
            status=400,
        )


@require_POST
def sshSecurityWhitelistList(request):
    """List Trusted IPs (SSH security whitelist)."""
    try:
        _, err = _ssh_whitelist_admin_gate(request)
        if err:
            return err
        from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
        entries = SSHSecurityWhitelistUtilities.load_entries()
        return HttpResponse(
            json.dumps({'status': 1, 'entries': entries}, ensure_ascii=False),
            content_type='application/json',
        )
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile('sshSecurityWhitelistList: %s' % str(e))
        return HttpResponse(
            json.dumps({'status': 0, 'error': 'Could not load trusted IPs'}),
            content_type='application/json',
            status=500,
        )


@require_POST
def sshSecurityWhitelistAdd(request):
    """Add IP to Trusted IPs whitelist."""
    try:
        _, err = _ssh_whitelist_admin_gate(request)
        if err:
            return err
        data, perr = _ssh_whitelist_parse_body(request)
        if perr:
            return perr
        ip = (data.get('ip') or '').strip()
        label = (data.get('label') or '').strip()
        from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
        ok, result = SSHSecurityWhitelistUtilities.add_entry(ip, label)
        if ok:
            return HttpResponse(
                json.dumps({'status': 1, 'ip': result}),
                content_type='application/json',
            )
        return HttpResponse(
            json.dumps({'status': 0, 'error': result}),
            content_type='application/json',
            status=400,
        )
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile('sshSecurityWhitelistAdd: %s' % str(e))
        return HttpResponse(
            json.dumps({'status': 0, 'error': 'Could not add trusted IP'}),
            content_type='application/json',
            status=500,
        )


@require_POST
def sshSecurityWhitelistRemove(request):
    """Remove IP from Trusted IPs whitelist."""
    try:
        _, err = _ssh_whitelist_admin_gate(request)
        if err:
            return err
        data, perr = _ssh_whitelist_parse_body(request)
        if perr:
            return perr
        ip = (data.get('ip') or '').strip()
        from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
        ok, result = SSHSecurityWhitelistUtilities.remove_entry(ip)
        if ok:
            return HttpResponse(
                json.dumps({'status': 1, 'ip': result}),
                content_type='application/json',
            )
        return HttpResponse(
            json.dumps({'status': 0, 'error': result}),
            content_type='application/json',
            status=400,
        )
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile('sshSecurityWhitelistRemove: %s' % str(e))
        return HttpResponse(
            json.dumps({'status': 0, 'error': 'Could not remove trusted IP'}),
            content_type='application/json',
            status=500,
        )


@require_POST
def sshSecurityWhitelistUpdate(request):
    """Update Trusted IP row (IP and/or label)."""
    try:
        _, err = _ssh_whitelist_admin_gate(request)
        if err:
            return err
        data, perr = _ssh_whitelist_parse_body(request)
        if perr:
            return perr
        ip = (data.get('ip') or '').strip()
        new_ip = data.get('new_ip')
        label = data.get('label')
        from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
        ok, result, unchanged = SSHSecurityWhitelistUtilities.update_entry(
            ip,
            new_ip=new_ip,
            label=label,
        )
        if ok:
            msg = 'No changes to save.' if unchanged else 'Entry updated'
            return HttpResponse(
                json.dumps({
                    'status': 1,
                    'ip': result,
                    'unchanged': bool(unchanged),
                    'message': msg,
                }),
                content_type='application/json',
            )
        return HttpResponse(
            json.dumps({'status': 0, 'error': result}),
            content_type='application/json',
            status=400,
        )
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile('sshSecurityWhitelistUpdate: %s' % str(e))
        return HttpResponse(
            json.dumps({'status': 0, 'error': 'Could not update trusted IP'}),
            content_type='application/json',
            status=500,
        )
