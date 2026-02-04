#!/usr/local/CyberCP/bin/python
import html
import os
import os.path
import sys
import django

from databases.models import Databases
from plogical.DockerSites import Docker_Sites
from plogical.httpProc import httpProc

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from plogical.acl import ACLManager
import plogical.CyberCPLogFileWriter as logging
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
from websiteFunctions.models import Websites, ChildDomains, GitLogs, wpplugins, WPSites, WPStaging, WPSitesBackup, \
    RemoteBackupConfig, RemoteBackupSchedule, RemoteBackupsites, DockerPackages, PackageAssignment, DockerSites, \
    FTPQuota, BandwidthResetLog
from plogical.virtualHostUtilities import virtualHostUtilities
import subprocess
import shlex
from plogical.installUtilities import installUtilities
from django.shortcuts import HttpResponse, render, redirect
from loginSystem.models import Administrator, ACL
from packages.models import Package
from plogical.mailUtilities import mailUtilities
from random import randint
import time
import re
import boto3
from plogical.childDomain import ChildDomainManager
from math import ceil
from plogical.alias import AliasManager
from plogical.applicationInstaller import ApplicationInstaller
from plogical import hashPassword, randomPassword
# emailMarketing removed from INSTALLED_APPS
# from emailMarketing.emACL import emACL
from plogical.processUtilities import ProcessUtilities
from managePHP.phpManager import PHPManager
from ApachController.ApacheVhosts import ApacheVhost
from plogical.vhostConfs import vhostConfs
from plogical.cronUtil import CronUtil
from .StagingSetup import StagingSetup
import validators
from django.http import JsonResponse
import ipaddress


def _get_ssl_renewal_schedule():
    """Get formatted SSL renewal schedule (e.g. 'Thursday 12:00 AM').
    Reads from world-readable config file first (web server can't read root crontab).
    Cron day_of_week: 0=Sun, 1=Mon, ..., 6=Sat. Python weekday: Mon=0, ..., Sun=6."""
    try:
        from datetime import datetime, timedelta
        # Config file is world-readable; web server (lscpd) cannot read /var/spool/cron/root
        config_path = '/usr/local/CyberCP/ssl_renewal_schedule.conf'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    line = f.read().strip()
                if line:
                    return line
            except (IOError, OSError):
                pass
        cron_paths = ['/var/spool/cron/root', '/var/spool/cron/crontabs/root']
        cron_content = None
        for path in cron_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        cron_content = f.read()
                except (IOError, OSError):
                    continue
                break
        if not cron_content:
            return None
        renew_hour, renew_minute, renew_weekday_cron = 0, 0, 4  # default Thursday
        for line in cron_content.splitlines():
            line = line.strip()
            if 'renew.py' in line and not line.startswith('#'):
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        renew_minute = int(parts[0]) if parts[0].isdigit() else 0
                        renew_hour = int(parts[1]) if parts[1].isdigit() else 0
                        dow = parts[4]
                        renew_weekday_cron = int(dow) if dow.isdigit() and 0 <= int(dow) <= 7 else 4
                    except (ValueError, IndexError):
                        pass
                elif len(parts) >= 2:
                    renew_minute = int(parts[0]) if parts[0].isdigit() else 0
                    renew_hour = int(parts[1]) if parts[1].isdigit() else 0
                break
        now = datetime.now()
        # Cron: 0/7=Sun, 1=Mon, ..., 6=Sat -> Python: Mon=0, Tue=1, ..., Sun=6
        target_weekday = (renew_weekday_cron - 1) % 7 if renew_weekday_cron else 6
        days_until = (target_weekday - now.weekday()) % 7
        if days_until == 0 and (now.hour > renew_hour or (now.hour == renew_hour and now.minute >= renew_minute)):
            days_until = 7
        next_run = now.replace(hour=renew_hour, minute=renew_minute, second=0, microsecond=0)
        next_run += timedelta(days=days_until)
        return next_run.strftime('%B %d, %Y %I:%M %p')
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile('_get_ssl_renewal_schedule: ' + str(e))
        return None


class WebsiteManager:
    apache = 1
    ols = 2
    lsws = 3

    def __init__(self, domain=None, childDomain=None):
        self.domain = domain
        self.childDomain = childDomain

    def createWebsite(self, request=None, userID=None, data=None):

        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        data = {
            "name": "all",
            "IP": ACLManager.GetServerIP()
        }

        import requests
        response = requests.post(url, data=json.dumps(data))
        Status = response.json()['status']

        test_domain_status = 0

        if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
            test_domain_status = 1

        currentACL = ACLManager.loadedACL(userID)
        adminNames = ACLManager.loadAllUsers(userID)
        packagesName = ACLManager.loadPackages(userID, currentACL)
        phps = PHPManager.findPHPVersions()

        rnpss = randomPassword.generate_pass(10)

        Data = {'packageList': packagesName, "owernList": adminNames, 'phps': phps, 'Randam_String': rnpss.lower(),
                'test_domain_data': test_domain_status}
        proc = httpProc(request, 'websiteFunctions/createWebsite.html',
                        Data, 'createWebsite')
        return proc.render()

    def WPCreate(self, request=None, userID=None, data=None):
        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        data = {
            "name": "wp-manager",
            "IP": ACLManager.GetServerIP()
        }

        import requests
        response = requests.post(url, data=json.dumps(data))
        Status = response.json()['status']


        if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
            currentACL = ACLManager.loadedACL(userID)
            adminNames = ACLManager.loadAllUsers(userID)
            packagesName = ACLManager.loadPackages(userID, currentACL)

            if len(packagesName) == 0:
                packagesName = ['Default']

            FinalVersions = []
            userobj = Administrator.objects.get(pk=userID)
            counter = 0
            try:
                import requests
                WPVersions = json.loads(requests.get('https://api.wordpress.org/core/version-check/1.7/').text)[
                    'offers']

                for versions in WPVersions:
                    if counter == 7:
                        break
                    if versions['current'] not in FinalVersions:
                        FinalVersions.append(versions['current'])
                        counter = counter + 1
            except:
                FinalVersions = ['5.6', '5.5.3', '5.5.2']

            Plugins = wpplugins.objects.filter(owner=userobj)
            rnpss = randomPassword.generate_pass(10)

            ##

            test_domain_status = 1

            Data = {'packageList': packagesName, "owernList": adminNames, 'WPVersions': FinalVersions,
                    'Plugins': Plugins, 'Randam_String': rnpss.lower(), 'test_domain_data': test_domain_status}
            proc = httpProc(request, 'websiteFunctions/WPCreate.html',
                            Data, 'createDatabase')
            return proc.render()
        else:
            from django.shortcuts import reverse
            return redirect(reverse('pricing'))

    def ListWPSites(self, request=None, userID=None, DeleteID=None):
        import json
        currentACL = ACLManager.loadedACL(userID)

        admin = Administrator.objects.get(pk=userID)
        data = {}
        wp_sites = ACLManager.GetALLWPObjects(currentACL, userID)
        data['wp'] = wp_sites

        try:
            if DeleteID != None:
                WPDelete = WPSites.objects.get(pk=DeleteID)

                if ACLManager.checkOwnership(WPDelete.owner.domain, admin, currentACL) == 1:
                    # Check if this is a staging site (referenced by WPStaging as wpsite)
                    staging_records = WPStaging.objects.filter(wpsite=WPDelete)

                    if staging_records.exists():
                        # This is a staging site - perform complete cleanup
                        staging_website = WPDelete.owner

                        # Use the same robust deletion method as regular websites
                        execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                        execPath = execPath + " deleteVirtualHostConfigurations --virtualHostName " + staging_website.domain
                        ProcessUtilities.popenExecutioner(execPath)

                        # Delete all staging records
                        staging_records.delete()  # Delete WPStaging records
                        WPDelete.delete()         # Delete WPSites record
                        staging_website.delete()  # Delete Websites record
                    else:
                        # Regular WP site deletion
                        WPDelete.delete()
        except BaseException as msg:
            pass

        sites = []
        for site in data['wp']:
            sites.append({
                'id': site.id,
                'title': site.title,
                'url': site.FinalURL,
                'production_status': True
            })

        context = {
            "wpsite": json.dumps(sites),
            "status": 1,
            "total_sites": len(sites),
            "debug_info": json.dumps({
                "user_id": userID,
                "is_admin": bool(currentACL.get('admin', 0)),
                "wp_sites_count": wp_sites.count()
            })
        }

        proc = httpProc(request, 'websiteFunctions/WPsitesList.html', context)
        return proc.render()

    def WPHome(self, request=None, userID=None, WPid=None, DeleteID=None):
        Data = {}
        currentACL = ACLManager.loadedACL(userID)
        WPobj = WPSites.objects.get(pk=WPid)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(WPobj.owner.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        try:

            url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
            data = {
                "name": "wp-manager",
                "IP": ACLManager.GetServerIP()
            }

            import requests
            response = requests.post(url, data=json.dumps(data))
            Status = response.json()['status']

            rnpss = randomPassword.generate_pass(10)

            Data['Randam_String'] = rnpss.lower()

            if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
                Data['wpsite'] = WPobj
                Data['test_domain_data'] = 1

                try:
                    DeleteID = request.GET.get('DeleteID', None)

                    if DeleteID != None:
                        wstagingDelete = WPStaging.objects.get(pk=DeleteID, owner=WPobj)

                        # Get the associated staging WPSites and Websites records
                        staging_wpsite = wstagingDelete.wpsite
                        staging_website = staging_wpsite.owner

                        # Delete the staging Websites record and all associated data BEFORE deleting DB records
                        # Use the same robust deletion method as regular websites
                        execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                        execPath = execPath + " deleteVirtualHostConfigurations --virtualHostName " + staging_website.domain
                        ProcessUtilities.popenExecutioner(execPath)

                        # Delete the WPStaging record
                        wstagingDelete.delete()

                        # Delete the staging WPSites record
                        staging_wpsite.delete()

                        # Delete the staging Websites record
                        staging_website.delete()

                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error cleaning up WP/Staging sites: {str(msg)}")

                proc = httpProc(request, 'websiteFunctions/WPsiteHome.html',
                                Data, 'createDatabase')
                return proc.render()
            else:
                from django.shortcuts import reverse
                return redirect(reverse('pricing'))
        except:
            proc = httpProc(request, 'websiteFunctions/WPsiteHome.html',
                            Data, 'createDatabase')
            return proc.render()

    def RestoreHome(self, request=None, userID=None, BackupID=None):
        Data = {}
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.CheckForPremFeature('wp-manager'):

            Data['backupobj'] = WPSitesBackup.objects.get(pk=BackupID)

            if ACLManager.CheckIPBackupObjectOwner(currentACL, Data['backupobj'], admin) == 1:
                pass
            else:
                return ACLManager.loadError()

            config = json.loads(Data['backupobj'].config)
            Data['FileName'] = config['name']
            try:
                Data['Backuptype'] = config['Backuptype']

                if Data['Backuptype'] == 'DataBase Backup' or Data['Backuptype'] == 'Website Backup':
                    Data['WPsites'] = [WPSites.objects.get(pk=Data['backupobj'].WPSiteID)]
                else:
                    Data['WPsites'] = ACLManager.GetALLWPObjects(currentACL, userID)

            except:
                Data['Backuptype'] = None
                Data['WPsites'] = ACLManager.GetALLWPObjects(currentACL, userID)

            proc = httpProc(request, 'websiteFunctions/WPRestoreHome.html',
                            Data, 'createDatabase')
            return proc.render()
        else:
            from django.shortcuts import reverse
            return redirect(reverse('pricing'))

    def RemoteBackupConfig(self, request=None, userID=None, DeleteID=None):
        Data = {}
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        try:
            if DeleteID != None:
                BackupconfigDelete = RemoteBackupConfig.objects.get(pk=DeleteID)
                BackupconfigDelete.delete()
        except:
            pass

        if ACLManager.CheckForPremFeature('wp-manager'):

            Data['WPsites'] = ACLManager.GetALLWPObjects(currentACL, userID)
            allcon = RemoteBackupConfig.objects.all()
            Data['backupconfigs'] = []
            for i in allcon:
                configr = json.loads(i.config)
                if i.configtype == "SFTP":
                    Data['backupconfigs'].append({
                        'id': i.pk,
                        'Type': i.configtype,
                        'HostName': configr['Hostname'],
                        'Path': configr['Path']
                    })
                elif i.configtype == "S3":
                    Provider = configr['Provider']
                    if Provider == "Backblaze":
                        Data['backupconfigs'].append({
                            'id': i.pk,
                            'Type': i.configtype,
                            'HostName': Provider,
                            'Path': configr['S3keyname']
                        })
                    else:
                        Data['backupconfigs'].append({
                            'id': i.pk,
                            'Type': i.configtype,
                            'HostName': Provider,
                            'Path': configr['S3keyname']
                        })

            proc = httpProc(request, 'websiteFunctions/RemoteBackupConfig.html',
                            Data, 'createDatabase')
            return proc.render()
        else:
            from django.shortcuts import reverse
            return redirect(reverse('pricing'))

    def BackupfileConfig(self, request=None, userID=None, RemoteConfigID=None, DeleteID=None):
        Data = {}
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        Data['RemoteConfigID'] = RemoteConfigID
        RemoteConfigobj = RemoteBackupConfig.objects.get(pk=RemoteConfigID)
        try:
            if DeleteID != None:
                RemoteBackupConfigDelete = RemoteBackupSchedule.objects.get(pk=DeleteID)
                RemoteBackupConfigDelete.delete()
        except:
            pass

        if ACLManager.CheckForPremFeature('wp-manager'):
            Data['WPsites'] = ACLManager.GetALLWPObjects(currentACL, userID)
            allsechedule = RemoteBackupSchedule.objects.filter(RemoteBackupConfig=RemoteConfigobj)
            Data['Backupschedule'] = []
            for i in allsechedule:
                lastrun = i.lastrun
                LastRun = time.strftime('%Y-%m-%d', time.localtime(float(lastrun)))
                Data['Backupschedule'].append({
                    'id': i.pk,
                    'Name': i.Name,
                    'RemoteConfiguration': i.RemoteBackupConfig.configtype,
                    'Retention': i.fileretention,
                    'Frequency': i.timeintervel,
                    'LastRun': LastRun
                })
            proc = httpProc(request, 'websiteFunctions/BackupfileConfig.html',
                            Data, 'createDatabase')
            return proc.render()
        else:
            from django.shortcuts import reverse
            return redirect(reverse('pricing'))

    def AddRemoteBackupsite(self, request=None, userID=None, RemoteScheduleID=None, DeleteSiteID=None):
        Data = {}
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        Data['RemoteScheduleID'] = RemoteScheduleID
        RemoteBackupScheduleobj = RemoteBackupSchedule.objects.get(pk=RemoteScheduleID)

        try:
            if DeleteSiteID != None:
                RemoteBackupsitesDelete = RemoteBackupsites.objects.get(pk=DeleteSiteID)
                RemoteBackupsitesDelete.delete()
        except:
            pass

        if ACLManager.CheckForPremFeature('wp-manager'):
            Data['WPsites'] = ACLManager.GetALLWPObjects(currentACL, userID)
            allRemoteBackupsites = RemoteBackupsites.objects.filter(owner=RemoteBackupScheduleobj)
            Data['RemoteBackupsites'] = []
            for i in allRemoteBackupsites:
                try:
                    wpsite = WPSites.objects.get(pk=i.WPsites)
                    Data['RemoteBackupsites'].append({
                        'id': i.pk,
                        'Title': wpsite.title,
                    })
                except:
                    pass
            proc = httpProc(request, 'websiteFunctions/AddRemoteBackupSite.html',
                            Data, 'createDatabase')
            return proc.render()
        else:
            from django.shortcuts import reverse
            return redirect(reverse('pricing'))

    def WordpressPricing(self, request=None, userID=None, ):
        Data = {}
        proc = httpProc(request, 'websiteFunctions/CyberpanelPricing.html', Data, 'createWebsite')
        return proc.render()

    def RestoreBackups(self, request=None, userID=None, DeleteID=None):
        Data = {}
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        data = {
            "name": "wp-manager",
            "IP": ACLManager.GetServerIP()
        }

        import requests
        response = requests.post(url, data=json.dumps(data))
        Status = response.json()['status']

        if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:

            backobj = WPSitesBackup.objects.filter(owner=admin).order_by('-id')

            # if ACLManager.CheckIPBackupObjectOwner(currentACL, backobj, admin) == 1:
            #     pass
            # else:
            #     return ACLManager.loadError()

            try:
                if DeleteID != None:
                    DeleteIDobj = WPSitesBackup.objects.get(pk=DeleteID)

                    if ACLManager.CheckIPBackupObjectOwner(currentACL, DeleteIDobj, admin) == 1:
                        config = DeleteIDobj.config
                        conf = json.loads(config)
                        FileName = conf['name']
                        command = "rm -r /home/backup/%s.tar.gz" % FileName
                        ProcessUtilities.executioner(command)
                        DeleteIDobj.delete()

            except BaseException as msg:
                pass
            Data['job'] = []

            for sub in backobj:
                try:
                    wpsite = WPSites.objects.get(pk=sub.WPSiteID)
                    web = wpsite.title
                except:
                    web = "Website Not Found"

                try:
                    config = sub.config
                    conf = json.loads(config)
                    Backuptype = conf['Backuptype']
                    BackupDestination = conf['BackupDestination']
                except:
                    Backuptype = "Backup type not exists"

                Data['job'].append({
                    'id': sub.id,
                    'title': web,
                    'Backuptype': Backuptype,
                    'BackupDestination': BackupDestination
                })

            proc = httpProc(request, 'websiteFunctions/RestoreBackups.html',
                            Data, 'createDatabase')
            return proc.render()
        else:
            from django.shortcuts import reverse
            return redirect(reverse('pricing'))

    def AutoLogin(self, request=None, userID=None):

        WPid = request.GET.get('id')
        currentACL = ACLManager.loadedACL(userID)
        WPobj = WPSites.objects.get(pk=WPid)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(WPobj.owner.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        from managePHP.phpManager import PHPManager

        php = PHPManager.getPHPString(WPobj.owner.phpSelection)
        FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)
        
        # Validate PHP binary exists before proceeding
        is_valid, error_msg, php_path = PHPManager.validatePHPInstallation(WPobj.owner.phpSelection)
        
        if not is_valid:
            # Try to fix PHP configuration
            fix_success, fix_msg = PHPManager.fixPHPConfiguration(WPobj.owner.phpSelection)
            if fix_success:
                # Re-validate after fix attempt
                is_valid, error_msg, php_path = PHPManager.validatePHPInstallation(WPobj.owner.phpSelection)
            
            if not is_valid:
                # Return error page if no PHP binary found
                from django.shortcuts import render
                return render(request, 'websiteFunctions/error.html', {
                    'error_message': f'PHP configuration issue: {error_msg}. Fix attempt: {fix_msg}'
                })
            else:
                FinalPHPPath = php_path
        else:
            FinalPHPPath = php_path

        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        data = {
            "name": "wp-manager",
            "IP": ACLManager.GetServerIP()
        }

        import requests
        response = requests.post(url, data=json.dumps(data))
        Status = response.json()['status']

        if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:

            ## Get title

            password = randomPassword.generate_pass(10)

            command = f'sudo -u %s {FinalPHPPath} /usr/bin/wp user create autologin %s --role=administrator --user_pass="%s" --path=%s --skip-plugins --skip-themes' % (
                WPobj.owner.externalApp, 'autologin@cloudpages.cloud', password, WPobj.path)
            ProcessUtilities.executioner(command)

            command = f'sudo -u %s {FinalPHPPath} /usr/bin/wp user update autologin --user_pass="%s" --path=%s --skip-plugins --skip-themes' % (
                WPobj.owner.externalApp, password, WPobj.path)
            ProcessUtilities.executioner(command)

            data = {}

            if WPobj.FinalURL.endswith('/'):
                FinalURL = WPobj.FinalURL[:-1]
            else:
                FinalURL = WPobj.FinalURL

            data['url'] = 'https://%s' % (FinalURL)
            data['userName'] = 'autologin'
            data['password'] = password

            proc = httpProc(request, 'websiteFunctions/AutoLogin.html',
                            data, 'createDatabase')
            return proc.render()
        else:
            from django.shortcuts import reverse
            return redirect(reverse('pricing'))

    def ConfigurePlugins(self, request=None, userID=None, data=None):

        if ACLManager.CheckForPremFeature('wp-manager'):
            currentACL = ACLManager.loadedACL(userID)
            userobj = Administrator.objects.get(pk=userID)

            Selectedplugins = wpplugins.objects.filter(owner=userobj)
            # data['Selectedplugins'] = wpplugins.objects.filter(ProjectOwner=HostingCompany)

            Data = {'Selectedplugins': Selectedplugins, }
            proc = httpProc(request, 'websiteFunctions/WPConfigurePlugins.html',
                            Data, 'createDatabase')
            return proc.render()
        else:
            from django.shortcuts import reverse
            return redirect(reverse('pricing'))

    def Addnewplugin(self, request=None, userID=None, data=None):
        from django.shortcuts import reverse
        if ACLManager.CheckForPremFeature('wp-manager'):
            currentACL = ACLManager.loadedACL(userID)
            adminNames = ACLManager.loadAllUsers(userID)
            packagesName = ACLManager.loadPackages(userID, currentACL)
            phps = PHPManager.findPHPVersions()

            Data = {'packageList': packagesName, "owernList": adminNames, 'phps': phps}
            proc = httpProc(request, 'websiteFunctions/WPAddNewPlugin.html',
                            Data, 'createDatabase')
            return proc.render()

        return redirect(reverse('pricing'))

    def SearchOnkeyupPlugin(self, userID=None, data=None):
        try:
            if ACLManager.CheckForPremFeature('wp-manager'):
                currentACL = ACLManager.loadedACL(userID)

                pluginname = data['pluginname']
                # logging.CyberCPLogFileWriter.writeToFile("Plugin Name ....... %s"%pluginname)

                url = "http://api.wordpress.org/plugins/info/1.1/?action=query_plugins&request[search]=%s" % str(
                    pluginname)
                import requests

                res = requests.get(url)
                r = res.json()

                # return proc.ajax(1, 'Done', {'plugins': r})

                data_ret = {'status': 1, 'plugns': r, }

                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': 'Premium feature not available.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def AddNewpluginAjax(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            userobj = Administrator.objects.get(pk=userID)

            config = data['config']
            Name = data['Name']
            # pluginname = data['pluginname']
            # logging.CyberCPLogFileWriter.writeToFile("config ....... %s"%config)
            # logging.CyberCPLogFileWriter.writeToFile(" Name ....... %s"%Name)

            addpl = wpplugins(Name=Name, config=json.dumps(config), owner=userobj)
            addpl.save()

            data_ret = {'status': 1}

            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'AddNewpluginAjax': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def EidtPlugin(self, request=None, userID=None, pluginbID=None):
        Data = {}
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        pluginobj = wpplugins.objects.get(pk=pluginbID)

        if ACLManager.CheckIPPluginObjectOwner(currentACL, pluginobj, admin) == 1:
            pass
        else:
            return ACLManager.loadError()

        lmo = json.loads(pluginobj.config)
        Data['Selectedplugins'] = lmo
        Data['pluginbID'] = pluginbID
        Data['BucketName'] = pluginobj.Name

        proc = httpProc(request, 'websiteFunctions/WPEidtPlugin.html',
                        Data, 'createDatabase')
        return proc.render()

    def deletesPlgin(self, userID=None, data=None, ):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            userobj = Administrator.objects.get(pk=userID)
            pluginname = data['pluginname']
            pluginbBucketID = data['pluginbBucketID']
            # logging.CyberCPLogFileWriter.writeToFile("pluginbID ....... %s" % pluginbBucketID)
            # logging.CyberCPLogFileWriter.writeToFile("pluginname ....... %s" % pluginname)

            obj = wpplugins.objects.get(pk=pluginbBucketID, owner=userobj)

            if ACLManager.CheckIPPluginObjectOwner(currentACL, obj, admin) == 1:
                pass
            else:
                return ACLManager.loadError()

            ab = []
            ab = json.loads(obj.config)
            ab.remove(pluginname)
            obj.config = json.dumps(ab)
            obj.save()

            data_ret = {'status': 1}

            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'status': 0, 'deletesPlgin': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def Addplugineidt(self, userID=None, data=None, ):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            userobj = Administrator.objects.get(pk=userID)
            pluginname = data['pluginname']
            pluginbBucketID = data['pluginbBucketID']

            # logging.CyberCPLogFileWriter.writeToFile("pluginbID ....... %s" % pluginbBucketID)
            # logging.CyberCPLogFileWriter.writeToFile("pluginname ....... %s" % pluginname)

            pObj = wpplugins.objects.get(pk=pluginbBucketID, owner=userobj)

            if ACLManager.CheckIPPluginObjectOwner(currentACL, pObj, admin) == 1:
                pass
            else:
                return ACLManager.loadError()

            listofplugin = json.loads(pObj.config)
            try:
                index = listofplugin.index(pluginname)
                print('index.....%s' % index)
                if (index >= 0):
                    data_ret = {'status': 0, 'deletesPlgin': 0, 'error_message': str('Already Save in your Plugin lis')}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

            except:
                ab = []
                ab = json.loads(pObj.config)
                ab.append(pluginname)
                pObj.config = json.dumps(ab)
                pObj.save()

            data_ret = {'status': 1}

            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'status': 0, 'deletesPlgin': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def modifyWebsite(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)

        websitesName = ACLManager.findAllSites(currentACL, userID)
        phps = PHPManager.findPHPVersions()
        proc = httpProc(request, 'websiteFunctions/modifyWebsite.html',
                        {'websiteList': websitesName, 'phps': phps}, 'modifyWebsite')
        return proc.render()

    def deleteWebsite(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        websitesName = ACLManager.findAllSites(currentACL, userID)
        proc = httpProc(request, 'websiteFunctions/deleteWebsite.html',
                        {'websiteList': websitesName}, 'deleteWebsite')
        return proc.render()

    def CreateNewDomain(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        websitesName = ACLManager.findAllSites(currentACL, userID)

        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.defaultSite == 0:
                websites = ACLManager.findWebsiteObjects(currentACL, userID)
                admin.defaultSite = websites[0].id
                admin.save()
        except:
            pass

        try:
            admin = Administrator.objects.get(pk=userID)
            defaultDomain = Websites.objects.get(pk=admin.defaultSite).domain
        except:
            try:
                admin = Administrator.objects.get(pk=userID)
                websites = ACLManager.findWebsiteObjects(currentACL, userID)
                admin.defaultSite = websites[0].id
                admin.save()
                defaultDomain = websites[0].domain
            except:
                defaultDomain='NONE'


        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        data = {
            "name": "all",
            "IP": ACLManager.GetServerIP()
        }

        import requests
        response = requests.post(url, data=json.dumps(data))
        Status = response.json()['status']

        test_domain_status = 0

        if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
            test_domain_status = 1

        rnpss = randomPassword.generate_pass(10)
        proc = httpProc(request, 'websiteFunctions/createDomain.html',
                        {'websiteList': websitesName, 'phps': PHPManager.findPHPVersions(), 'Randam_String': rnpss,
                         'test_domain_data': test_domain_status, 'defaultSite': defaultDomain})
        return proc.render()

    def siteState(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)

        websitesName = ACLManager.findAllSites(currentACL, userID)

        proc = httpProc(request, 'websiteFunctions/suspendWebsite.html',
                        {'websiteList': websitesName}, 'suspendWebsite')
        return proc.render()

    def listWebsites(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        pagination = self.websitePagination(currentACL, userID)
        proc = httpProc(request, 'websiteFunctions/listWebsites.html',
                        {"pagination": pagination})
        return proc.render()

    def listChildDomains(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        adminNames = ACLManager.loadAllUsers(userID)
        packagesName = ACLManager.loadPackages(userID, currentACL)
        phps = PHPManager.findPHPVersions()

        Data = {'packageList': packagesName, "owernList": adminNames, 'phps': phps}
        proc = httpProc(request, 'websiteFunctions/listChildDomains.html',
                        Data)
        return proc.render()

    def listCron(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(request.GET.get('domain'), admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        proc = httpProc(request, 'websiteFunctions/listCron.html',
                        {'domain': request.GET.get('domain')})
        return proc.render()

    def domainAlias(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        aliasManager = AliasManager(self.domain)
        noAlias, finalAlisList = aliasManager.fetchAlisForDomains()

        path = "/home/" + self.domain + "/public_html"

        proc = httpProc(request, 'websiteFunctions/domainAlias.html', {
            'masterDomain': self.domain,
            'aliases': finalAlisList,
            'path': path,
            'noAlias': noAlias
        })
        return proc.render()

    def FetchWPdata(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            path = wpsite.path

            Webobj = Websites.objects.get(pk=wpsite.owner_id)

            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection

            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)
            
            # Validate PHP binary exists before proceeding
            from managePHP.phpManager import PHPManager
            is_valid, error_msg, php_path = PHPManager.validatePHPInstallation(PHPVersion)
            
            if not is_valid:
                # Try to fix PHP configuration
                fix_success, fix_msg = PHPManager.fixPHPConfiguration(PHPVersion)
                if fix_success:
                    # Re-validate after fix attempt
                    is_valid, error_msg, php_path = PHPManager.validatePHPInstallation(PHPVersion)
                
                if not is_valid:
                    final_json = json.dumps({
                        'status': 0, 
                        'error_message': f'PHP configuration issue: {error_msg}. Fix attempt: {fix_msg}'
                    })
                    return HttpResponse(final_json)
                else:
                    FinalPHPPath = php_path
            else:
                FinalPHPPath = php_path

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp core version --skip-plugins --skip-themes --path=%s 2>/dev/null' % (
                Vhuser, FinalPHPPath, path)
            version = ProcessUtilities.outputExecutioner(command, None, True)
            version = html.escape(version)

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin status litespeed-cache --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, path)
            lscachee = ProcessUtilities.outputExecutioner(command)

            # Get current theme
            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme list --status=active --field=name --skip-plugins --skip-themes --path=%s 2>/dev/null' % (
                Vhuser, FinalPHPPath, path)
            currentTheme = ProcessUtilities.outputExecutioner(command, None, True)
            currentTheme = currentTheme.strip()

            # Get number of plugins
            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin list --field=name --skip-plugins --skip-themes --path=%s 2>/dev/null' % (
                Vhuser, FinalPHPPath, path)
            plugins = ProcessUtilities.outputExecutioner(command, None, True)
            pluginCount = len([p for p in plugins.split('\n') if p.strip()])


            if lscachee.find('Status: Active') > -1:
                lscache = 1
            else:
                lscache = 0

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp config list --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, path)
            stdout = ProcessUtilities.outputExecutioner(command)
            debugging = 0
            for items in stdout.split('\n'):
                if items.find('WP_DEBUG	true	constant') > -1:
                    debugging = 1
                    break

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp option get blog_public --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, path)
            stdoutput = ProcessUtilities.outputExecutioner(command)
            searchindex = int(stdoutput.splitlines()[-1])

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp maintenance-mode status --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, path)
            maintenanceMod = ProcessUtilities.outputExecutioner(command)

            

            result = maintenanceMod.splitlines()[-1]
            if result.find('not active') > -1:
                maintenanceMode = 0
            else:
                maintenanceMode = 1

            ##### Check passwd protection
            vhostName = wpsite.owner.domain
            vhostPassDir = f'/home/{vhostName}'
            path = f'{vhostPassDir}/{WPManagerID}'
            if os.path.exists(path):
                passwd = 1
            else:
                passwd = 0

            #### Check WP cron
            command = "sudo -u %s cat %s/wp-config.php" % (Vhuser, wpsite.path)
            stdout = ProcessUtilities.outputExecutioner(command)
            if stdout.find("'DISABLE_WP_CRON', 'true'") > -1:
                wpcron = 1
            else:
                wpcron = 0

            fb = {
                'version': version.rstrip('\n'),
                'lscache': lscache,
                'debugging': debugging,
                'searchIndex': searchindex,
                'maintenanceMode': maintenanceMode,
                'passwordprotection': passwd,
                'wpcron': wpcron,
                'theme': currentTheme,
                'activePlugins': pluginCount,
                'phpVersion': wpsite.owner.phpSelection

            }

            data_ret = {'status': 1, 'error_message': 'None', 'ret_data': fb}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def GetCurrentPlugins(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            path = wpsite.path

            Webobj = Websites.objects.get(pk=wpsite.owner_id)

            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection
            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin list --skip-plugins --skip-themes --format=json --path=%s' % (
                Vhuser, FinalPHPPath, path)
            stdoutput = ProcessUtilities.outputExecutioner(command)
            json_data = stdoutput.splitlines()[-1]

            data_ret = {'status': 1, 'error_message': 'None', 'plugins': json_data}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def GetCurrentThemes(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            path = wpsite.path

            Webobj = Websites.objects.get(pk=wpsite.owner_id)

            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection
            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme list --skip-plugins --skip-themes --format=json --path=%s' % (
                Vhuser, FinalPHPPath, path)
            stdoutput = ProcessUtilities.outputExecutioner(command)
            json_data = stdoutput.splitlines()[-1]

            data_ret = {'status': 1, 'error_message': 'None', 'themes': json_data}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchstaging(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            from plogical.phpUtilities import phpUtilities

            json_data = phpUtilities.GetStagingInJson(wpsite.wpstaging_set.all().order_by('-id'))

            data_ret = {'status': 1, 'error_message': 'None', 'wpsites': json_data}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchDatabase(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            php = PHPManager.getPHPString(wpsite.owner.phpSelection)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp config get DB_NAME  --skip-plugins --skip-themes --path={wpsite.path} 2>/dev/null'
            retStatus, stdoutput = ProcessUtilities.outputExecutioner(command, wpsite.owner.externalApp, True, None, 1)

            if stdoutput.find('Error:') == -1:
                DataBaseName = stdoutput.rstrip("\n")
                DataBaseName = html.escape(DataBaseName)
            else:
                data_ret = {'status': 0, 'error_message': stdoutput}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp config get DB_USER  --skip-plugins --skip-themes --path={wpsite.path} 2>/dev/null'
            retStatus, stdoutput = ProcessUtilities.outputExecutioner(command, wpsite.owner.externalApp, True, None, 1)

            if stdoutput.find('Error:') == -1:
                DataBaseUser = stdoutput.rstrip("\n")
                DataBaseUser = html.escape(DataBaseUser)
            else:
                data_ret = {'status': 0, 'error_message': stdoutput}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp config get table_prefix  --skip-plugins --skip-themes --path={wpsite.path} 2>/dev/null'
            retStatus, stdoutput = ProcessUtilities.outputExecutioner(command, wpsite.owner.externalApp, True, None, 1)

            if stdoutput.find('Error:') == -1:
                tableprefix = stdoutput.rstrip("\n")
                tableprefix = html.escape(tableprefix)
            else:
                data_ret = {'status': 0, 'error_message': stdoutput}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'status': 1, 'error_message': 'None', "DataBaseUser": DataBaseUser,
                        "DataBaseName": DataBaseName, 'tableprefix': tableprefix}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def SaveUpdateConfig(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            Plugins = data['Plugins']
            Themes = data['Themes']
            AutomaticUpdates = data['AutomaticUpdates']

            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()


            php = PHPManager.getPHPString(wpsite.owner.phpSelection)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            if AutomaticUpdates == 'Disabled':
                command = f"{FinalPHPPath} -d error_reporting=0 /usr/bin/wp config set WP_AUTO_UPDATE_CORE false --raw --allow-root --path=" + wpsite.path
                result = ProcessUtilities.outputExecutioner(command, wpsite.owner.externalApp)

                if result.find('Success:') == -1:
                    raise BaseException(result)
            elif AutomaticUpdates == 'Minor and Security Updates':
                command = f"{FinalPHPPath} -d error_reporting=0 /usr/bin/wp config set WP_AUTO_UPDATE_CORE minor --allow-root --path=" + wpsite.path
                result = ProcessUtilities.outputExecutioner(command, wpsite.owner.externalApp)

                if result.find('Success:') == -1:
                    raise BaseException(result)
            else:
                command = f"{FinalPHPPath} -d error_reporting=0 /usr/bin/wp config set WP_AUTO_UPDATE_CORE true --raw --allow-root --path=" + wpsite.path
                result = ProcessUtilities.outputExecutioner(command, wpsite.owner.externalApp)

                if result.find('Success:') == -1:
                    raise BaseException(result)

            wpsite.AutoUpdates = AutomaticUpdates
            wpsite.PluginUpdates = Plugins
            wpsite.ThemeUpdates = Themes
            wpsite.save()

            data_ret = {'status': 1, 'error_message': 'None', }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def DeploytoProduction(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            statgingID = data['StagingID']
            wpsite = WPSites.objects.get(pk=WPManagerID)
            StagingObj = WPSites.objects.get(pk=statgingID)

            ###

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            if ACLManager.checkOwnership(StagingObj.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            ###

            extraArgs = {}
            extraArgs['adminID'] = admin.pk
            extraArgs['statgingID'] = statgingID
            extraArgs['WPid'] = WPManagerID
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            background = ApplicationInstaller('DeploytoProduction', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def WPCreateBackup(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            Backuptype = data['Backuptype']

            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            extraArgs = {}
            extraArgs['adminID'] = admin.pk
            extraArgs['WPid'] = WPManagerID
            extraArgs['Backuptype'] = Backuptype
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            background = ApplicationInstaller('WPCreateBackup', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def RestoreWPbackupNow(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            backupid = data['backupid']
            DesSiteID = data['DesSite']

            # try:
            #
            #     bwp = WPSites.objects.get(pk=int(backupid))
            #
            #     if ACLManager.checkOwnership(bwp.owner.domain, admin, currentACL) == 1:
            #         pass
            #     else:
            #         return ACLManager.loadError()
            #
            # except:
            #     pass
            #
            # dwp = WPSites.objects.get(pk=int(DesSiteID))
            # if ACLManager.checkOwnership(dwp.owner.domain, admin, currentACL) == 1:
            #     pass
            # else:
            #     return ACLManager.loadError()

            Domain = data['Domain']

            extraArgs = {}
            extraArgs['adminID'] = admin.pk
            extraArgs['backupid'] = backupid
            extraArgs['DesSiteID'] = DesSiteID
            extraArgs['Domain'] = Domain
            extraArgs['path'] = data['path']
            extraArgs['home'] = data['home']
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            background = ApplicationInstaller('RestoreWPbackupNow', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def SaveBackupConfig(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            ConfigType = data['type']
            if ConfigType == 'SFTP':
                Hname = data['Hname']
                Uname = data['Uname']
                Passwd = data['Passwd']
                path = data['path']
                config = {
                    "Hostname": Hname,
                    "Username": Uname,
                    "Password": Passwd,
                    "Path": path
                }
            elif ConfigType == "S3":
                Provider = data['Provider']
                if Provider == "Backblaze":
                    S3keyname = data['S3keyname']
                    SecertKey = data['SecertKey']
                    AccessKey = data['AccessKey']
                    EndUrl = data['EndUrl']
                    config = {
                        "Provider": Provider,
                        "S3keyname": S3keyname,
                        "SecertKey": SecertKey,
                        "AccessKey": AccessKey,
                        "EndUrl": EndUrl

                    }
                else:
                    S3keyname = data['S3keyname']
                    SecertKey = data['SecertKey']
                    AccessKey = data['AccessKey']
                    config = {
                        "Provider": Provider,
                        "S3keyname": S3keyname,
                        "SecertKey": SecertKey,
                        "AccessKey": AccessKey,

                    }

            mkobj = RemoteBackupConfig(owner=admin, configtype=ConfigType, config=json.dumps(config))
            mkobj.save()

            time.sleep(1)

            data_ret = {'status': 1, 'error_message': 'None', }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def SaveBackupSchedule(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            FileRetention = data['FileRetention']
            Backfrequency = data['Backfrequency']
            ScheduleName = data['ScheduleName']
            RemoteConfigID = data['RemoteConfigID']
            BackupType = data['BackupType']

            RemoteBackupConfigobj = RemoteBackupConfig.objects.get(pk=RemoteConfigID)
            Rconfig = json.loads(RemoteBackupConfigobj.config)

            try:
                # This code is only supposed to run if backups are s3, not for SFTP
                provider = Rconfig['Provider']
                if provider == "Backblaze":
                    EndURl = Rconfig['EndUrl']
                elif provider == "Amazon":
                    EndURl = "https://s3.us-east-1.amazonaws.com"
                elif provider == "Wasabi":
                    EndURl = "https://s3.wasabisys.com"

                AccessKey = Rconfig['AccessKey']
                SecertKey = Rconfig['SecertKey']

                session = boto3.session.Session()

                client = session.client(
                    's3',
                    endpoint_url=EndURl,
                    aws_access_key_id=AccessKey,
                    aws_secret_access_key=SecertKey,
                    verify=False
                )

                ############Creating Bucket
                BucketName = randomPassword.generate_pass().lower()

                try:
                    client.create_bucket(Bucket=BucketName)
                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile("Creating Bucket Error: %s" % str(msg))
                    data_ret = {'status': 0, 'error_message': str(msg)}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                config = {
                    'BackupType': BackupType,
                    'BucketName': BucketName
                }
            except BaseException as msg:
                config = {'BackupType': BackupType}
                pass

            svobj = RemoteBackupSchedule(RemoteBackupConfig=RemoteBackupConfigobj, Name=ScheduleName,
                                         timeintervel=Backfrequency, fileretention=FileRetention,
                                         config=json.dumps(config),
                                         lastrun=str(time.time()))
            svobj.save()

            data_ret = {'status': 1, 'error_message': 'None', }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def AddWPsiteforRemoteBackup(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            WPid = data['WpsiteID']
            RemoteScheduleID = data['RemoteScheduleID']

            wpsiteobj = WPSites.objects.get(pk=WPid)
            WPpath = wpsiteobj.path
            VHuser = wpsiteobj.owner.externalApp
            PhpVersion = wpsiteobj.owner.phpSelection
            php = PHPManager.getPHPString(PhpVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            ####Get DB Name

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp config get DB_NAME  --skip-plugins --skip-themes --path=%s' % (
                VHuser, FinalPHPPath, WPpath)
            result, stdout = ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            if stdout.find('Error:') > -1:
                raise BaseException(stdout)
            else:
                Finaldbname = stdout.rstrip("\n")

            ## Get DB obj
            try:
                DBobj = Databases.objects.get(dbName=Finaldbname)
            except:
                raise BaseException(str("DataBase Not Found"))
            RemoteScheduleIDobj = RemoteBackupSchedule.objects.get(pk=RemoteScheduleID)

            svobj = RemoteBackupsites(owner=RemoteScheduleIDobj, WPsites=WPid, database=DBobj.pk)
            svobj.save()

            data_ret = {'status': 1, 'error_message': 'None', }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def UpdateRemoteschedules(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            ScheduleID = data['ScheduleID']
            Frequency = data['Frequency']
            FileRetention = data['FileRetention']

            scheduleobj = RemoteBackupSchedule.objects.get(pk=ScheduleID)
            scheduleobj.timeintervel = Frequency
            scheduleobj.fileretention = FileRetention
            scheduleobj.save()

            data_ret = {'status': 1, 'error_message': 'None', }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def ScanWordpressSite(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            allweb = Websites.objects.all()

            childdomain = ChildDomains.objects.all()

            for web in allweb:
                webpath = "/home/%s/public_html/" % web.domain
                command = "cat %swp-config.php" % webpath
                result = ProcessUtilities.outputExecutioner(command, web.externalApp)

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(result)

                if result.find('No such file or directory') == -1:
                    try:
                        WPSites.objects.get(path=webpath)
                    except:
                        wpobj = WPSites(owner=web, title=web.domain, path=webpath, FinalURL=web.domain,
                                        AutoUpdates="Enabled", PluginUpdates="Enabled",
                                        ThemeUpdates="Enabled", )
                        wpobj.save()

            for chlid in childdomain:
                childPath = chlid.path.rstrip('/')

                command = "cat %s/wp-config.php" % childPath
                result = ProcessUtilities.outputExecutioner(command, chlid.master.externalApp)

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(result)

                if result.find('No such file or directory') == -1:
                    fChildPath = f'{childPath}/'
                    try:
                        WPSites.objects.get(path=fChildPath)
                    except:

                        wpobj = WPSites(owner=chlid.master, title=chlid.domain, path=fChildPath, FinalURL=chlid.domain,
                                        AutoUpdates="Enabled", PluginUpdates="Enabled",
                                        ThemeUpdates="Enabled", )
                        wpobj.save()

            data_ret = {'status': 1, 'error_message': 'None', }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def installwpcore(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            path = wpsite.path

            Webobj = Websites.objects.get(pk=wpsite.owner_id)

            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection

            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            ###fetch WP version

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp core version --skip-plugins --skip-themes --path=%s 2>/dev/null' % (
                Vhuser, FinalPHPPath, path)
            version = ProcessUtilities.outputExecutioner(command, None, True)
            version = version.rstrip("\n")

            ###install wp core
            command = f"sudo -u {Vhuser} {FinalPHPPath} -d error_reporting=0 /usr/bin/wp core download --force --skip-content --version={version} --path={path}"
            output = ProcessUtilities.outputExecutioner(command)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None', 'result': output}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def dataintegrity(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            path = wpsite.path

            Webobj = Websites.objects.get(pk=wpsite.owner_id)

            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection

            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            ###fetch WP version

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp core verify-checksums --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, path)
            result = ProcessUtilities.outputExecutioner(command)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None', 'result': result}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def UpdatePlugins(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            plugin = data['plugin']
            pluginarray = data['pluginarray']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            path = wpsite.path

            Webobj = Websites.objects.get(pk=wpsite.owner_id)

            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection
            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            extraArgs = {}
            extraArgs['adminID'] = admin.pk
            extraArgs['plugin'] = plugin
            extraArgs['pluginarray'] = pluginarray
            extraArgs['FinalPHPPath'] = FinalPHPPath
            extraArgs['path'] = path
            extraArgs['Vhuser'] = Vhuser

            background = ApplicationInstaller('UpdateWPPlugin', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def UpdateThemes(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            Theme = data['Theme']
            Themearray = data['Themearray']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            path = wpsite.path

            Webobj = Websites.objects.get(pk=wpsite.owner_id)

            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection
            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            extraArgs = {}
            extraArgs['adminID'] = admin.pk
            extraArgs['Theme'] = Theme
            extraArgs['Themearray'] = Themearray
            extraArgs['FinalPHPPath'] = FinalPHPPath
            extraArgs['path'] = path
            extraArgs['Vhuser'] = Vhuser

            background = ApplicationInstaller('UpdateWPTheme', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def DeletePlugins(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            plugin = data['plugin']
            pluginarray = data['pluginarray']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            path = wpsite.path

            Webobj = Websites.objects.get(pk=wpsite.owner_id)

            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection
            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            extraArgs = {}
            extraArgs['adminID'] = admin.pk
            extraArgs['plugin'] = plugin
            extraArgs['pluginarray'] = pluginarray
            extraArgs['FinalPHPPath'] = FinalPHPPath
            extraArgs['path'] = path
            extraArgs['Vhuser'] = Vhuser

            background = ApplicationInstaller('DeletePlugins', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def DeleteThemes(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            Theme = data['Theme']
            Themearray = data['Themearray']
            wpsite = WPSites.objects.get(pk=WPManagerID)
            path = wpsite.path

            Webobj = Websites.objects.get(pk=wpsite.owner_id)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection
            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            extraArgs = {}
            extraArgs['adminID'] = admin.pk
            extraArgs['Theme'] = Theme
            extraArgs['Themearray'] = Themearray
            extraArgs['FinalPHPPath'] = FinalPHPPath
            extraArgs['path'] = path
            extraArgs['Vhuser'] = Vhuser

            background = ApplicationInstaller('DeleteThemes', extraArgs)
            background.start()

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def ChangeStatus(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            plugin = data['plugin']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            path = wpsite.path

            Webobj = Websites.objects.get(pk=wpsite.owner_id)

            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection
            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin status %s --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, plugin, path)
            stdoutput = ProcessUtilities.outputExecutioner(command)

            if stdoutput.find('Status: Active') > -1:
                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin deactivate %s --skip-plugins --skip-themes --path=%s' % (
                    Vhuser, FinalPHPPath, plugin, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)
                time.sleep(3)

            else:

                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin activate %s --skip-plugins --skip-themes --path=%s' % (
                    Vhuser, FinalPHPPath, plugin, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)
                time.sleep(3)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def ChangeStatusThemes(self, userID=None, data=None):
        try:
            # logging.CyberCPLogFileWriter.writeToFile("Error WP ChangeStatusThemes ....... %s")
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            Theme = data['theme']
            wpsite = WPSites.objects.get(pk=WPManagerID)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            path = wpsite.path

            Webobj = Websites.objects.get(pk=wpsite.owner_id)

            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection
            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            extraArgs = {}
            extraArgs['adminID'] = admin.pk
            extraArgs['Theme'] = Theme
            extraArgs['FinalPHPPath'] = FinalPHPPath
            extraArgs['path'] = path
            extraArgs['Vhuser'] = Vhuser

            background = ApplicationInstaller('ChangeStatusThemes', extraArgs)
            background.start()

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def CreateStagingNow(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            extraArgs = {}
            extraArgs['adminID'] = admin.pk
            extraArgs['StagingDomain'] = data['StagingDomain']
            extraArgs['StagingName'] = data['StagingName']
            extraArgs['WPid'] = data['WPid']
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            wpsite = WPSites.objects.get(pk=data['WPid'])

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            background = ApplicationInstaller('CreateStagingNow', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        
    def UpdateWPSettings(self, userID=None, data=None):
        # Map old setting names to new ones
        setting_map = {
            'PasswordProtection': 'password-protection',
            'searchIndex': 'search-indexing',
            'debugging': 'debugging',
            'maintenanceMode': 'maintenance-mode',
            'lscache': 'lscache',
            'Wpcron': 'wpcron',
            # Add more mappings as needed
        }

        siteId = data.get('siteId') or data.get('WPid')
        if not siteId:
            resp = {'status': 0, 'error_message': 'Missing siteId or WPid'}
            return JsonResponse(resp)

        # Accept both new and old setting names
        setting = data.get('setting')
        if not setting:
            for old_key in setting_map:
                if old_key in data:
                    setting = old_key
                    data['settingValue'] = data[old_key]
                    break

        # Map to new setting name if needed
        setting = setting_map.get(setting, setting)
        value = data.get('value') or data.get('settingValue')

        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            wpsite = WPSites.objects.get(pk=siteId)

            if ACLManager.checkOwnership(wpsite.owner.domain, admin, currentACL) != 1:
                return ACLManager.loadError()

            # Get PHP version and path
            Webobj = Websites.objects.get(pk=wpsite.owner_id)
            Vhuser = Webobj.externalApp
            PHPVersion = Webobj.phpSelection
            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

            # Update the appropriate setting based on the setting type
            if setting == 'search-indexing':
                command = f'sudo -u {Vhuser} {FinalPHPPath} -d error_reporting=0 /usr/bin/wp option update blog_public {value} --skip-plugins --skip-themes --path={wpsite.path}'
            elif setting == 'debugging':
                if value:
                    command = f'sudo -u {Vhuser} {FinalPHPPath} -d error_reporting=0 /usr/bin/wp config set WP_DEBUG true --raw --skip-plugins --skip-themes --path={wpsite.path}'
                else:
                    command = f'sudo -u {Vhuser} {FinalPHPPath} -d error_reporting=0 /usr/bin/wp config set WP_DEBUG false --raw --skip-plugins --skip-themes --path={wpsite.path}'
            elif setting == 'password-protection':
                vhostName = wpsite.owner.domain
                vhostPassDir = f'/home/{vhostName}'
                path = f'{vhostPassDir}/{siteId}'
                if value:
                    tempPath = f'/home/cyberpanel/{str(randint(1000, 9999))}'
                    os.makedirs(tempPath)
                    htpasswd = f'{tempPath}/.htpasswd'
                    htaccess = f'{tempPath}/.htaccess'
                    password = randomPassword.generate_pass(12)
                    command = f"htpasswd -cb {htpasswd} admin {password}"
                    ProcessUtilities.executioner(command)
                    htaccess_content = f"""
AuthType Basic
AuthName "Restricted Access"
AuthUserFile {path}/.htpasswd
Require valid-user
"""
                    with open(htaccess, 'w') as f:
                        f.write(htaccess_content)
                    command = f"mkdir -p {path}"
                    ProcessUtilities.executioner(command, wpsite.owner.externalApp)
                    command = f"mv {htpasswd} {path}/.htpasswd"
                    ProcessUtilities.executioner(command, wpsite.owner.externalApp)
                    command = f"mv {htaccess} {wpsite.path}/.htaccess"
                    ProcessUtilities.executioner(command, wpsite.owner.externalApp)
                    command = f"rm -rf {tempPath}"
                    ProcessUtilities.executioner(command)
                else:
                    if os.path.exists(path):
                        command = f"rm -rf {path}"
                        ProcessUtilities.executioner(command, wpsite.owner.externalApp)
                    htaccess = f'{wpsite.path}/.htaccess'
                    if os.path.exists(htaccess):
                        command = f"rm -f {htaccess}"
                        ProcessUtilities.executioner(command, wpsite.owner.externalApp)
                    resp = {'status': 1, 'error_message': 'None'}
                    if data.get('legacy_response'):
                        import json
                        return HttpResponse(json.dumps(resp))
                    else:
                        return JsonResponse(resp)
            elif setting == 'maintenance-mode':
                if value:
                    command = f'sudo -u {Vhuser} {FinalPHPPath} -d error_reporting=0 /usr/bin/wp maintenance-mode activate --skip-plugins --skip-themes --path={wpsite.path}'
                else:
                    command = f'sudo -u {Vhuser} {FinalPHPPath} -d error_reporting=0 /usr/bin/wp maintenance-mode deactivate --skip-plugins --skip-themes --path={wpsite.path}'
            elif setting == 'lscache':
                if value:
                    command = f'sudo -u {Vhuser} {FinalPHPPath} -d error_reporting=0 /usr/bin/wp plugin activate litespeed-cache --skip-plugins --skip-themes --path={wpsite.path}'
                else:
                    command = f'sudo -u {Vhuser} {FinalPHPPath} -d error_reporting=0 /usr/bin/wp plugin deactivate litespeed-cache --skip-plugins --skip-themes --path={wpsite.path}'
            else:
                resp = {'status': 0, 'error_message': 'Invalid setting type'}
                if data.get('legacy_response'):
                    import json
                    return HttpResponse(json.dumps(resp))
                else:
                    return JsonResponse(resp)

            result = ProcessUtilities.outputExecutioner(command)
            if result.find('Error:') > -1:
                resp = {'status': 0, 'error_message': result}
                if data.get('legacy_response'):
                    import json
                    return HttpResponse(json.dumps(resp))
                else:
                    return JsonResponse(resp)

            resp = {'status': 1, 'error_message': 'None'}
            if data.get('legacy_response'):
                import json
                return HttpResponse(json.dumps(resp))
            else:
                return JsonResponse(resp)

        except BaseException as msg:
            resp = {'status': 0, 'error_message': str(msg)}
            if data and data.get('legacy_response'):
                import json
                return HttpResponse(json.dumps(resp))
            else:
                return JsonResponse(resp)

    def submitWorpressCreation(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            extraArgs = {}
            extraArgs['currentACL'] = currentACL
            extraArgs['adminID'] = admin.pk
            extraArgs['domainName'] = data['domain']
            extraArgs['WPVersion'] = data['WPVersion']
            extraArgs['blogTitle'] = data['title']
            try:
                extraArgs['pluginbucket'] = data['pluginbucket']
            except:
                extraArgs['pluginbucket'] = '-1'
            extraArgs['adminUser'] = data['adminUser']
            extraArgs['PasswordByPass'] = data['PasswordByPass']
            extraArgs['adminPassword'] = data['PasswordByPass']
            extraArgs['adminEmail'] = data['Email']
            extraArgs['updates'] = data['AutomaticUpdates']
            extraArgs['Plugins'] = data['Plugins']
            extraArgs['Themes'] = data['Themes']
            extraArgs['websiteOwner'] = data['websiteOwner']
            extraArgs['package'] = data['package']
            extraArgs['home'] = data['home']
            extraArgs['apacheBackend'] = data['apacheBackend']
            try:
                extraArgs['path'] = data['path']
                if extraArgs['path'] == '':
                    extraArgs['home'] = '1'
            except:
                pass
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            background = ApplicationInstaller('wordpressInstallNew', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitWebsiteCreation(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            domain = data['domainName']
            adminEmail = data['adminEmail']
            phpSelection = data['phpSelection']
            packageName = data['package']
            websiteOwner = data['websiteOwner'].lower()

            if data['domainName'].find("cyberpanel.website") > -1:
                url = "https://platform.cyberpersons.com/CyberpanelAdOns/CreateDomain"

                domain_data = {
                    "name": "test-domain",
                    "IP": ACLManager.GetServerIP(),
                    "domain": data['domainName']
                }

                import requests
                response = requests.post(url, data=json.dumps(domain_data))
                domain_status = response.json()['status']

                if domain_status == 0:
                    data_ret = {'status': 0, 'installStatus': 0, 'error_message': response.json()['error_message']}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

            loggedUser = Administrator.objects.get(pk=userID)
            newOwner = Administrator.objects.get(userName=websiteOwner)

            if ACLManager.currentContextPermission(currentACL, 'createWebsite') == 0:
                return ACLManager.loadErrorJson('createWebSiteStatus', 0)

            if ACLManager.checkOwnerProtection(currentACL, loggedUser, newOwner) == 0:
                return ACLManager.loadErrorJson('createWebSiteStatus', 0)

            if currentACL['admin'] == 0:
                if ACLManager.CheckDomainBlackList(domain) == 0:
                    data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': "Blacklisted domain."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

            if not validators.domain(domain):
                data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': "Invalid domain."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if not validators.email(adminEmail) or adminEmail.find('--') > -1:
                data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': "Invalid email."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                HA = data['HA']
                externalApp = 'nobody'
            except:
                externalApp = "".join(re.findall("[a-zA-Z]+", domain))[:5] + str(randint(1000, 9999))

            try:
                counter = 0
                while 1:
                    tWeb = Websites.objects.get(externalApp=externalApp)
                    externalApp = '%s%s' % (tWeb.externalApp, str(counter))
                    counter = counter + 1
            except:
                pass

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            try:
                apacheBackend = str(data['apacheBackend'])
            except:
                apacheBackend = "0"

            try:
                mailDomain = str(data['mailDomain'])
            except:
                mailDomain = "1"

            import pwd
            counter = 0

            ## Create Configurations

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " createVirtualHost --virtualHostName " + domain + \
                       " --administratorEmail " + adminEmail + " --phpVersion '" + phpSelection + \
                       "' --virtualHostUser " + externalApp + " --ssl " + str(1) + " --dkimCheck " \
                       + str(1) + " --openBasedir " + str(data['openBasedir']) + \
                       ' --websiteOwner "' + websiteOwner + '" --package "' + packageName + '" --tempStatusPath ' + tempStatusPath + " --apache " + apacheBackend + " --mailDomain %s" % (
                           mailDomain)

            ProcessUtilities.popenExecutioner(execPath)
            time.sleep(2)

            data_ret = {'status': 1, 'createWebSiteStatus': 1, 'error_message': "None",
                        'tempStatusPath': tempStatusPath, 'LinuxUser': externalApp}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitDomainCreation(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            try:
                alias = data['alias']
            except:
                alias = 0

            masterDomain = data['masterDomain']
            domain = data['domainName']


            if alias == 0:
                phpSelection = data['phpSelection']
                path = data['path']
            else:

                ### if master website have apache then create this sub-domain also as ols + apache

                apachePath = ApacheVhost.configBasePath + masterDomain + '.conf'

                if os.path.exists(apachePath):
                    data['apacheBackend'] = 1

                phpSelection = Websites.objects.get(domain=masterDomain).phpSelection

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            if not validators.domain(domain):
                data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': "Invalid domain."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if data['domainName'].find("cyberpanel.website") > -1:
                url = "https://platform.cyberpersons.com/CyberpanelAdOns/CreateDomain"

                domain_data = {
                    "name": "test-domain",
                    "IP": ACLManager.GetServerIP(),
                    "domain": data['domainName']
                }

                import requests
                response = requests.post(url, data=json.dumps(domain_data))
                domain_status = response.json()['status']

                if domain_status == 0:
                    data_ret = {'status': 0, 'installStatus': 0, 'error_message': response.json()['error_message']}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

            if ACLManager.checkOwnership(masterDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('createWebSiteStatus', 0)

            if data['path'].find('..') > -1:
                return ACLManager.loadErrorJson('createWebSiteStatus', 0)

            if currentACL['admin'] != 1:
                data['openBasedir'] = 1

            if alias == 0:

                if len(path) > 0:
                    path = path.lstrip("/")
                    path = "/home/" + masterDomain + "/" + path
                else:
                    path = "/home/" + masterDomain + "/" + domain
            else:
                path = f'/home/{masterDomain}/public_html'

            try:
                apacheBackend = str(data['apacheBackend'])
            except:
                apacheBackend = "0"

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " createDomain --masterDomain " + masterDomain + " --virtualHostName " + domain + \
                       " --phpVersion '" + phpSelection + "' --ssl " + str(1) + " --dkimCheck " + str(1) \
                       + " --openBasedir " + str(data['openBasedir']) + ' --path ' + path + ' --websiteOwner ' \
                       + admin.userName + ' --tempStatusPath ' + tempStatusPath + " --apache " + apacheBackend + f' --aliasDomain {str(alias)}'

            ProcessUtilities.popenExecutioner(execPath)
            time.sleep(2)

            data_ret = {'status': 1, 'createWebSiteStatus': 1, 'error_message': "None",
                        'tempStatusPath': tempStatusPath}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchDomains(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            masterDomain = data['masterDomain']

            try:
                alias = data['alias']
            except:
                alias = 0

            if ACLManager.checkOwnership(masterDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            cdManager = ChildDomainManager(masterDomain)
            json_data = cdManager.findChildDomainsJson(alias)

            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def searchWebsites(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            try:
                json_data = self.searchWebsitesJson(currentACL, userID, data['patternAdded'])
            except BaseException as msg:
                tempData = {}
                tempData['page'] = 1
                return self.getFurtherAccounts(userID, tempData)

            pagination = self.websitePagination(currentACL, userID)
            final_dic = {'status': 1, 'listWebSiteStatus': 1, 'error_message': "None", "data": json_data,
                         'pagination': pagination}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException as msg:
            dic = {'status': 1, 'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def searchChilds(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            websites = ACLManager.findWebsiteObjects(currentACL, userID)
            childDomains = []

            for web in websites:
                for child in web.childdomains_set.filter(domain__istartswith=data['patternAdded']):
                    childDomains.append(child)

            json_data = self.findChildsListJson(childDomains)

            final_dic = {'status': 1, 'listWebSiteStatus': 1, 'error_message': "None", "data": json_data}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException as msg:
            dic = {'status': 1, 'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def getFurtherAccounts(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            pageNumber = int(data['page'])
            json_data = self.findWebsitesJson(currentACL, userID, pageNumber)
            pagination = self.websitePagination(currentACL, userID)
            final_dic = {'status': 1, 'listWebSiteStatus': 1, 'error_message': "None", "data": json_data,
                         'pagination': pagination}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException as msg:
            dic = {'status': 1, 'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def fetchWebsitesList(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            pageNumber = int(data['page'])
            recordsToShow = int(data['recordsToShow'])

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'Fetch sites step 1..')

            endPageNumber, finalPageNumber = self.recordsPointer(pageNumber, recordsToShow)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'Fetch sites step 2..')

            websites = ACLManager.findWebsiteObjects(currentACL, userID)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'Fetch sites step 3..')

            pagination = self.getPagination(len(websites), recordsToShow)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'Fetch sites step 4..')

            json_data = self.findWebsitesListJson(websites[finalPageNumber:endPageNumber])

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'Fetch sites step 5..')

            final_dic = {'status': 1, 'listWebSiteStatus': 1, 'error_message': "None", "data": json_data,
                         'pagination': pagination}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException as msg:
            dic = {'status': 1, 'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def fetchChildDomainsMain(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            pageNumber = int(data['page'])
            recordsToShow = int(data['recordsToShow'])

            endPageNumber, finalPageNumber = self.recordsPointer(pageNumber, recordsToShow)
            websites = ACLManager.findWebsiteObjects(currentACL, userID)
            childDomains = []

            for web in websites:
                for child in web.childdomains_set.all():
                    if child.alais == 0:
                        if child.domain == f'mail.{web.domain}':
                            pass
                        else:
                            childDomains.append(child)

            pagination = self.getPagination(len(childDomains), recordsToShow)
            json_data = self.findChildsListJson(childDomains[finalPageNumber:endPageNumber])

            final_dic = {'status': 1, 'listWebSiteStatus': 1, 'error_message': "None", "data": json_data,
                         'pagination': pagination}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException as msg:
            import traceback
            logging.CyberCPLogFileWriter.writeToFile(f"fetchChildDomainsMain error for userID {userID}: {str(msg)}\n{traceback.format_exc()}")
            dic = {'status': 1, 'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def findWebsitesListJson(self, websites):
        try:
            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to read machine IP, error:" + str(msg))
            ipAddress = "192.168.100.1"

        json_data = []

        for website in websites:
            wp_sites = []
            try:
                wp_sites = WPSites.objects.filter(owner=website)
                wp_sites = [{
                    'id': wp.id,
                    'title': wp.title,
                    'url': wp.FinalURL,
                    'version': wp.version if hasattr(wp, 'version') else 'Unknown',
                    'phpVersion': wp.phpVersion if hasattr(wp, 'phpVersion') else 'Unknown'
                } for wp in wp_sites]
            except:
                pass

            # Calculate disk usage
            DiskUsage, DiskUsagePercentage, bwInMB, bwUsage = virtualHostUtilities.FindStats(website)
            diskUsed = "%sMB" % str(DiskUsage)

            # Convert numeric state to text
            state = "Active" if website.state == 1 else "Suspended"

            # Get SSL status
            ssl_status = self.getSSLStatus(website.domain)

            json_data.append({
                'domain': website.domain,
                'adminEmail': website.adminEmail,
                'phpVersion': website.phpSelection,
                'state': state,
                'ipAddress': ipAddress,
                'package': website.package.packageName,
                'admin': website.admin.userName,
                'wp_sites': wp_sites,
                'diskUsed': diskUsed,
                'ssl': ssl_status
            })
        return json.dumps(json_data)

    def getSSLStatus(self, domain):
        """Get SSL status for a domain"""
        try:
            import OpenSSL
            from datetime import datetime
            
            # Check main domain certificate
            filePath = '/etc/letsencrypt/live/%s/fullchain.pem' % domain
            
            if not os.path.exists(filePath):
                # Check for wildcard certificate in parent domain
                parts = domain.split('.')
                if len(parts) > 2:  # Subdomain like mail.example.com or ftp.example.com
                    parent_domain = '.'.join(parts[-2:])
                    wildcard_path = '/etc/letsencrypt/live/%s/fullchain.pem' % parent_domain
                    if os.path.exists(wildcard_path):
                        # Check if it's actually a wildcard cert
                        try:
                            x509 = OpenSSL.crypto.load_certificate(
                                OpenSSL.crypto.FILETYPE_PEM,
                                open(wildcard_path, 'r').read()
                            )
                            cn = None
                            for component in x509.get_subject().get_components():
                                if component[0].decode('utf-8') == 'CN':
                                    cn = component[1].decode('utf-8')
                                    break
                            
                            if cn and cn.startswith('*.'):
                                filePath = wildcard_path
                                is_wildcard = True
                            else:
                                return {'status': 'none', 'days': 0, 'issuer': '', 'is_wildcard': False}
                        except:
                            return {'status': 'none', 'days': 0, 'issuer': '', 'is_wildcard': False}
                    else:
                        return {'status': 'none', 'days': 0, 'issuer': '', 'is_wildcard': False}
                else:
                    return {'status': 'none', 'days': 0, 'issuer': '', 'is_wildcard': False}
            else:
                is_wildcard = False
            
            # Load and analyze certificate
            x509 = OpenSSL.crypto.load_certificate(
                OpenSSL.crypto.FILETYPE_PEM,
                open(filePath, 'r').read()
            )
            
            # Get expiration date
            expireData = x509.get_notAfter().decode('ascii')
            finalDate = datetime.strptime(expireData, '%Y%m%d%H%M%SZ')
            now = datetime.now()
            diff = finalDate - now
            days = diff.days
            
            # Get issuer
            issuer_org = None
            for component in x509.get_issuer().get_components():
                if component[0].decode('utf-8') == 'O':
                    issuer_org = component[1].decode('utf-8')
                    break
            
            if not issuer_org:
                issuer_org = 'Unknown'
            
            # Check if it's a wildcard certificate
            if not is_wildcard:
                cn = None
                for component in x509.get_subject().get_components():
                    if component[0].decode('utf-8') == 'CN':
                        cn = component[1].decode('utf-8')
                        break
                if cn and cn.startswith('*.'):
                    is_wildcard = True
            
            # Check if it's self-signed by comparing issuer and subject
            is_self_signed = False
            issuer_cn = None
            subject_cn = None
            
            for component in x509.get_issuer().get_components():
                if component[0].decode('utf-8') == 'CN':
                    issuer_cn = component[1].decode('utf-8')
                    break
                    
            for component in x509.get_subject().get_components():
                if component[0].decode('utf-8') == 'CN':
                    subject_cn = component[1].decode('utf-8')
                    break
            
            # Certificate is self-signed if issuer CN equals subject CN
            if issuer_cn and subject_cn and issuer_cn == subject_cn:
                is_self_signed = True
            
            # Also check if issuer equals subject entirely
            if x509.get_issuer() == x509.get_subject():
                is_self_signed = True
            
            # Determine status
            if is_self_signed:
                status = 'self-signed'
            elif days < 0:
                status = 'expired'
            elif days <= 7:
                status = 'expiring'
            elif days <= 30:
                status = 'warning'
            else:
                status = 'valid'
            
            return {
                'status': status,
                'days': days,
                'issuer': issuer_org,
                'is_wildcard': is_wildcard
            }
            
        except Exception as e:
            return {'status': 'none', 'days': 0, 'issuer': '', 'is_wildcard': False}


    def findDockersitesListJson(self, Dockersite):

        json_data = "["
        checker = 0

        try:
            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to read machine IP, error:" + str(msg))
            ipAddress = "192.168.100.1"

        from plogical.phpUtilities import phpUtilities
        for items in Dockersite:
            website = Websites.objects.get(pk=items.admin.pk)
            vhFile = f'/usr/local/lsws/conf/vhosts/{website.domain}/vhost.conf'

            try:
                PHPVersionActual = phpUtilities.WrapGetPHPVersionFromFileToGetVersionWithPHP(website)
            except:
                PHPVersionActual = 'PHP 8.1'


            if items.state == 0:
                state = "Suspended"
            else:
                state = "Active"

            dpkg = PackageAssignment.objects.get(user=website.admin)


            dic = {'id':items.pk, 'domain': website.domain,  'adminEmail': website.adminEmail, 'ipAddress': ipAddress,
                   'admin': website.admin.userName, 'package': dpkg.package.Name, 'state': state,
                   'CPU': int(items.CPUsMySQL)+int(items.CPUsSite), 'Ram': int(items.MemorySite)+int(items.MemoryMySQL),  'phpVersion': PHPVersionActual }

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        return json_data

    def findChildsListJson(self, childs):

        json_data = "["
        checker = 0

        try:
            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to read machine IP, error:" + str(msg))
            ipAddress = "192.168.100.1"

        for items in childs:

            dic = {'domain': items.domain, 'masterDomain': items.master.domain, 'adminEmail': items.master.adminEmail,
                   'ipAddress': ipAddress,
                   'admin': items.master.admin.userName, 'package': items.master.package.packageName,
                   'path': items.path}

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        return json_data

    def recordsPointer(self, page, toShow):
        finalPageNumber = ((page * toShow)) - toShow
        endPageNumber = finalPageNumber + toShow
        return endPageNumber, finalPageNumber

    def getPagination(self, records, toShow):
        pages = float(records) / float(toShow)

        pagination = []
        counter = 1

        if pages <= 1.0:
            pages = 1
            pagination.append(counter)
        else:
            pages = ceil(pages)
            finalPages = int(pages) + 1

            for i in range(1, finalPages):
                pagination.append(counter)
                counter = counter + 1

        return pagination

    def submitWebsiteDeletion(self, userID=None, data=None):
        try:
            if data['websiteName'].find("cyberpanel.website") > -1:
                url = "https://platform.cyberpersons.com/CyberpanelAdOns/DeleteDomain"

                domain_data = {
                    "name": "test-domain",
                    "IP": ACLManager.GetServerIP(),
                    "domain": data['websiteName']
                }

                import requests
                response = requests.post(url, data=json.dumps(domain_data))

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'deleteWebsite') == 0:
                return ACLManager.loadErrorJson('websiteDeleteStatus', 0)

            websiteName = data['websiteName']

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(websiteName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('websiteDeleteStatus', 0)

            ## Deleting master domain

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " deleteVirtualHostConfigurations --virtualHostName " + websiteName
            ProcessUtilities.popenExecutioner(execPath)

            ### delete site from dgdrive backups

            try:

                from websiteFunctions.models import GDriveSites
                GDriveSites.objects.filter(domain=websiteName).delete()
            except:
                pass

            data_ret = {'status': 1, 'websiteDeleteStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'websiteDeleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitDomainDeletion(self, userID=None, data=None):
        try:

            if data['websiteName'].find("cyberpanel.website") > -1:
                url = "https://platform.cyberpersons.com/CyberpanelAdOns/DeleteDomain"

                domain_data = {
                    "name": "test-domain",
                    "IP": ACLManager.GetServerIP(),
                    "domain": data['websiteName']
                }

                import requests
                response = requests.post(url, data=json.dumps(domain_data))

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            websiteName = data['websiteName']

            try:
                DeleteDocRoot = int(data['DeleteDocRoot'])
            except:
                DeleteDocRoot = 0

            if ACLManager.checkOwnership(websiteName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('websiteDeleteStatus', 0)

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " deleteDomain --virtualHostName " + websiteName + ' --DeleteDocRoot %s' % (
                str(DeleteDocRoot))
            ProcessUtilities.outputExecutioner(execPath)

            data_ret = {'status': 1, 'websiteDeleteStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'websiteDeleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitWebsiteStatus(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'suspendWebsite') == 0:
                return ACLManager.loadErrorJson('websiteStatus', 0)

            websiteName = data['websiteName']
            state = data['state']

            website = Websites.objects.get(domain=websiteName)

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(websiteName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('websiteStatus', 0)

            if state == "Suspend":
                confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + websiteName
                vhostConfPath = confPath + "/vhost.conf"
                
                # Ensure suspension page exists and has proper permissions
                suspensionPagePath = "/usr/local/CyberCP/websiteFunctions/suspension.html"
                suspensionDir = "/usr/local/CyberCP/websiteFunctions"
                
                # Ensure directory exists
                if not os.path.exists(suspensionDir):
                    try:
                        command = f"mkdir -p {suspensionDir}"
                        ProcessUtilities.executioner(command)
                        logging.CyberCPLogFileWriter.writeToFile(f"Created suspension directory: {suspensionDir}")
                    except Exception as e:
                        logging.CyberCPLogFileWriter.writeToFile(f"Failed to create suspension directory: {str(e)}")
                
                if not os.path.exists(suspensionPagePath):
                    # Create default suspension page if it doesn't exist
                    defaultSuspensionHTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Website Suspended</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .container {
            text-align: center;
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 500px;
        }
        h1 {
            color: #e74c3c;
            margin-bottom: 20px;
        }
        p {
            color: #555;
            line-height: 1.6;
            margin-bottom: 20px;
        }
        .contact {
            color: #777;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Website Suspended</h1>
        <p>This website has been temporarily suspended. This could be due to various reasons including billing issues, policy violations, or administrative actions.</p>
        <p>If you are the website owner, please contact your hosting provider for more information about why your account was suspended and how to restore service.</p>
        <p class="contact">For support, please contact your system administrator.</p>
    </div>
</body>
</html>"""
                    try:
                        # Create directory if it doesn't exist
                        dirPath = os.path.dirname(suspensionPagePath)
                        if not os.path.exists(dirPath):
                            command = f"mkdir -p {dirPath}"
                            ProcessUtilities.executioner(command)
                        
                        # Write the HTML content to a temporary file in /home/cyberpanel
                        tempFile = "/home/cyberpanel/suspension_temp.html"
                        
                        # Create the file using normal Python file operations
                        with open(tempFile, 'w') as f:
                            f.write(defaultSuspensionHTML)
                        
                        # Use ProcessUtilities to move the file to the final location
                        command = f"mv {tempFile} {suspensionPagePath}"
                        ProcessUtilities.executioner(command)
                        logging.CyberCPLogFileWriter.writeToFile(f"Created suspension page: {suspensionPagePath}")
                    except Exception as e:
                        logging.CyberCPLogFileWriter.writeToFile(f"Failed to create suspension page: {str(e)}")
                        # Try alternative method using echo command
                        try:
                            escaped_html = defaultSuspensionHTML.replace('"', '\\"')
                            command = f'echo "{escaped_html}" > {suspensionPagePath}'
                            ProcessUtilities.executioner(command)
                            logging.CyberCPLogFileWriter.writeToFile(f"Created suspension page using echo: {suspensionPagePath}")
                        except Exception as e2:
                            logging.CyberCPLogFileWriter.writeToFile(f"Failed to create suspension page with echo: {str(e2)}")
                            return self.ajaxPre(0, f"Failed to create suspension page: {str(e2)}")
                
                # Set proper permissions for suspension page
                try:
                    command = f"chown lsadm:lsadm {suspensionPagePath}"
                    result = ProcessUtilities.executioner(command)
                    if result.find('cannot') > -1:
                        logging.CyberCPLogFileWriter.writeToFile(f"Warning: Failed to set ownership for suspension page: {result}")
                    
                    command = f"chmod 644 {suspensionPagePath}"
                    result = ProcessUtilities.executioner(command)
                    if result.find('cannot') > -1:
                        logging.CyberCPLogFileWriter.writeToFile(f"Warning: Failed to set permissions for suspension page: {result}")
                    
                    logging.CyberCPLogFileWriter.writeToFile(f"Set permissions for suspension page: {suspensionPagePath}")
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error setting suspension page permissions: {str(e)}")
                    # Don't fail the entire operation for permission issues
                
                # Create suspension configuration with end marker
                suspensionConf = """# Website Suspension Configuration
context /{
  location                        $DOC_ROOT/
  allowBrowse                     1
  
  rewrite  {
    enable                  1
    autoLoadHtaccess        0
    rules                   <<<END_rules
RewriteEngine On
RewriteCond %{REQUEST_URI} !^/cyberpanel_suspension_page\.html$
RewriteRule ^(.*)$ /cyberpanel_suspension_page.html [L]
END_rules
  }
  
  addDefaultCharset               off
}

context /cyberpanel_suspension_page.html {
  location                        /usr/local/CyberCP/websiteFunctions/suspension.html
  accessible                      1
  extraHeaders                    X-Frame-Options: DENY
  allowBrowse                     1
}
# End Website Suspension Configuration
"""
                
                try:
                    # Check if vhost file exists
                    if not os.path.exists(vhostConfPath):
                        logging.CyberCPLogFileWriter.writeToFile(f"Error: Vhost configuration file not found: {vhostConfPath}")
                        return self.ajaxPre(0, f"Vhost configuration file not found for {websiteName}")
                    
                    # Read current vhost configuration
                    with open(vhostConfPath, 'r') as f:
                        vhostContent = f.read()
                    
                    if not vhostContent.strip():
                        logging.CyberCPLogFileWriter.writeToFile(f"Warning: Empty vhost configuration file: {vhostConfPath}")
                    
                    if "# Website Suspension Configuration" not in vhostContent:
                        # Check if there's an existing rewrite block at the root level
                        # If so, we need to comment it out to avoid conflicts
                        
                        # Pattern to find root-level rewrite block
                        rewrite_pattern = r'^(rewrite\s*\{[^}]*\})'
                        
                        # Comment out existing root-level rewrite block if found
                        if re.search(rewrite_pattern, vhostContent, re.MULTILINE | re.DOTALL):
                            vhostContent = re.sub(rewrite_pattern, 
                                lambda m: '# Commented out during suspension\n#' + m.group(0).replace('\n', '\n#'), 
                                vhostContent, 
                                flags=re.MULTILINE | re.DOTALL)
                        
                        # Add suspension configuration at the beginning
                        modifiedContent = suspensionConf + "\n" + vhostContent
                        
                        # Write directly to vhost file
                        with open(vhostConfPath, 'w') as f:
                            f.write(modifiedContent)
                        
                        # Set proper ownership
                        command = f"chown lsadm:lsadm {vhostConfPath}"
                        result = ProcessUtilities.executioner(command)
                        if result.find('cannot') > -1:
                            logging.CyberCPLogFileWriter.writeToFile(f"Warning: Failed to set vhost ownership: {result}")
                        
                        logging.CyberCPLogFileWriter.writeToFile(f"Successfully suspended website: {websiteName}")
                except IOError as e:
                    # If direct file access fails, fall back to command-based approach
                    command = f"cat {vhostConfPath}"
                    vhostContent = ProcessUtilities.outputExecutioner(command)
                    
                    if vhostContent and "# Website Suspension Configuration" not in vhostContent:
                        # Check if there's an existing rewrite block at the root level
                        # If so, we need to comment it out to avoid conflicts
                        
                        # Pattern to find root-level rewrite block
                        rewrite_pattern = r'^(rewrite\s*\{[^}]*\})'
                        
                        # Comment out existing root-level rewrite block if found
                        if re.search(rewrite_pattern, vhostContent, re.MULTILINE | re.DOTALL):
                            vhostContent = re.sub(rewrite_pattern, 
                                lambda m: '# Commented out during suspension\n#' + m.group(0).replace('\n', '\n#'), 
                                vhostContent, 
                                flags=re.MULTILINE | re.DOTALL)
                        
                        modifiedContent = suspensionConf + "\n" + vhostContent
                        
                        # Use temp file in /tmp
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='cyberpanel_') as tmpfile:
                            tmpfile.write(modifiedContent)
                            tempFile = tmpfile.name
                        
                        # Copy to vhost configuration
                        command = f"cp {tempFile} {vhostConfPath}"
                        ProcessUtilities.executioner(command)
                        
                        # Set proper ownership
                        command = f"chown lsadm:lsadm {vhostConfPath}"
                        ProcessUtilities.executioner(command)
                        
                        # Remove temporary file
                        try:
                            os.remove(tempFile)
                        except:
                            pass
                
                # Suspend cron jobs for child domains
                childDomains = website.childdomains_set.all()
                
                for items in childDomains:
                    # Suspend cron jobs for child domain
                    try:
                        CronUtil.CronPrem(1)
                        execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/cronUtil.py"
                        execPath = execPath + " suspendWebsiteCrons --externalApp " + items.externalApp
                        cronOutput = ProcessUtilities.outputExecutioner(execPath, items.externalApp)
                        CronUtil.CronPrem(0)
                        
                        if cronOutput.find("1,") > -1:
                            logging.CyberCPLogFileWriter.writeToFile(f"Successfully suspended cron jobs for child domain {items.domain}")
                        else:
                            logging.CyberCPLogFileWriter.writeToFile(f"Warning: Failed to suspend cron jobs for child domain {items.domain}: {cronOutput}")
                    except Exception as e:
                        CronUtil.CronPrem(0)  # Ensure permissions are restored
                        logging.CyberCPLogFileWriter.writeToFile(f"Error suspending cron jobs for child domain {items.domain}: {str(e)}")

                # Apply same suspension configuration to child domains
                for items in childDomains:
                    childConfPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + items.domain
                    childVhostConfPath = childConfPath + "/vhost.conf"
                    
                    try:
                        # Try direct file access first
                        try:
                            with open(childVhostConfPath, 'r') as f:
                                childVhostContent = f.read()
                            
                            if "# Website Suspension Configuration" not in childVhostContent:
                                childModifiedContent = suspensionConf + "\n" + childVhostContent
                                
                                with open(childVhostConfPath, 'w') as f:
                                    f.write(childModifiedContent)
                                
                                command = f"chown lsadm:lsadm {childVhostConfPath}"
                                ProcessUtilities.executioner(command)
                        except IOError:
                            # Fall back to command-based approach
                            command = f"cat {childVhostConfPath}"
                            childVhostContent = ProcessUtilities.outputExecutioner(command)
                            
                            if childVhostContent and "# Website Suspension Configuration" not in childVhostContent:
                                childModifiedContent = suspensionConf + "\n" + childVhostContent
                                
                                import tempfile
                                with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='cyberpanel_child_') as tmpfile:
                                    tmpfile.write(childModifiedContent)
                                    childTempFile = tmpfile.name
                                
                                command = f"cp {childTempFile} {childVhostConfPath}"
                                ProcessUtilities.executioner(command)
                                
                                command = f"chown lsadm:lsadm {childVhostConfPath}"
                                ProcessUtilities.executioner(command)
                                
                                try:
                                    os.remove(childTempFile)
                                except:
                                    pass
                    except Exception as e:
                        CyberCPLogFileWriter.writeToFile(f"Error suspending child domain {items.domain}: {str(e)}")
                
                # Suspend cron jobs for this website
                try:
                    CronUtil.CronPrem(1)
                    execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/cronUtil.py"
                    execPath = execPath + " suspendWebsiteCrons --externalApp " + website.externalApp
                    cronOutput = ProcessUtilities.outputExecutioner(execPath, website.externalApp)
                    CronUtil.CronPrem(0)
                    
                    if cronOutput.find("1,") > -1:
                        logging.CyberCPLogFileWriter.writeToFile(f"Successfully suspended cron jobs for {websiteName}")
                    else:
                        logging.CyberCPLogFileWriter.writeToFile(f"Warning: Failed to suspend cron jobs for {websiteName}: {cronOutput}")
                except Exception as e:
                    CronUtil.CronPrem(0)  # Ensure permissions are restored
                    logging.CyberCPLogFileWriter.writeToFile(f"Error suspending cron jobs for {websiteName}: {str(e)}")

                # Restart LiteSpeed to apply changes
                try:
                    installUtilities.reStartLiteSpeedSocket()
                    logging.CyberCPLogFileWriter.writeToFile(f"Restarted LiteSpeed after suspending {websiteName}")
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Warning: Failed to restart LiteSpeed: {str(e)}")
                
                website.state = 1
            else:
                # Unsuspend logic
                confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + websiteName
                vhostConfPath = confPath + "/vhost.conf"
                
                logging.CyberCPLogFileWriter.writeToFile(f"Attempting to unsuspend website: {websiteName}")
                
                try:
                    # Check if vhost file exists
                    if not os.path.exists(vhostConfPath):
                        logging.CyberCPLogFileWriter.writeToFile(f"Error: Vhost configuration file not found: {vhostConfPath}")
                        return self.ajaxPre(0, f"Vhost configuration file not found for {websiteName}")
                    
                    # Try direct file access first
                    with open(vhostConfPath, 'r') as f:
                        vhostContent = f.read()
                    
                    if not vhostContent.strip():
                        logging.CyberCPLogFileWriter.writeToFile(f"Warning: Empty vhost configuration file: {vhostConfPath}")
                    
                    if "# Website Suspension Configuration" in vhostContent:
                        # Use regex to remove the suspension configuration block
                        pattern = r'# Website Suspension Configuration.*?# End Website Suspension Configuration\n'
                        modifiedContent = re.sub(pattern, '', vhostContent, flags=re.DOTALL)
                        
                        # Restore any rewrite blocks that were commented out during suspension
                        commented_rewrite_pattern = r'# Commented out during suspension\n((?:#[^\n]*\n)+)'
                        
                        def restore_commented_block(match):
                            commented_block = match.group(1)
                            # Remove the leading # from each line
                            restored_block = '\n'.join(line[1:] if line.startswith('#') else line 
                                                     for line in commented_block.splitlines())
                            return restored_block
                        
                        if re.search(commented_rewrite_pattern, modifiedContent):
                            modifiedContent = re.sub(commented_rewrite_pattern,
                                                   restore_commented_block,
                                                   modifiedContent)
                        
                        with open(vhostConfPath, 'w') as f:
                            f.write(modifiedContent)
                        
                        command = f"chown lsadm:lsadm {vhostConfPath}"
                        result = ProcessUtilities.executioner(command)
                        if result.find('cannot') > -1:
                            logging.CyberCPLogFileWriter.writeToFile(f"Warning: Failed to set vhost ownership: {result}")
                        
                        logging.CyberCPLogFileWriter.writeToFile(f"Successfully unsuspended website: {websiteName}")
                    else:
                        logging.CyberCPLogFileWriter.writeToFile(f"Website {websiteName} is not currently suspended")
                except IOError:
                    # Fall back to command-based approach
                    command = f"cat {vhostConfPath}"
                    vhostContent = ProcessUtilities.outputExecutioner(command)
                    
                    if vhostContent and "# Website Suspension Configuration" in vhostContent:
                        pattern = r'# Website Suspension Configuration.*?# End Website Suspension Configuration\n'
                        modifiedContent = re.sub(pattern, '', vhostContent, flags=re.DOTALL)
                        
                        # Restore any rewrite blocks that were commented out during suspension
                        commented_rewrite_pattern = r'# Commented out during suspension\n((?:#[^\n]*\n)+)'
                        
                        def restore_commented_block(match):
                            commented_block = match.group(1)
                            # Remove the leading # from each line
                            restored_block = '\n'.join(line[1:] if line.startswith('#') else line 
                                                     for line in commented_block.splitlines())
                            return restored_block
                        
                        if re.search(commented_rewrite_pattern, modifiedContent):
                            modifiedContent = re.sub(commented_rewrite_pattern,
                                                   restore_commented_block,
                                                   modifiedContent)
                        
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='cyberpanel_') as tmpfile:
                            tmpfile.write(modifiedContent)
                            tempFile = tmpfile.name
                        
                        command = f"cp {tempFile} {vhostConfPath}"
                        ProcessUtilities.executioner(command)
                        
                        command = f"chown lsadm:lsadm {vhostConfPath}"
                        ProcessUtilities.executioner(command)
                        
                        try:
                            os.remove(tempFile)
                        except:
                            pass
                
                # Restore cron jobs for child domains
                childDomains = website.childdomains_set.all()
                
                for items in childDomains:
                    # Restore cron jobs for child domain
                    try:
                        CronUtil.CronPrem(1)
                        execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/cronUtil.py"
                        execPath = execPath + " restoreWebsiteCrons --externalApp " + items.externalApp
                        cronOutput = ProcessUtilities.outputExecutioner(execPath, items.externalApp)
                        CronUtil.CronPrem(0)
                        
                        if cronOutput.find("1,") > -1:
                            logging.CyberCPLogFileWriter.writeToFile(f"Successfully restored cron jobs for child domain {items.domain}")
                        else:
                            logging.CyberCPLogFileWriter.writeToFile(f"Info: {cronOutput} for child domain {items.domain}")
                    except Exception as e:
                        CronUtil.CronPrem(0)  # Ensure permissions are restored
                        logging.CyberCPLogFileWriter.writeToFile(f"Error restoring cron jobs for child domain {items.domain}: {str(e)}")
                
                # Remove suspension configuration from child domains
                for items in childDomains:
                    childConfPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + items.domain
                    childVhostConfPath = childConfPath + "/vhost.conf"
                    
                    try:
                        # Try direct file access first
                        try:
                            with open(childVhostConfPath, 'r') as f:
                                childVhostContent = f.read()
                            
                            if "# Website Suspension Configuration" in childVhostContent:
                                pattern = r'# Website Suspension Configuration.*?# End Website Suspension Configuration\n'
                                childModifiedContent = re.sub(pattern, '', childVhostContent, flags=re.DOTALL)
                                
                                with open(childVhostConfPath, 'w') as f:
                                    f.write(childModifiedContent)
                                
                                command = f"chown lsadm:lsadm {childVhostConfPath}"
                                ProcessUtilities.executioner(command)
                        except IOError:
                            # Fall back to command-based approach
                            command = f"cat {childVhostConfPath}"
                            childVhostContent = ProcessUtilities.outputExecutioner(command)
                            
                            if childVhostContent and "# Website Suspension Configuration" in childVhostContent:
                                pattern = r'# Website Suspension Configuration.*?# End Website Suspension Configuration\n'
                                childModifiedContent = re.sub(pattern, '', childVhostContent, flags=re.DOTALL)
                                
                                import tempfile
                                with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='cyberpanel_child_') as tmpfile:
                                    tmpfile.write(childModifiedContent)
                                    childTempFile = tmpfile.name
                                
                                command = f"cp {childTempFile} {childVhostConfPath}"
                                ProcessUtilities.executioner(command)
                                
                                command = f"chown lsadm:lsadm {childVhostConfPath}"
                                ProcessUtilities.executioner(command)
                                
                                try:
                                    os.remove(childTempFile)
                                except:
                                    pass
                    except Exception as e:
                        CyberCPLogFileWriter.writeToFile(f"Error unsuspending child domain {items.domain}: {str(e)}")
                
                # Restore cron jobs for this website
                try:
                    CronUtil.CronPrem(1)
                    execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/cronUtil.py"
                    execPath = execPath + " restoreWebsiteCrons --externalApp " + website.externalApp
                    cronOutput = ProcessUtilities.outputExecutioner(execPath, website.externalApp)
                    CronUtil.CronPrem(0)
                    
                    if cronOutput.find("1,") > -1:
                        logging.CyberCPLogFileWriter.writeToFile(f"Successfully restored cron jobs for {websiteName}")
                    else:
                        logging.CyberCPLogFileWriter.writeToFile(f"Info: {cronOutput} for {websiteName}")
                except Exception as e:
                    CronUtil.CronPrem(0)  # Ensure permissions are restored
                    logging.CyberCPLogFileWriter.writeToFile(f"Error restoring cron jobs for {websiteName}: {str(e)}")

                # Restart LiteSpeed to apply changes
                try:
                    installUtilities.reStartLiteSpeedSocket()
                    logging.CyberCPLogFileWriter.writeToFile(f"Restarted LiteSpeed after unsuspending {websiteName}")
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Warning: Failed to restart LiteSpeed: {str(e)}")
                
                website.state = 0

            website.save()

            data_ret = {'websiteStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except Exception as msg:
            CyberCPLogFileWriter.writeToFile(f"Error in submitWebsiteStatus: {str(msg)}")
            data_ret = {'websiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitWebsiteModify(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'modifyWebsite') == 0:
                return ACLManager.loadErrorJson('modifyStatus', 0)

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(data['websiteToBeModified'], admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('websiteDeleteStatus', 0)

            packs = ACLManager.loadPackages(userID, currentACL)
            admins = ACLManager.loadAllUsers(userID)

            ## Get packs name

            json_data = "["
            checker = 0

            for items in packs:
                dic = {"pack": items}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            ### Get admin names

            admin_data = "["
            checker = 0

            for items in admins:
                dic = {"adminNames": items}

                if checker == 0:
                    admin_data = admin_data + json.dumps(dic)
                    checker = 1
                else:
                    admin_data = admin_data + ',' + json.dumps(dic)

            admin_data = admin_data + ']'

            websiteToBeModified = data['websiteToBeModified']

            modifyWeb = Websites.objects.get(domain=websiteToBeModified)

            email = modifyWeb.adminEmail
            currentPack = modifyWeb.package.packageName
            owner = modifyWeb.admin.userName
            
            # Get current home directory information
            from userManagment.homeDirectoryUtils import HomeDirectoryUtils
            current_home = HomeDirectoryUtils.getUserHomeDirectoryObject(owner)
            currentHomeDirectory = current_home.name if current_home else 'Default'

            data_ret = {'status': 1, 'modifyStatus': 1, 'error_message': "None", "adminEmail": email,
                        "packages": json_data, "current_pack": currentPack, "adminNames": admin_data,
                        'currentAdmin': owner, 'currentHomeDirectory': currentHomeDirectory}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)

        except BaseException as msg:
            dic = {'status': 0, 'modifyStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def fetchWebsiteDataJSON(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'createWebsite') == 0:
                return ACLManager.loadErrorJson('createWebSiteStatus', 0)

            packs = ACLManager.loadPackages(userID, currentACL)
            admins = ACLManager.loadAllUsers(userID)

            ## Get packs name

            json_data = "["
            checker = 0

            for items in packs:
                dic = {"pack": items}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            ### Get admin names

            admin_data = "["
            checker = 0

            for items in admins:
                dic = {"adminNames": items}

                if checker == 0:
                    admin_data = admin_data + json.dumps(dic)
                    checker = 1
                else:
                    admin_data = admin_data + ',' + json.dumps(dic)

            admin_data = admin_data + ']'

            data_ret = {'status': 1, 'error_message': "None",
                        "packages": json_data, "adminNames": admin_data}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)

        except BaseException as msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def saveWebsiteChanges(self, userID=None, data=None):
        try:
            domain = data['domain']
            package = data['packForWeb']
            email = data['email']
            phpVersion = data['phpVersion']
            newUser = data['admin']
            homeDirectory = data.get('homeDirectory', '')

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'modifyWebsite') == 0:
                return ACLManager.loadErrorJson('saveStatus', 0)

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('websiteDeleteStatus', 0)

            newOwner = Administrator.objects.get(userName=newUser)
            if ACLManager.checkUserOwnerShip(currentACL, admin, newOwner) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('websiteDeleteStatus', 0)

            confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + domain
            completePathToConfigFile = confPath + "/vhost.conf"

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " changePHP --phpVersion '" + phpVersion + "' --path " + completePathToConfigFile
            ProcessUtilities.popenExecutioner(execPath)

            ####

            newOwner = Administrator.objects.get(userName=newUser)

            modifyWeb = Websites.objects.get(domain=domain)
            webpack = Package.objects.get(packageName=package)

            modifyWeb.package = webpack
            modifyWeb.adminEmail = email
            modifyWeb.phpSelection = phpVersion
            modifyWeb.admin = newOwner

            modifyWeb.save()

            # Handle home directory migration if specified
            if homeDirectory:
                from userManagment.homeDirectoryUtils import HomeDirectoryUtils
                from userManagment.models import HomeDirectory, UserHomeMapping
                
                try:
                    # Get the new home directory
                    new_home_dir = HomeDirectory.objects.get(id=homeDirectory)
                    
                    # Get current home directory for the user
                    current_home = HomeDirectoryUtils.getUserHomeDirectoryObject(newUser)
                    
                    if current_home and current_home.id != new_home_dir.id:
                        # Migrate user to new home directory
                        success, message = HomeDirectoryUtils.migrateUser(
                            newUser, 
                            current_home.path, 
                            new_home_dir.path
                        )
                        
                        if success:
                            # Update user-home mapping
                            UserHomeMapping.objects.update_or_create(
                                user=newOwner,
                                defaults={'home_directory': new_home_dir}
                            )
                        else:
                            # Log error but don't fail the website modification
                            logging.CyberCPLogFileWriter.writeToFile(f"Failed to migrate user {newUser} to home directory {new_home_dir.path}: {message}")
                    elif not current_home:
                        # Create new mapping if user doesn't have one
                        UserHomeMapping.objects.create(
                            user=newOwner,
                            home_directory=new_home_dir
                        )
                        
                except Exception as e:
                    # Log error but don't fail the website modification
                    logging.CyberCPLogFileWriter.writeToFile(f"Error handling home directory change for {newUser}: {str(e)}")

            ## Update disk quota when package changes - Fix for GitHub issue #1442
            if webpack.enforceDiskLimits:
                spaceString = f'{webpack.diskSpace}M {webpack.diskSpace}M'
                command = f'setquota -u {modifyWeb.externalApp} {spaceString} 0 0 /'
                ProcessUtilities.executioner(command)

            ## Fix https://github.com/usmannasir/cyberpanel/issues/998

            # from plogical.IncScheduler import IncScheduler
            # isPU = IncScheduler('CalculateAndUpdateDiskUsage', {})
            # isPU.start()

            command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/IncScheduler.py UpdateDiskUsageForce'
            ProcessUtilities.outputExecutioner(command)

            ##

            data_ret = {'status': 1, 'saveStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def loadDomainHome(self, request=None, userID=None, data=None):

        if Websites.objects.filter(domain=self.domain).exists():

            currentACL = ACLManager.loadedACL(userID)
            website = Websites.objects.get(domain=self.domain)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            Data = {}

            from plogical.processUtilities import ProcessUtilities

            # emailMarketing removed - always return False for marketing status
            # marketingStatus = emACL.checkIfEMEnabled(admin.userName)
            marketingStatus = False

            Data['marketingStatus'] = marketingStatus
            Data['ftpTotal'] = website.package.ftpAccounts
            Data['ftpUsed'] = website.users_set.all().count()

            Data['databasesUsed'] = website.databases_set.all().count()
            Data['databasesTotal'] = website.package.dataBases

            Data['domain'] = self.domain

            DiskUsage, DiskUsagePercentage, bwInMB, bwUsage = virtualHostUtilities.FindStats(website)

            ## bw usage calculations

            Data['bwInMBTotal'] = website.package.bandwidth
            Data['bwInMB'] = bwInMB
            Data['bwUsage'] = bwUsage

            if DiskUsagePercentage > 100:
                DiskUsagePercentage = 100

            Data['diskUsage'] = DiskUsagePercentage
            Data['diskInMB'] = DiskUsage
            Data['diskInMBTotal'] = website.package.diskSpace

            Data['phps'] = PHPManager.findPHPVersions()
            import os

            servicePath = '/home/cyberpanel/postfix'
            if os.path.exists(servicePath):
                Data['email'] = 1
            else:
                Data['email'] = 0

            ## Getting SSL Information
            try:
                import OpenSSL
                from datetime import datetime
                filePath = '/etc/letsencrypt/live/%s/fullchain.pem' % (self.domain)
                x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                       open(filePath, 'r').read())
                expireData = x509.get_notAfter().decode('ascii')
                finalDate = datetime.strptime(expireData, '%Y%m%d%H%M%SZ')

                now = datetime.now()
                diff = finalDate - now
                Data['viewSSL'] = 1
                Data['days'] = str(diff.days)
                Data['authority'] = x509.get_issuer().get_components()[1][1].decode('utf-8')
                renewal_when = _get_ssl_renewal_schedule()
                Data['renewal_when'] = renewal_when

                if Data['authority'] == 'Denial':
                    Data['authority'] = '%s has SELF-SIGNED SSL.' % (self.domain)
                else:
                    Data['authority'] = '%s has SSL from %s.' % (self.domain, Data['authority'])

            except BaseException as msg:
                Data['viewSSL'] = 0
                Data['renewal_when'] = None
                logging.CyberCPLogFileWriter.writeToFile(str(msg))

            servicePath = '/home/cyberpanel/pureftpd'
            if os.path.exists(servicePath):
                Data['ftp'] = 1
            else:
                Data['ftp'] = 0

            # Add-on check logic (copied from sshAccess)
            url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
            addon_data = {
                "name": "all",
                "IP": ACLManager.GetServerIP()
            }
            import requests
            import json
            try:
                response = requests.post(url, data=json.dumps(addon_data))
                Status = response.json().get('status', 0)
            except Exception:
                Status = 0
            Data['has_addons'] = bool((Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent)

            # SSL check (self-signed logic)
            cert_path = '/etc/letsencrypt/live/%s/fullchain.pem' % (self.domain)
            is_selfsigned = False
            ssl_issue_link = '/manageSSL/sslForHostName'
            try:
                import OpenSSL
                with open(cert_path, 'r') as f:
                    pem_data = f.read()
                cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, pem_data)
                # Only check the first cert in the PEM
                issuer_org = None
                for k, v in cert.get_issuer().get_components():
                    if k.decode() == 'O':
                        issuer_org = v.decode()
                        break
                if issuer_org == 'Denial':
                    is_selfsigned = True
                else:
                    is_selfsigned = False
            except Exception:
                is_selfsigned = True  # If cert missing or unreadable, treat as self-signed
            Data['is_selfsigned_ssl'] = bool(is_selfsigned)
            Data['ssl_issue_link'] = ssl_issue_link
            

            # Detect if accessed via IP
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
            accessed_via_ip = False
            try:
                host = request.get_host().split(':')[0]  # Remove port if present
                try:
                    ipaddress.ip_address(host)
                    accessed_via_ip = True
                except ValueError:
                    accessed_via_ip = False
            except Exception as e:
                accessed_via_ip = False
                CyberCPLogFileWriter.writeToFile(f"Error detecting accessed_via_ip: {str(e)}")

            Data['accessed_via_ip'] = bool(accessed_via_ip)

            #### update jwt secret if needed

            import secrets

            fastapi_file = '/usr/local/CyberCP/fastapi_ssh_server.py'
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
            try:
                
                content = ProcessUtilities.outputExecutioner(f'cat {fastapi_file}')
                if 'REPLACE_ME_WITH_INSTALLER' in content:
                    new_secret = secrets.token_urlsafe(32)
                    
                    sed_cmd = f"sed -i 's|JWT_SECRET = \"REPLACE_ME_WITH_INSTALLER\"|JWT_SECRET = \"{new_secret}\"|' '{fastapi_file}'"
                    ProcessUtilities.outputExecutioner(sed_cmd)
                    
                    command = 'systemctl restart fastapi_ssh_server'
                    ProcessUtilities.outputExecutioner(command)
            except Exception:
                CyberCPLogFileWriter.writeLog(f"Failed to update JWT secret: {e}")
                pass

            #####

            #####

            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
            # Ensure FastAPI SSH server systemd service file is in place
            try:
                service_path = '/etc/systemd/system/fastapi_ssh_server.service'
                local_service_path = 'fastapi_ssh_server.service'
                check_service = ProcessUtilities.outputExecutioner(f'test -f {service_path} && echo exists || echo missing')
                if 'missing' in check_service:
                    ProcessUtilities.outputExecutioner(f'cp /usr/local/CyberCP/fastapi_ssh_server.service {service_path}')
                    ProcessUtilities.outputExecutioner('systemctl daemon-reload')
            except Exception as e:
                CyberCPLogFileWriter.writeLog(f"Failed to copy or reload fastapi_ssh_server.service: {e}")
            

            #####

            # Ensure FastAPI SSH server is running using ProcessUtilities
            try:
                ProcessUtilities.outputExecutioner('systemctl is-active --quiet fastapi_ssh_server')
                ProcessUtilities.outputExecutioner('systemctl enable --now fastapi_ssh_server')
                ProcessUtilities.outputExecutioner('systemctl start fastapi_ssh_server')

                csfPath = '/etc/csf'

                sshPort = '8888'

                if os.path.exists(csfPath):
                        dataIn = {'protocol': 'TCP_IN', 'ports': sshPort}

                        # self.modifyPorts is a method in the firewallManager.py file so how can we call it here?
                        # we need to call the method from the firewallManager.py file
                        from firewall.firewallManager import FirewallManager
                        firewallManager = FirewallManager()
                        firewallManager.modifyPorts(dataIn)
                        dataIn = {'protocol': 'TCP_OUT', 'ports': sshPort}
                        firewallManager.modifyPorts(dataIn)
                else:
                    from plogical.firewallUtilities import FirewallUtilities
                    from firewall.models import FirewallRules
                    try:
                        updateFW = FirewallRules.objects.get(name="WebTerminalPort")
                        FirewallUtilities.deleteRule("tcp", updateFW.port, "0.0.0.0/0")
                        updateFW.port = sshPort
                        updateFW.save()
                        FirewallUtilities.addRule('tcp', sshPort, "0.0.0.0/0")
                    except:
                        try:
                            newFireWallRule = FirewallRules(name="WebTerminalPort", port=sshPort, proto="tcp")
                            newFireWallRule.save()
                            FirewallUtilities.addRule('tcp', sshPort, "0.0.0.0/0")
                        except BaseException as msg:
                            CyberCPLogFileWriter.writeToFile(str(msg))

            except Exception as e:
                CyberCPLogFileWriter.writeLog(f"Failed to ensure fastapi_ssh_server is running: {e}")

            proc = httpProc(request, 'websiteFunctions/website.html', Data)
            return proc.render()
        else:
            proc = httpProc(request, 'websiteFunctions/website.html',
                            {"error": 1, "domain": "This domain does not exists."})
            return proc.render()

    def launchChild(self, request=None, userID=None, data=None):

        if ChildDomains.objects.filter(domain=self.childDomain).exists():
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            website = Websites.objects.get(domain=self.domain)

            Data = {}

            Data['ftpTotal'] = website.package.ftpAccounts
            Data['ftpUsed'] = website.users_set.all().count()

            Data['databasesUsed'] = website.databases_set.all().count()
            Data['databasesTotal'] = website.package.dataBases

            Data['domain'] = self.domain
            Data['childDomain'] = self.childDomain

            DiskUsage, DiskUsagePercentage, bwInMB, bwUsage = virtualHostUtilities.FindStats(website)

            ## bw usage calculations

            Data['bwInMBTotal'] = website.package.bandwidth
            Data['bwInMB'] = bwInMB
            Data['bwUsage'] = bwUsage

            if DiskUsagePercentage > 100:
                DiskUsagePercentage = 100

            Data['diskUsage'] = DiskUsagePercentage
            Data['diskInMB'] = DiskUsage
            Data['diskInMBTotal'] = website.package.diskSpace

            Data['phps'] = PHPManager.findPHPVersions()

            servicePath = '/home/cyberpanel/postfix'
            if os.path.exists(servicePath):
                Data['email'] = 1
            else:
                Data['email'] = 0

            servicePath = '/home/cyberpanel/pureftpd'
            if os.path.exists(servicePath):
                Data['ftp'] = 1
            else:
                Data['ftp'] = 0

            ## Getting SSL Information
            try:
                import OpenSSL
                from datetime import datetime
                filePath = '/etc/letsencrypt/live/%s/fullchain.pem' % (self.childDomain)
                x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                       open(filePath, 'r').read())
                expireData = x509.get_notAfter().decode('ascii')
                finalDate = datetime.strptime(expireData, '%Y%m%d%H%M%SZ')

                now = datetime.now()
                diff = finalDate - now
                Data['viewSSL'] = 1
                Data['days'] = str(diff.days)
                Data['authority'] = x509.get_issuer().get_components()[1][1].decode('utf-8')
                Data['renewal_when'] = _get_ssl_renewal_schedule()

                if Data['authority'] == 'Denial':
                    Data['authority'] = '%s has SELF-SIGNED SSL.' % (self.childDomain)
                else:
                    Data['authority'] = '%s has SSL from %s.' % (self.childDomain, Data['authority'])

            except BaseException as msg:
                Data['viewSSL'] = 0
                Data['renewal_when'] = None
                logging.CyberCPLogFileWriter.writeToFile(str(msg))

            proc = httpProc(request, 'websiteFunctions/launchChild.html', Data)
            return proc.render()
        else:
            proc = httpProc(request, 'websiteFunctions/launchChild.html',
                            {"error": 1, "domain": "This child domain does not exists"})
            return proc.render()

    def _get_log_file_path(self, domain_name, log_type):
        """
        Get the correct log file path for a domain.
        For child domains (sub-domains), logs are stored in the master domain's log directory.
        
        Args:
            domain_name: The domain name (could be a child domain)
            log_type: 1 for access log, 0 for error log
            
        Returns:
            str: The full path to the log file
        """
        try:
            # Check if this is a child domain
            try:
                child_domain = ChildDomains.objects.get(domain=domain_name)
                master_domain = child_domain.master.domain
                log_dir = f"/home/{master_domain}/logs"
            except ChildDomains.DoesNotExist:
                # Not a child domain, use standard path
                log_dir = f"/home/{domain_name}/logs"
            
            # Construct log file path
            if log_type == 1:
                log_file = f"{domain_name}.access_log"
            else:
                log_file = f"{domain_name}.error_log"
            
            return f"{log_dir}/{log_file}"
        except Exception as e:
            # Fallback to standard path if anything fails
            logging.CyberCPLogFileWriter.writeToFile(f'Error determining log path for {domain_name}: {str(e)}')
            if log_type == 1:
                return f"/home/{domain_name}/logs/{domain_name}.access_log"
            else:
                return f"/home/{domain_name}/logs/{domain_name}.error_log"

    def getDataFromLogFile(self, userID=None, data=None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        logType = data['logType']
        self.domain = data['virtualHost']
        page = data['page']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('logstatus', 0)

        # Use helper method to get correct log file path (handles child domains)
        fileName = self._get_log_file_path(self.domain, logType)

        command = 'ls -la %s' % fileName
        result = ProcessUtilities.outputExecutioner(command)

        if result.find('->') > -1:
            final_json = json.dumps(
                {'status': 0, 'logstatus': 0,
                 'error_message': "Symlink attack."})
            return HttpResponse(final_json)
        
        # Only read from the specific domain's log file - don't fallback to master domain
        # This ensures we only show logs for the requested domain, not mixed logs from other domains
        # If the log file doesn't exist or is empty, we'll return empty results

        ## get Logs
        website = Websites.objects.get(domain=self.domain)

        output = virtualHostUtilities.getAccessLogs(fileName, page, website.externalApp)

        if output.find("1,None") > -1:
            final_json = json.dumps(
                {'status': 0, 'logstatus': 0,
                 'error_message': "Not able to fetch logs, see CyberPanel main log file, Error: %s" % (output)})
            return HttpResponse(final_json)

        ## get log ends here.

        data = output.split("\n")

        json_data = "["
        checker = 0

        for items in reversed(data):
            if len(items) > 10:
                try:
                    logData = items.split(" ")
                    if len(logData) < 10:
                        continue
                    
                    # Parse log entry: format is "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\""
                    # When split by space: [0]="IP, [1]=-, [2]=-, [3]=[timestamp_part1, [4]=timestamp_part2], [5]="GET, [6]=/path?params, [7]=HTTP/2", [8]=status, [9]=size, [10]="referer", [11+]="user-agent"
                    ipAddress = logData[0].strip('"')
                    # Reconstruct timestamp from fields 3 and 4
                    time = (logData[3] + " " + logData[4]).strip("[").strip("]") if len(logData) > 4 else logData[3].strip("[").strip("]")
                    # Resource path starts at field 6, reconstruct until we hit HTTP/version field
                    if len(logData) > 6:
                        resource_parts = []
                        i = 6
                        while i < len(logData) and not logData[i].startswith('HTTP/'):
                            resource_parts.append(logData[i])
                            i += 1
                        resource = " ".join(resource_parts).strip('"')
                    else:
                        resource = ""
                    # Size is typically in field 9 (after status code in field 8)
                    size = logData[9].replace('"', '') if len(logData) > 9 else "0"
                    
                    # Note: Log format doesn't include domain name, so domain is determined by which log file is read
                    # We already ensured we're reading from the correct domain's log file above

                    dic = {'domain': self.domain,  # Use requested domain since it's determined by log file
                           'ipAddress': ipAddress,
                           'time': time,
                           'resource': resource,
                           'size': size,
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)
                except (IndexError, ValueError) as e:
                    # Skip malformed log entries
                    continue

        json_data = json_data + ']'
        final_json = json.dumps({'status': 1, 'logstatus': 1, 'error_message': "None", "data": json_data})
        return HttpResponse(final_json)

    def fetchErrorLogs(self, userID=None, data=None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        self.domain = data['virtualHost']
        page = data['page']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('logstatus', 0)

        # Use helper method to get correct log file path (handles child domains)
        # log_type 0 = error log
        fileName = self._get_log_file_path(self.domain, 0)

        command = 'ls -la %s' % fileName
        result = ProcessUtilities.outputExecutioner(command)

        if result.find('->') > -1:
            final_json = json.dumps(
                {'status': 0, 'logstatus': 0,
                 'error_message': "Symlink attack."})
            return HttpResponse(final_json)

        ## get Logs
        website = Websites.objects.get(domain=self.domain)

        output = virtualHostUtilities.getErrorLogs(fileName, page, website.externalApp)

        if output.find("1,None") > -1:
            final_json = json.dumps(
                {'status': 0, 'logstatus': 0, 'error_message': "Not able to fetch logs, see CyberPanel main log file!"})
            return HttpResponse(final_json)

        ## get log ends here.

        final_json = json.dumps({'status': 1, 'logstatus': 1, 'error_message': "None", "data": output})
        return HttpResponse(final_json)

    def getDataFromConfigFile(self, userID=None, data=None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        self.domain = data['virtualHost']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('configstatus', 0)

        command = 'cat %s' % ('/usr/local/lsws/conf/dvhost_redis.conf')

        if ProcessUtilities.outputExecutioner(command).find('127.0.0.1') == -1:
            filePath = installUtilities.Server_root_path + "/conf/vhosts/" + self.domain + "/vhost.conf"

            command = 'cat ' + filePath
            configData = ProcessUtilities.outputExecutioner(command, 'lsadm')

            if len(configData) == 0:
                status = {'status': 0, "configstatus": 0, "error_message": "Configuration file is currently empty!"}

                final_json = json.dumps(status)
                return HttpResponse(final_json)

        else:
            command = 'redis-cli get "vhost:%s"' % (self.domain)
            configData = ProcessUtilities.outputExecutioner(command)
            configData = '#### This configuration is fetched from redis as Redis-Mass Hosting is being used.\n%s' % (
                configData)

        status = {'status': 1, "configstatus": 1, "configData": configData}
        final_json = json.dumps(status)
        return HttpResponse(final_json)

    def resetVHostConfigToDefault(self, userID=None, data=None):
        """Reset vHost configuration to default template"""
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] != 1:
            return ACLManager.loadErrorJson('configstatus', 0)

        virtualHost = data['virtualHost']
        self.domain = virtualHost

        try:
            # Get the default vHost configuration template
            from plogical import vhostConfs
            
            # Determine if it's a child domain or main domain
            try:
                child_domain = ChildDomains.objects.get(domain=virtualHost)
                is_child = True
                master_domain = child_domain.master.domain
                admin_email = child_domain.master.adminEmail if child_domain.master.adminEmail else child_domain.master.admin.email
                path = child_domain.path
            except:
                is_child = False
                try:
                    website = Websites.objects.get(domain=virtualHost)
                    admin_email = website.adminEmail if website.adminEmail else website.admin.email
                except:
                    admin_email = "admin@" + virtualHost

            # Generate default configuration based on server type
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                if is_child:
                    # Use child domain template
                    default_config = vhostConfs.olsChildConf
                    default_config = default_config.replace('{virtualHostName}', virtualHost)
                    default_config = default_config.replace('{path}', path)
                    default_config = default_config.replace('{masterDomain}', master_domain)
                    default_config = default_config.replace('{adminEmails}', admin_email)
                    default_config = default_config.replace('{externalApp}', "".join(re.findall("[a-zA-Z]+", virtualHost))[:5] + str(randint(1000, 9999)))
                    default_config = default_config.replace('{externalAppMaster}', "".join(re.findall("[a-zA-Z]+", master_domain))[:5] + str(randint(1000, 9999)))
                    default_config = default_config.replace('{php}', '8.1')  # Default PHP version
                    default_config = default_config.replace('{open_basedir}', '')  # Default open_basedir setting
                else:
                    # Use main domain template
                    default_config = vhostConfs.olsMasterConf
                    default_config = default_config.replace('{virtualHostName}', virtualHost)
                    default_config = default_config.replace('{administratorEmail}', admin_email)
                    default_config = default_config.replace('{externalApp}', "".join(re.findall("[a-zA-Z]+", virtualHost))[:5] + str(randint(1000, 9999)))
                    default_config = default_config.replace('{php}', '8.1')  # Default PHP version
            else:
                # For other server types, use basic template
                default_config = f"""# Default vHost Configuration for {virtualHost}
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Basic configuration
# Add your custom configuration here
"""

            # Save the default configuration
            mailUtilities.checkHome()
            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            
            vhost = open(tempPath, "w")
            vhost.write(default_config)
            vhost.close()

            filePath = installUtilities.Server_root_path + "/conf/vhosts/" + virtualHost + "/vhost.conf"

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " saveVHostConfigs --path " + filePath + " --tempPath " + tempPath

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                status = {"configstatus": 1, "message": "vHost configuration reset to default successfully."}
            else:
                status = {"configstatus": 0, "error_message": f"Failed to reset configuration: {output}"}

            final_json = json.dumps(status)
            return HttpResponse(final_json)

        except Exception as e:
            status = {"configstatus": 0, "error_message": f"Error resetting configuration: {str(e)}"}
            final_json = json.dumps(status)
            return HttpResponse(final_json)

    def saveConfigsToFile(self, userID=None, data=None):

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] != 1:
            return ACLManager.loadErrorJson('configstatus', 0)

        configData = data['configData']
        self.domain = data['virtualHost']

        if len(configData) == 0:
            status = {"configstatus": 0, 'error_message': 'Error: you are trying to save empty vhost file, your website will stop working.'}

            final_json = json.dumps(status)
            return HttpResponse(final_json)


        command = 'cat %s' % ('/usr/local/lsws/conf/dvhost_redis.conf')

        if ProcessUtilities.outputExecutioner(command).find('127.0.0.1') == -1:

            mailUtilities.checkHome()

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            vhost = open(tempPath, "w")

            vhost.write(configData)

            vhost.close()

            ## writing data temporary to file

            filePath = installUtilities.Server_root_path + "/conf/vhosts/" + self.domain + "/vhost.conf"

            ## save configuration data

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " saveVHostConfigs --path " + filePath + " --tempPath " + tempPath

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                status = {"configstatus": 1}

                final_json = json.dumps(status)
                return HttpResponse(final_json)
            else:
                data_ret = {'configstatus': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

                ## save configuration data ends
        else:
            command = "redis-cli set vhost:%s '%s'" % (self.domain, configData.replace(
                '#### This configuration is fetched from redis as Redis-Mass Hosting is being used.\n', ''))
            ProcessUtilities.executioner(command)

            status = {"configstatus": 1}

            final_json = json.dumps(status)
            return HttpResponse(final_json)

    def getRewriteRules(self, userID=None, data=None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        self.domain = data['virtualHost']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('rewriteStatus', 0)

        try:
            childDom = ChildDomains.objects.get(domain=self.domain)
            filePath = childDom.path + '/.htaccess'
            externalApp = childDom.master.externalApp
        except:
            website = Websites.objects.get(domain=self.domain)
            externalApp = website.externalApp
            filePath = "/home/" + self.domain + "/public_html/.htaccess"

        try:
            command = 'cat %s' % (filePath)
            rewriteRules = ProcessUtilities.outputExecutioner(command, externalApp)

            if len(rewriteRules) == 0:
                status = {"rewriteStatus": 1, "error_message": "Rules file is currently empty"}
                final_json = json.dumps(status)
                return HttpResponse(final_json)

            status = {"rewriteStatus": 1, "rewriteRules": rewriteRules}

            final_json = json.dumps(status)
            return HttpResponse(final_json)

        except BaseException as msg:
            status = {"rewriteStatus": 1, "error_message": str(msg), "rewriteRules": ""}
            final_json = json.dumps(status)
            return HttpResponse(final_json)

    def saveRewriteRules(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            self.domain = data['virtualHost']
            rewriteRules = data['rewriteRules'].encode('utf-8')

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('rewriteStatus', 0)

            ## writing data temporary to file

            mailUtilities.checkHome()
            tempPath = "/tmp/" + str(randint(1000, 9999))
            vhost = open(tempPath, "wb")
            vhost.write(rewriteRules)
            vhost.close()

            ## writing data temporary to file

            try:
                childDomain = ChildDomains.objects.get(domain=self.domain)
                filePath = childDomain.path + '/.htaccess'
                externalApp = childDomain.master.externalApp
            except:
                filePath = "/home/" + self.domain + "/public_html/.htaccess"
                website = Websites.objects.get(domain=self.domain)
                externalApp = website.externalApp

            ## save configuration data

            command = 'cp %s %s' % (tempPath, filePath)
            ProcessUtilities.executioner(command, externalApp)

            command = 'rm -f %s' % (tempPath)
            ProcessUtilities.executioner(command, 'cyberpanel')

            installUtilities.reStartLiteSpeedSocket()
            status = {"rewriteStatus": 1, 'error_message': 'None'}
            final_json = json.dumps(status)
            return HttpResponse(final_json)
        except BaseException as msg:
            status = {"rewriteStatus": 0, 'error_message': str(msg)}
            final_json = json.dumps(status)
            return HttpResponse(final_json)

    def saveSSL(self, userID=None, data=None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        self.domain = data['virtualHost']
        key = data['key']
        cert = data['cert']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('sslStatus', 0)

        mailUtilities.checkHome()

        ## writing data temporary to file

        tempKeyPath = "/home/cyberpanel/" + str(randint(1000, 9999))
        vhost = open(tempKeyPath, "w")
        vhost.write(key)
        vhost.close()

        tempCertPath = "/home/cyberpanel/" + str(randint(1000, 9999))
        vhost = open(tempCertPath, "w")
        vhost.write(cert)
        vhost.close()

        ## writing data temporary to file

        execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
        execPath = execPath + " saveSSL --virtualHostName " + self.domain + " --tempKeyPath " + tempKeyPath + " --tempCertPath " + tempCertPath
        output = ProcessUtilities.outputExecutioner(execPath)

        if output.find("1,None") > -1:
            data_ret = {'sslStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        else:
            logging.CyberCPLogFileWriter.writeToFile(
                output)
            data_ret = {'sslStatus': 0, 'error_message': output}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def changePHP(self, userID=None, data=None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        self.domain = data['childDomain']
        phpVersion = data['phpSelection']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('changePHP', 0)

        confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + self.domain
        completePathToConfigFile = confPath + "/vhost.conf"

        execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
        execPath = execPath + " changePHP --phpVersion '" + phpVersion + "' --path " + completePathToConfigFile
        ProcessUtilities.popenExecutioner(execPath)

        try:
            website = Websites.objects.get(domain=self.domain)
            website.phpSelection = data['phpSelection']
            website.save()

            ### check if there are any alias domains under the main website and then change php for them too

            for alias in website.childdomains_set.filter(alais=1):

                try:

                    confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + alias.domain
                    completePathToConfigFile = confPath + "/vhost.conf"
                    execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                    execPath = execPath + " changePHP --phpVersion '" + phpVersion + "' --path " + completePathToConfigFile
                    ProcessUtilities.popenExecutioner(execPath)
                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile(f'Error changing PHP for alias: {str(msg)}')


        except:
            website = ChildDomains.objects.get(domain=self.domain)
            website.phpSelection = data['phpSelection']
            website.save()

        data_ret = {'status': 1, 'changePHP': 1, 'error_message': "None"}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    def getWebsiteCron(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('getWebsiteCron', 0)

            website = Websites.objects.get(domain=self.domain)

            if Websites.objects.filter(domain=self.domain).exists():
                pass
            else:
                dic = {'getWebsiteCron': 0, 'error_message': 'You do not own this domain'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

            CronUtil.CronPrem(1)

            crons = []

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/cronUtil.py"
            execPath = execPath + " getWebsiteCron --externalApp " + website.externalApp

            f = ProcessUtilities.outputExecutioner(execPath, website.externalApp)

            CronUtil.CronPrem(0)

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                cronPath = "/var/spool/cron/" + website.externalApp
            else:
                cronPath = "/var/spool/cron/crontabs/" + website.externalApp

            if f.find('Permission denied') > -1:
                command = 'chmod 644 %s' % (cronPath)
                ProcessUtilities.executioner(command)

                command = 'chown %s:%s %s' % (website.externalApp, website.externalApp, cronPath)
                ProcessUtilities.executioner(command)

                f = ProcessUtilities.outputExecutioner(execPath, website.externalApp)

            if f.find("0,CyberPanel,") > -1:
                data_ret = {'getWebsiteCron': 0, "user": website.externalApp, "crons": {}}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            counter = 0
            for line in f.split("\n"):
                if line:
                    split = line.split(" ", 5)
                    if len(split) == 6:
                        counter += 1
                        crons.append({"line": counter,
                                      "minute": split[0],
                                      "hour": split[1],
                                      "monthday": split[2],
                                      "month": split[3],
                                      "weekday": split[4],
                                      "command": split[5]})

            data_ret = {'getWebsiteCron': 1, "user": website.externalApp, "crons": crons}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            dic = {'getWebsiteCron': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def getCronbyLine(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            line = data['line']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('getWebsiteCron', 0)

            if Websites.objects.filter(domain=self.domain).exists():
                pass
            else:
                dic = {'getWebsiteCron': 0, 'error_message': 'You do not own this domain'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

            line -= 1
            website = Websites.objects.get(domain=self.domain)

            try:
                CronUtil.CronPrem(1)
                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/cronUtil.py"
                execPath = execPath + " getWebsiteCron --externalApp " + website.externalApp

                f = ProcessUtilities.outputExecutioner(execPath, website.externalApp)
                CronUtil.CronPrem(0)
            except subprocess.CalledProcessError as error:
                dic = {'getWebsiteCron': 0, 'error_message': 'Unable to access Cron file'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

            f = f.split("\n")
            cron = f[line]

            cron = cron.split(" ", 5)
            if len(cron) != 6:
                dic = {'getWebsiteCron': 0, 'error_message': 'Cron line incorrect'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

            data_ret = {"getWebsiteCron": 1,
                        "user": website.externalApp,
                        "cron": {
                            "minute": cron[0],
                            "hour": cron[1],
                            "monthday": cron[2],
                            "month": cron[3],
                            "weekday": cron[4],
                            "command": cron[5],
                        },
                        "line": line}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)
        except BaseException as msg:
            print(msg)
            dic = {'getWebsiteCron': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def saveCronChanges(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            line = data['line']

            minute = data['minute']
            hour = data['hour']
            monthday = data['monthday']
            month = data['month']
            weekday = data['weekday']
            command = data['cronCommand']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('getWebsiteCron', 0)

            website = Websites.objects.get(domain=self.domain)

            finalCron = "%s %s %s %s %s %s" % (minute, hour, monthday, month, weekday, command)

            CronUtil.CronPrem(1)

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/cronUtil.py"
            execPath = execPath + " saveCronChanges --externalApp " + website.externalApp + " --line " + str(
                line) + " --finalCron '" + finalCron + "'"
            output = ProcessUtilities.outputExecutioner(execPath, website.externalApp)
            CronUtil.CronPrem(0)

            if output.find("1,") > -1:
                # Restart cron service to apply changes immediately
                restart_success, restart_error = CronUtil.restartCronService()
                
                if not restart_success:
                    # Strict mode: return error response if restart fails
                    dic = {'getWebsiteCron': 0, 'error_message': f'Cron job modified but service restart failed: {restart_error}. Please manually restart cron service.'}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)
                
                data_ret = {"getWebsiteCron": 1,
                            "user": website.externalApp,
                            "cron": finalCron,
                            "line": line}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)
            else:
                dic = {'getWebsiteCron': 0, 'error_message': output}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

        except BaseException as msg:
            dic = {'getWebsiteCron': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def remCronbyLine(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            line = data['line']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('addNewCron', 0)

            website = Websites.objects.get(domain=self.domain)

            CronUtil.CronPrem(1)

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/cronUtil.py"
            execPath = execPath + " remCronbyLine --externalApp " + website.externalApp + " --line " + str(
                line)
            output = ProcessUtilities.outputExecutioner(execPath, website.externalApp)

            CronUtil.CronPrem(0)

            if output.find("1,") > -1:
                # Restart cron service to apply changes immediately
                restart_success, restart_error = CronUtil.restartCronService()
                
                if not restart_success:
                    # Strict mode: return error response if restart fails
                    dic = {'remCronbyLine': 0, 'error_message': f'Cron job removed but service restart failed: {restart_error}. Please manually restart cron service.'}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)
                
                data_ret = {"remCronbyLine": 1,
                            "user": website.externalApp,
                            "removeLine": output.split(',')[1],
                            "line": line}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)
            else:
                dic = {'remCronbyLine': 0, 'error_message': output}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)


        except BaseException as msg:
            dic = {'remCronbyLine': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def addNewCron(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            minute = data['minute']
            hour = data['hour']
            monthday = data['monthday']
            month = data['month']
            weekday = data['weekday']
            command = data['cronCommand']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('addNewCron', 0)

            website = Websites.objects.get(domain=self.domain)

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                cronPath = "/var/spool/cron/" + website.externalApp
            else:
                cronPath = "/var/spool/cron/crontabs/" + website.externalApp

            commandT = 'touch %s' % (cronPath)
            ProcessUtilities.executioner(commandT, 'root')
            commandT = 'chown %s:%s %s' % (website.externalApp, website.externalApp, cronPath)
            ProcessUtilities.executioner(commandT, 'root')

            CronUtil.CronPrem(1)

            finalCron = "%s %s %s %s %s %s" % (minute, hour, monthday, month, weekday, command)

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/cronUtil.py"
            execPath = execPath + " addNewCron --externalApp " + website.externalApp + " --finalCron '" + finalCron + "'"
            output = ProcessUtilities.outputExecutioner(execPath, website.externalApp)

            # Set proper permissions for Ubuntu/Debian
            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                command = 'chmod 600 %s' % (cronPath)
                ProcessUtilities.executioner(command)

            CronUtil.CronPrem(0)

            if output.find("1,") > -1:
                # Restart cron service to apply changes immediately (all distributions)
                restart_success, restart_error = CronUtil.restartCronService()
                
                if not restart_success:
                    # Strict mode: return error response if restart fails
                    dic = {'addNewCron': 0, 'error_message': f'Cron job added but service restart failed: {restart_error}. Please manually restart cron service.'}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                data_ret = {"addNewCron": 1,
                            "user": website.externalApp,
                            "cron": finalCron}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)
            else:
                dic = {'addNewCron': 0, 'error_message': output}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)


        except BaseException as msg:
            dic = {'addNewCron': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def submitAliasCreation(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['masterDomain']
            aliasDomain = data['aliasDomain']
            ssl = data['ssl']

            if not validators.domain(aliasDomain):
                data_ret = {'status': 0, 'createAliasStatus': 0, 'error_message': "Invalid domain."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('createAliasStatus', 0)

            sslpath = "/home/" + self.domain + "/public_html"

            ## Create Configurations

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " createAlias --masterDomain " + self.domain + " --aliasDomain " + aliasDomain + " --ssl " + str(
                ssl) + " --sslPath " + sslpath + " --administratorEmail " + admin.email + ' --websiteOwner ' + admin.userName

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                pass
            else:
                data_ret = {'createAliasStatus': 0, 'error_message': output, "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            ## Create Configurations ends here

            data_ret = {'createAliasStatus': 1, 'error_message': "None", "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)



        except BaseException as msg:
            data_ret = {'createAliasStatus': 0, 'error_message': str(msg), "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def issueAliasSSL(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['masterDomain']
            aliasDomain = data['aliasDomain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('sslStatus', 0)

            if ACLManager.AliasDomainCheck(currentACL, aliasDomain, self.domain) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('sslStatus', 0)

            sslpath = "/home/" + self.domain + "/public_html"

            ## Create Configurations

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " issueAliasSSL --masterDomain " + self.domain + " --aliasDomain " + aliasDomain + " --sslPath " + sslpath + " --administratorEmail " + admin.email

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                data_ret = {'sslStatus': 1, 'error_message': "None", "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'sslStatus': 0, 'error_message': output, "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'sslStatus': 0, 'error_message': str(msg), "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def delateAlias(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['masterDomain']
            aliasDomain = data['aliasDomain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('deleteAlias', 0)

            if ACLManager.AliasDomainCheck(currentACL, aliasDomain, self.domain) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('deleteAlias', 0)

            ## Create Configurations

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " deleteAlias --masterDomain " + self.domain + " --aliasDomain " + aliasDomain
            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                data_ret = {'deleteAlias': 1, 'error_message': "None", "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'deleteAlias': 0, 'error_message': output, "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'deleteAlias': 0, 'error_message': str(msg), "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def changeOpenBasedir(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            self.domain = data['domainName']
            openBasedirValue = data['openBasedirValue']

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('changeOpenBasedir', 0)

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " changeOpenBasedir --virtualHostName '" + self.domain + "' --openBasedirValue " + openBasedirValue
            output = ProcessUtilities.popenExecutioner(execPath)

            data_ret = {'status': 1, 'changeOpenBasedir': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'changeOpenBasedir': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def wordpressInstall(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        proc = httpProc(request, 'websiteFunctions/installWordPress.html', {'domainName': self.domain})
        return proc.render()

    def installWordpress(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['admin'] = admin
            extraArgs['domainName'] = data['domain']
            extraArgs['home'] = data['home']
            extraArgs['blogTitle'] = data['blogTitle']
            extraArgs['adminUser'] = data['adminUser']
            extraArgs['adminPassword'] = data['passwordByPass']
            extraArgs['adminEmail'] = data['adminEmail']
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            if data['home'] == '0':
                extraArgs['path'] = data['path']

            background = ApplicationInstaller('wordpress', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def installWordpressStatus(self, userID=None, data=None):
        try:
            statusFile = data['statusFile']

            if ACLManager.CheckStatusFilleLoc(statusFile):
                pass
            else:
                data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "100",
                            'currentStatus': 'Invalid status file.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            statusData = ProcessUtilities.outputExecutioner("cat " + statusFile).splitlines()

            lastLine = statusData[-1]

            if lastLine.find('[200]') > -1:
                command = 'rm -f ' + statusFile
                subprocess.call(shlex.split(command))
                data_ret = {'abort': 1, 'installStatus': 1, 'installationProgress': "100",
                            'currentStatus': 'Successfully Installed.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            elif lastLine.find('[404]') > -1:
                data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "0",
                            'error_message': ProcessUtilities.outputExecutioner("cat " + statusFile).splitlines()}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                progress = lastLine.split(',')
                currentStatus = progress[0]
                try:
                    installationProgress = progress[1]
                except:
                    installationProgress = 0
                data_ret = {'abort': 0, 'installStatus': 0, 'installationProgress': installationProgress,
                            'currentStatus': currentStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'abort': 0, 'installStatus': 0, 'installationProgress': "0", 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def joomlaInstall(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        proc = httpProc(request, 'websiteFunctions/installJoomla.html', {'domainName': self.domain})
        return proc.render()

    def installJoomla(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            extraArgs = {}

            extraArgs['password'] = data['passwordByPass']
            extraArgs['prefix'] = data['prefix']
            extraArgs['domain'] = data['domain']
            extraArgs['home'] = data['home']
            extraArgs['siteName'] = data['siteName']
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            mailUtilities.checkHome()

            if data['home'] == '0':
                extraArgs['path'] = data['path']

            background = ApplicationInstaller('joomla', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

            ## Installation ends

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def setupGit(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        website = Websites.objects.get(domain=self.domain)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        path = '/home/cyberpanel/' + self.domain + '.git'

        if os.path.exists(path):
            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]

            port = ProcessUtilities.fetchCurrentPort()

            webhookURL = 'https://' + ipAddress + ':%s/websites/' % (port) + self.domain + '/gitNotify'

            proc = httpProc(request, 'websiteFunctions/setupGit.html',
                            {'domainName': self.domain, 'installed': 1, 'webhookURL': webhookURL})
            return proc.render()
        else:

            command = "ssh-keygen -f /home/%s/.ssh/%s -t rsa -N ''" % (self.domain, website.externalApp)
            ProcessUtilities.executioner(command, website.externalApp)

            ###

            configContent = """Host github.com
IdentityFile /home/%s/.ssh/%s
StrictHostKeyChecking no
""" % (self.domain, website.externalApp)

            path = "/home/cyberpanel/config"
            writeToFile = open(path, 'w')
            writeToFile.writelines(configContent)
            writeToFile.close()

            command = 'mv %s /home/%s/.ssh/config' % (path, self.domain)
            ProcessUtilities.executioner(command)

            command = 'chown %s:%s /home/%s/.ssh/config' % (website.externalApp, website.externalApp, self.domain)
            ProcessUtilities.executioner(command)

            command = 'cat /home/%s/.ssh/%s.pub' % (self.domain, website.externalApp)
            deploymentKey = ProcessUtilities.outputExecutioner(command, website.externalApp)

        proc = httpProc(request, 'websiteFunctions/setupGit.html',
                        {'domainName': self.domain, 'deploymentKey': deploymentKey, 'installed': 0})
        return proc.render()

    def setupGitRepo(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['admin'] = admin
            extraArgs['domainName'] = data['domain']
            extraArgs['username'] = data['username']
            extraArgs['reponame'] = data['reponame']
            extraArgs['branch'] = data['branch']
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))
            extraArgs['defaultProvider'] = data['defaultProvider']

            background = ApplicationInstaller('git', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def gitNotify(self, userID=None, data=None):
        try:

            extraArgs = {}
            extraArgs['domain'] = self.domain

            background = ApplicationInstaller('pull', extraArgs)
            background.start()

            data_ret = {'pulled': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'pulled': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def detachRepo(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['domainName'] = data['domain']
            extraArgs['admin'] = admin

            background = ApplicationInstaller('detach', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def changeBranch(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['domainName'] = data['domain']
            extraArgs['githubBranch'] = data['githubBranch']
            extraArgs['admin'] = admin

            background = ApplicationInstaller('changeBranch', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def installPrestaShop(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        proc = httpProc(request, 'websiteFunctions/installPrestaShop.html', {'domainName': self.domain})
        return proc.render()

    def installMagento(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        proc = httpProc(request, 'websiteFunctions/installMagento.html', {'domainName': self.domain})
        return proc.render()

    def magentoInstall(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['admin'] = admin
            extraArgs['domainName'] = data['domain']
            extraArgs['home'] = data['home']
            extraArgs['firstName'] = data['firstName']
            extraArgs['lastName'] = data['lastName']
            extraArgs['username'] = data['username']
            extraArgs['email'] = data['email']
            extraArgs['password'] = data['passwordByPass']
            extraArgs['sampleData'] = data['sampleData']
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            if data['home'] == '0':
                extraArgs['path'] = data['path']

            background = ApplicationInstaller('magento', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

            ## Installation ends

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def installMautic(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        proc = httpProc(request, 'websiteFunctions/installMautic.html', {'domainName': self.domain})
        return proc.render()

    def mauticInstall(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            #### Before installing mautic change php to 8.1

            completePathToConfigFile = f'/usr/local/lsws/conf/vhosts/{self.domain}/vhost.conf'

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " changePHP --phpVersion 'PHP 8.1' --path " + completePathToConfigFile
            ProcessUtilities.executioner(execPath)

            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['admin'] = admin
            extraArgs['domainName'] = data['domain']
            extraArgs['home'] = data['home']
            extraArgs['username'] = data['username']
            extraArgs['email'] = data['email']
            extraArgs['password'] = data['passwordByPass']
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            if data['home'] == '0':
                extraArgs['path'] = data['path']

            background = ApplicationInstaller('mautic', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

            ## Installation ends

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def prestaShopInstall(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['admin'] = admin
            extraArgs['domainName'] = data['domain']
            extraArgs['home'] = data['home']
            extraArgs['shopName'] = data['shopName']
            extraArgs['firstName'] = data['firstName']
            extraArgs['lastName'] = data['lastName']
            extraArgs['databasePrefix'] = data['databasePrefix']
            extraArgs['email'] = data['email']
            extraArgs['password'] = data['passwordByPass']
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            if data['home'] == '0':
                extraArgs['path'] = data['path']

            #### Before installing Prestashop change php to 8.3

            completePathToConfigFile = f'/usr/local/lsws/conf/vhosts/{self.domain}/vhost.conf'

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " changePHP --phpVersion 'PHP 8.3' --path " + completePathToConfigFile
            ProcessUtilities.executioner(execPath)

            background = ApplicationInstaller('prestashop', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

            ## Installation ends

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def createWebsiteAPI(self, data=None):
        try:

            adminUser = data['adminUser']
            adminPass = data['adminPass']
            adminEmail = data['ownerEmail']
            websiteOwner = data['websiteOwner']
            ownerPassword = data['ownerPassword']
            data['ssl'] = 1
            data['dkimCheck'] = 1
            data['openBasedir'] = 1
            data['adminEmail'] = data['ownerEmail']

            try:
                data['phpSelection'] = data['phpSelection']
            except:
                data['phpSelection'] = "PHP 7.4"

            data['package'] = data['packageName']
            try:
                websitesLimit = data['websitesLimit']
            except:
                websitesLimit = 1

            try:
                apiACL = data['acl']
            except:
                apiACL = 'user'

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):

                if adminEmail is None:
                    data['adminEmail'] = "example@example.org"

                try:
                    acl = ACL.objects.get(name=apiACL)
                    websiteOwn = Administrator(userName=websiteOwner,
                                               password=hashPassword.hash_password(ownerPassword),
                                               email=adminEmail, type=3, owner=admin.pk,
                                               initWebsitesLimit=websitesLimit, acl=acl, api=1)
                    websiteOwn.save()
                except BaseException:
                    pass

            else:
                data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            return self.submitWebsiteCreation(admin.pk, data)

        except BaseException as msg:
            data_ret = {'createWebSiteStatus': 0, 'error_message': str(msg), "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def searchWebsitesJson(self, currentlACL, userID, searchTerm):

        websites = ACLManager.searchWebsiteObjects(currentlACL, userID, searchTerm)

        json_data = []

        try:
            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to read machine IP, error:" + str(msg))
            ipAddress = "192.168.100.1"

        for items in websites:
            if items.state == 0:
                state = "Suspended"
            else:
                state = "Active"

            DiskUsage, DiskUsagePercentage, bwInMB, bwUsage = virtualHostUtilities.FindStats(items)

            vhFile = f'/usr/local/lsws/conf/vhosts/{items.domain}/vhost.conf'

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(vhFile)

            try:
                from plogical.phpUtilities import phpUtilities
                PHPVersionActual = phpUtilities.WrapGetPHPVersionFromFileToGetVersionWithPHP(vhFile)
            except:
                PHPVersionActual = 'PHP 8.1'

            diskUsed = "%sMB" % str(DiskUsage)

            # Get WordPress sites for this website
            wp_sites = []
            try:
                wp_sites = WPSites.objects.filter(owner=items)
                wp_sites = [{
                    'id': wp.id,
                    'title': wp.title,
                    'url': wp.FinalURL,
                    'version': wp.version if hasattr(wp, 'version') else 'Unknown',
                    'phpVersion': wp.phpVersion if hasattr(wp, 'phpVersion') else 'Unknown'
                } for wp in wp_sites]
            except:
                pass

            json_data.append({
                'domain': items.domain,
                'adminEmail': items.adminEmail,
                'ipAddress': ipAddress,
                'admin': items.admin.userName,
                'package': items.package.packageName,
                'state': state,
                'diskUsed': diskUsed,
                'phpVersion': PHPVersionActual,
                'wp_sites': wp_sites
            })

        return json.dumps(json_data)

    def findWebsitesJson(self, currentACL, userID, pageNumber):
        finalPageNumber = ((pageNumber * 10)) - 10
        endPageNumber = finalPageNumber + 10
        websites = ACLManager.findWebsiteObjects(currentACL, userID)[finalPageNumber:endPageNumber]

        json_data = "["
        checker = 0

        try:
            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to read machine IP, error:" + str(msg))
            ipAddress = "192.168.100.1"

        for items in websites:
            if items.state == 0:
                state = "Suspended"
            else:
                state = "Active"

            DiskUsage, DiskUsagePercentage, bwInMB, bwUsage = virtualHostUtilities.FindStats(items)

            diskUsed = "%sMB" % str(DiskUsage)

            dic = {'domain': items.domain, 'adminEmail': items.adminEmail, 'ipAddress': ipAddress,
                   'admin': items.admin.userName, 'package': items.package.packageName, 'state': state,
                   'diskUsed': diskUsed}

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        return json_data

    def websitePagination(self, currentACL, userID):
        websites = ACLManager.findAllSites(currentACL, userID)

        pages = float(len(websites)) / float(10)
        pagination = []

        if pages <= 1.0:
            pages = 1
            pagination.append('<li><a href="\#"></a></li>')
        else:
            pages = ceil(pages)
            finalPages = int(pages) + 1

            for i in range(1, finalPages):
                pagination.append('<li><a href="\#">' + str(i) + '</a></li>')

        return pagination

    def DockersitePagination(self, currentACL, userID):
        websites = DockerSites.objects.all()

        pages = float(len(websites)) / float(10)
        pagination = []

        if pages <= 1.0:
            pages = 1
            pagination.append('<li><a href="\#"></a></li>')
        else:
            pages = ceil(pages)
            finalPages = int(pages) + 1

            for i in range(1, finalPages):
                pagination.append('<li><a href="\#">' + str(i) + '</a></li>')

        return pagination

    def getSwitchStatus(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            try:
                globalData = data['global']

                data = {}
                data['status'] = 1

                if os.path.exists('/etc/httpd'):
                    data['server'] = 1
                else:
                    data['server'] = 0

                json_data = json.dumps(data)
                return HttpResponse(json_data)
            except:
                pass

            self.domain = data['domainName']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                finalConfPath = ApacheVhost.configBasePath + self.domain + '.conf'

                if os.path.exists(finalConfPath):

                    phpPath = ApacheVhost.whichPHPExists(self.domain)
                    if phpPath is None:
                        # If PHP path is not found, return error response
                        data_ret = {'status': 0, 'saveStatus': 0, 'error_message': 'PHP configuration file not found for this domain'}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    
                    command = 'sudo cat ' + phpPath
                    phpConf = ProcessUtilities.outputExecutioner(command).splitlines()
                    pmMaxChildren = phpConf[8].split(' ')[2]
                    pmStartServers = phpConf[9].split(' ')[2]
                    pmMinSpareServers = phpConf[10].split(' ')[2]
                    pmMaxSpareServers = phpConf[11].split(' ')[2]

                    data = {}
                    data['status'] = 1

                    data['server'] = WebsiteManager.apache
                    data['pmMaxChildren'] = pmMaxChildren
                    data['pmStartServers'] = pmStartServers
                    data['pmMinSpareServers'] = pmMinSpareServers
                    data['pmMaxSpareServers'] = pmMaxSpareServers
                    data['phpPath'] = phpPath
                    config_output = ProcessUtilities.outputExecutioner(f'cat {finalConfPath}')
                    data['configData'] = config_output if config_output is not None else ''
                else:
                    data = {}
                    data['status'] = 1
                    data['server'] = WebsiteManager.ols

            else:
                data = {}
                data['status'] = 1
                data['server'] = WebsiteManager.lsws

            json_data = json.dumps(data)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def switchServer(self, userID=None, data=None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        domainName = data['domainName']
        phpVersion = data['phpSelection']
        server = data['server']

        if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))
        execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
        execPath = execPath + " switchServer --phpVersion '" + phpVersion + "' --server " + str(
            server) + " --virtualHostName " + domainName + " --tempStatusPath " + tempStatusPath
        ProcessUtilities.popenExecutioner(execPath)

        time.sleep(3)

        data_ret = {'status': 1, 'tempStatusPath': tempStatusPath}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    def tuneSettings(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            domainName = data['domainName']
            pmMaxChildren = data['pmMaxChildren']
            pmStartServers = data['pmStartServers']
            pmMinSpareServers = data['pmMinSpareServers']
            pmMaxSpareServers = data['pmMaxSpareServers']
            phpPath = data['phpPath']

            if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            if int(pmStartServers) < int(pmMinSpareServers) or int(pmStartServers) > int(pmMinSpareServers):
                data_ret = {'status': 0,
                            'error_message': 'pm.start_servers must not be less than pm.min_spare_servers and not greater than pm.max_spare_servers.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if int(pmMinSpareServers) > int(pmMaxSpareServers):
                data_ret = {'status': 0,
                            'error_message': 'pm.max_spare_servers must not be less than pm.min_spare_servers'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp
            except:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                sockPath = '/var/run/php-fpm/'
                group = 'nobody'
            else:
                sockPath = '/var/run/php/'
                group = 'nogroup'

            phpFPMConf = vhostConfs.phpFpmPoolReplace
            phpFPMConf = phpFPMConf.replace('{externalApp}', externalApp)
            phpFPMConf = phpFPMConf.replace('{pmMaxChildren}', pmMaxChildren)
            phpFPMConf = phpFPMConf.replace('{pmStartServers}', pmStartServers)
            phpFPMConf = phpFPMConf.replace('{pmMinSpareServers}', pmMinSpareServers)
            phpFPMConf = phpFPMConf.replace('{pmMaxSpareServers}', pmMaxSpareServers)
            phpFPMConf = phpFPMConf.replace('{www}', "".join(re.findall("[a-zA-Z]+", domainName))[:7])
            phpFPMConf = phpFPMConf.replace('{Sock}', domainName)
            phpFPMConf = phpFPMConf.replace('{sockPath}', sockPath)
            phpFPMConf = phpFPMConf.replace('{group}', group)

            writeToFile = open(tempStatusPath, 'w')
            writeToFile.writelines(phpFPMConf)
            writeToFile.close()

            command = 'sudo mv %s %s' % (tempStatusPath, phpPath)
            ProcessUtilities.executioner(command)

            phpPath = phpPath.split('/')

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'PHP path in tune settings {phpPath}')

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                if phpPath[1] == 'etc':
                    phpVersion = phpPath[4][3] + phpPath[4][4]
                    phpVersion = f'PHP {phpPath[4][3]}.{phpPath[4][4]}'
                else:
                    phpVersion = phpPath[3][3] + phpPath[3][4]
                    phpVersion = f'PHP {phpPath[3][3]}.{phpPath[3][4]}'
            else:
                phpVersion = f'PHP {phpPath[2]}'

            # php = PHPManager.getPHPString(phpVersion)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'PHP Version in tune settings {phpVersion}')

            phpService = ApacheVhost.DecideFPMServiceName(phpVersion)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'PHP service in tune settings {phpService}')

            command = f"systemctl stop {phpService}"
            ProcessUtilities.normalExecutioner(command)

            command = f"systemctl restart {phpService}"
            ProcessUtilities.normalExecutioner(command)

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def sshAccess(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        website = Websites.objects.get(domain=self.domain)
        externalApp = website.externalApp

        #### update jwt secret if needed

        import secrets
        import re
        import os
        from plogical.processUtilities import ProcessUtilities

        fastapi_file = '/usr/local/CyberCP/fastapi_ssh_server.py'
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
        try:
            
            content = ProcessUtilities.outputExecutioner(f'cat {fastapi_file}')
            if 'REPLACE_ME_WITH_INSTALLER' in content:
                new_secret = secrets.token_urlsafe(32)
                
                sed_cmd = f"sed -i 's|JWT_SECRET = \"REPLACE_ME_WITH_INSTALLER\"|JWT_SECRET = \"{new_secret}\"|' '{fastapi_file}'"
                ProcessUtilities.outputExecutioner(sed_cmd)
                
                command = 'systemctl restart fastapi_ssh_server'
                ProcessUtilities.outputExecutioner(command)
        except Exception:
            CyberCPLogFileWriter.writeLog(f"Failed to update JWT secret: {e}")
            pass

        #####

        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
        # Ensure FastAPI SSH server systemd service file is in place
        try:
            service_path = '/etc/systemd/system/fastapi_ssh_server.service'
            local_service_path = 'fastapi_ssh_server.service'
            check_service = ProcessUtilities.outputExecutioner(f'test -f {service_path} && echo exists || echo missing')
            if 'missing' in check_service:
                ProcessUtilities.outputExecutioner(f'cp /usr/local/CyberCP/fastapi_ssh_server.service {service_path}')
                ProcessUtilities.outputExecutioner('systemctl daemon-reload')
        except Exception as e:
            CyberCPLogFileWriter.writeLog(f"Failed to copy or reload fastapi_ssh_server.service: {e}")

        # Ensure FastAPI SSH server is running using ProcessUtilities
        try:
            ProcessUtilities.outputExecutioner('systemctl is-active --quiet fastapi_ssh_server')
            ProcessUtilities.outputExecutioner('systemctl enable --now fastapi_ssh_server')
            ProcessUtilities.outputExecutioner('systemctl start fastapi_ssh_server')

            csfPath = '/etc/csf'

            sshPort = '8888'

            if os.path.exists(csfPath):
                    dataIn = {'protocol': 'TCP_IN', 'ports': sshPort}

                    # self.modifyPorts is a method in the firewallManager.py file so how can we call it here?
                    # we need to call the method from the firewallManager.py file
                    from firewall.firewallManager import FirewallManager
                    firewallManager = FirewallManager()
                    firewallManager.modifyPorts(dataIn)
                    dataIn = {'protocol': 'TCP_OUT', 'ports': sshPort}
                    firewallManager.modifyPorts(dataIn)
            else:
                from plogical.firewallUtilities import FirewallUtilities
                from firewall.models import FirewallRules
                try:
                    updateFW = FirewallRules.objects.get(name="WebTerminalPort")
                    FirewallUtilities.deleteRule("tcp", updateFW.port, "0.0.0.0/0")
                    updateFW.port = sshPort
                    updateFW.save()
                    FirewallUtilities.addRule('tcp', sshPort, "0.0.0.0/0")
                except:
                    try:
                        newFireWallRule = FirewallRules(name="WebTerminalPort", port=sshPort, proto="tcp")
                        newFireWallRule.save()
                        FirewallUtilities.addRule('tcp', sshPort, "0.0.0.0/0")
                    except BaseException as msg:
                        CyberCPLogFileWriter.writeToFile(str(msg))

        except Exception as e:
            CyberCPLogFileWriter.writeLog(f"Failed to ensure fastapi_ssh_server is running: {e}")

        # Add-on check logic
        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        data = {
            "name": "all",
            "IP": ACLManager.GetServerIP()
        }
        import requests
        import json
        try:
            response = requests.post(url, data=json.dumps(data))
            Status = response.json().get('status', 0)
        except Exception:
            Status = 0
        has_addons = (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent

        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter

        #CyberCPLogFileWriter.writeToFile(f"has_addons: {has_addons}")

        # SSL check
        cert_path = '/usr/local/lscp/conf/cert.pem'
        is_selfsigned = False
        ssl_issue_link = '/manageSSL/sslForHostName'
        try:
            import OpenSSL
            cert_content = ProcessUtilities.outputExecutioner(f'cat {cert_path}')
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_content)
            ssl_provider = cert.get_issuer().get_components()[1][1].decode('utf-8')
            CyberCPLogFileWriter.writeToFile(f"ssl_provider: {ssl_provider}")
            if ssl_provider == 'Denial':
                is_selfsigned = True
            else:
                is_selfsigned = False
        except Exception as e:
            is_selfsigned = True  # If cert missing or unreadable, treat as self-signed
            CyberCPLogFileWriter.writeToFile(f"is_selfsigned: {is_selfsigned}. Error: {str(e)}")

        # Detect if accessed via IP
        accessed_via_ip = False
        try:
            host = request.get_host().split(':')[0]  # Remove port if present
            try:
                ipaddress.ip_address(host)
                accessed_via_ip = True
            except ValueError:
                accessed_via_ip = False
        except Exception as e:
            accessed_via_ip = False
            CyberCPLogFileWriter.writeToFile(f"Error detecting accessed_via_ip: {str(e)}")

        proc = httpProc(request, 'websiteFunctions/sshAccess.html',
                        {'domainName': self.domain, 'externalApp': externalApp, 'has_addons': has_addons, 'is_selfsigned_ssl': is_selfsigned, 'ssl_issue_link': ssl_issue_link, 'accessed_via_ip': accessed_via_ip})
        return proc.render()

    def saveSSHAccessChanges(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            website = Websites.objects.get(domain=self.domain)

            # if website.externalApp != data['externalApp']:
            #     data_ret = {'status': 0, 'error_message': 'External app mis-match.'}
            #     json_data = json.dumps(data_ret)
            #     return HttpResponse(json_data)

            uBuntuPath = '/etc/lsb-release'

            if os.path.exists(uBuntuPath):
                command = "echo '%s:%s' | chpasswd" % (website.externalApp, data['password'])
            else:
                command = 'echo "%s" | passwd --stdin %s' % (data['password'], website.externalApp)

            ProcessUtilities.executioner(command)

            data_ret = {'status': 1, 'error_message': 'None', 'LinuxUser': website.externalApp}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def setupStaging(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        website = Websites.objects.get(domain=self.domain)
        externalApp = website.externalApp

        proc = httpProc(request, 'websiteFunctions/setupStaging.html',
                        {'domainName': self.domain, 'externalApp': externalApp})
        return proc.render()

    def startCloning(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['masterDomain']

            if not validators.domain(self.domain):
                data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': "Invalid domain."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if not validators.domain(data['domainName']):
                data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': "Invalid domain."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            extraArgs = {}
            extraArgs['domain'] = data['domainName']
            extraArgs['masterDomain'] = data['masterDomain']
            extraArgs['admin'] = admin

            tempStatusPath = "/tmp/" + str(randint(1000, 9999))
            writeToFile = open(tempStatusPath, 'a')
            message = 'Cloning process has started..,5'
            writeToFile.write(message)
            writeToFile.close()

            extraArgs['tempStatusPath'] = tempStatusPath

            st = StagingSetup('startCloning', extraArgs)
            st.start()

            data_ret = {'status': 1, 'error_message': 'None', 'tempStatusPath': tempStatusPath}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def syncToMaster(self, request=None, userID=None, data=None, childDomain=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        website = Websites.objects.get(domain=self.domain)
        externalApp = website.externalApp

        proc = httpProc(request, 'websiteFunctions/syncMaster.html',
                        {'domainName': self.domain, 'externalApp': externalApp, 'childDomain': childDomain})
        return proc.render()

    def startSync(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if not validators.domain(data['childDomain']):
                data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': "Invalid domain."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            self.domain = data['childDomain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            extraArgs = {}
            extraArgs['childDomain'] = data['childDomain']
            try:
                extraArgs['eraseCheck'] = data['eraseCheck']
            except:
                extraArgs['eraseCheck'] = False
            try:
                extraArgs['dbCheck'] = data['dbCheck']
            except:
                extraArgs['dbCheck'] = False
            try:
                extraArgs['copyChanged'] = data['copyChanged']
            except:
                extraArgs['copyChanged'] = False

            extraArgs['admin'] = admin

            tempStatusPath = "/tmp/" + str(randint(1000, 9999))
            writeToFile = open(tempStatusPath, 'a')
            message = 'Syncing process has started..,5'
            writeToFile.write(message)
            writeToFile.close()

            extraArgs['tempStatusPath'] = tempStatusPath

            st = StagingSetup('startSyncing', extraArgs)
            st.start()

            data_ret = {'status': 1, 'error_message': 'None', 'tempStatusPath': tempStatusPath}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def convertDomainToSite(self, userID=None, request=None):
        try:

            extraArgs = {}
            extraArgs['request'] = request
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))
            background = ApplicationInstaller('convertDomainToSite', extraArgs)
            background.start()

            data_ret = {'status': 1, 'createWebSiteStatus': 1, 'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def manageGIT(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        try:
            website = Websites.objects.get(domain=self.domain)
            folders = ['/home/%s/public_html' % (self.domain)]

            databases = website.databases_set.all()

            # for database in databases:
            #     basePath = '/var/lib/mysql/'
            #     folders.append('%s%s' % (basePath, database.dbName))
        except:

            self.childWebsite = ChildDomains.objects.get(domain=self.domain)

            folders = [self.childWebsite.path]

            databases = self.childWebsite.master.databases_set.all()

            # for database in databases:
            #     basePath = '/var/lib/mysql/'
            #     folders.append('%s%s' % (basePath, database.dbName))

        proc = httpProc(request, 'websiteFunctions/manageGIT.html',
                        {'domainName': self.domain, 'folders': folders})
        return proc.render()

    def folderCheck(self):

        try:

            ###

            domainPath = '/home/%s/public_html' % (self.domain)
            vhRoot = '/home/%s' % (self.domain)
            vmailPath = '/home/vmail/%s' % (self.domain)

            ##

            try:

                website = Websites.objects.get(domain=self.domain)

                self.masterWebsite = website
                self.masterDomain = website.domain
                externalApp = website.externalApp
                self.externalAppLocal = website.externalApp
                self.adminEmail = website.adminEmail
                self.firstName = website.admin.firstName
                self.lastName = website.admin.lastName

                self.home = 0
                if self.folder == '/home/%s/public_html' % (self.domain):
                    self.home = 1

            except:

                website = ChildDomains.objects.get(domain=self.domain)
                self.masterWebsite = website.master
                self.masterDomain = website.master.domain
                externalApp = website.master.externalApp
                self.externalAppLocal = website.master.externalApp
                self.adminEmail = website.master.adminEmail
                self.firstName = website.master.admin.firstName
                self.lastName = website.master.admin.lastName

                self.home = 0
                if self.folder == website.path:
                    self.home = 1

            ### Fetch git configurations

            self.confCheck = 1

            gitConfFolder = '/home/cyberpanel/git'
            gitConFile = '%s/%s' % (gitConfFolder, self.masterDomain)

            if not os.path.exists(gitConfFolder):
                os.mkdir(gitConfFolder)

            if not os.path.exists(gitConFile):
                os.mkdir(gitConFile)

            if os.path.exists(gitConFile):
                files = os.listdir(gitConFile)

                if len(files) >= 1:
                    for file in files:
                        self.finalFile = '%s/%s' % (gitConFile, file)

                        gitConf = json.loads(open(self.finalFile, 'r').read())

                        if gitConf['folder'] == self.folder:

                            self.autoCommitCurrent = gitConf['autoCommit']
                            self.autoPushCurrent = gitConf['autoPush']
                            self.emailLogsCurrent = gitConf['emailLogs']
                            try:
                                self.commands = gitConf['commands']
                            except:
                                self.commands = "Add Commands to run after every commit, separate commands using comma."

                            try:
                                self.webhookCommandCurrent = gitConf['webhookCommand']
                            except:
                                self.webhookCommandCurrent = "False"

                            self.confCheck = 0
                            break

            if self.confCheck:
                self.autoCommitCurrent = 'Never'
                self.autoPushCurrent = 'Never'
                self.emailLogsCurrent = 'False'
                self.webhookCommandCurrent = 'False'
                self.commands = "Add Commands to run after every commit, separate commands using comma."

            ##

            if self.folder == domainPath:
                self.externalApp = externalApp
                return 1

            ##

            if self.folder == vhRoot:
                self.externalApp = externalApp
                return 1

            ##

            try:
                childDomain = ChildDomains.objects.get(domain=self.domain)

                if self.folder == childDomain.path:
                    self.externalApp = externalApp
                    return 1

            except:
                pass

            ##

            if self.folder == vmailPath:
                self.externalApp = 'vmail'
                return 1

            try:

                for database in website.databases_set.all():
                    self.externalApp = 'mysql'
                    basePath = '/var/lib/mysql/'
                    dbPath = '%s%s' % (basePath, database.dbName)

                    if self.folder == dbPath:
                        return 1
            except:
                for database in website.master.databases_set.all():
                    self.externalApp = 'mysql'
                    basePath = '/var/lib/mysql/'
                    dbPath = '%s%s' % (basePath, database.dbName)

                    if self.folder == dbPath:
                        return 1

            return 0


        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile('%s. [folderCheck:3002]' % (str(msg)))

        return 0

    def fetchFolderDetails(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            gitPath = '%s/.git' % (self.folder)
            command = 'ls -la %s' % (gitPath)

            if ProcessUtilities.outputExecutioner(command, self.externalAppLocal).find(
                    'No such file or directory') > -1:

                command = 'cat /home/%s/.ssh/%s.pub' % (self.masterDomain, self.externalAppLocal)
                deploymentKey = ProcessUtilities.outputExecutioner(command, self.externalAppLocal)

                if deploymentKey.find('No such file or directory') > -1:
                    command = "ssh-keygen -f /home/%s/.ssh/%s -t rsa -N ''" % (self.masterDomain, self.externalAppLocal)
                    ProcessUtilities.executioner(command, self.externalAppLocal)

                    command = 'cat /home/%s/.ssh/%s.pub' % (self.masterDomain, self.externalAppLocal)
                    deploymentKey = ProcessUtilities.outputExecutioner(command, self.externalAppLocal)

                data_ret = {'status': 1, 'repo': 0, 'deploymentKey': deploymentKey, 'home': self.home}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:

                ## Find git branches

                command = 'git -C %s branch' % (self.folder)
                branches = ProcessUtilities.outputExecutioner(command, self.externalAppLocal).split('\n')[:-1]

                ## Fetch key

                command = 'cat /home/%s/.ssh/%s.pub' % (self.domain, self.externalAppLocal)
                deploymentKey = ProcessUtilities.outputExecutioner(command, self.externalAppLocal)

                if deploymentKey.find('No such file or directory') > -1:
                    command = "ssh-keygen -f /home/%s/.ssh/%s -t rsa -N ''" % (self.masterDomain, self.externalAppLocal)
                    ProcessUtilities.executioner(command, self.externalAppLocal)

                    command = 'cat /home/%s/.ssh/%s.pub' % (self.masterDomain, self.externalAppLocal)
                    deploymentKey = ProcessUtilities.outputExecutioner(command, self.externalAppLocal)

                ## Find Remote if any

                command = 'git -C %s remote -v' % (self.folder)
                remoteResult = ProcessUtilities.outputExecutioner(command, self.externalAppLocal)

                remote = 1
                if remoteResult.find('origin') == -1:
                    remote = 0
                    remoteResult = 'Remote currently not set.'

                ## Find Total commits on current branch

                command = 'git -C %s rev-list --count HEAD' % (self.folder)
                totalCommits = ProcessUtilities.outputExecutioner(command, self.externalAppLocal)

                if totalCommits.find('fatal') > -1:
                    totalCommits = '0'

                ##

                port = ProcessUtilities.fetchCurrentPort()

                webHookURL = 'https://%s:%s/websites/%s/webhook' % (ACLManager.fetchIP(), port, self.domain)

                data_ret = {'status': 1, 'repo': 1, 'finalBranches': branches, 'deploymentKey': deploymentKey,
                            'remote': remote, 'remoteResult': remoteResult, 'totalCommits': totalCommits,
                            'home': self.home,
                            'webHookURL': webHookURL, 'autoCommitCurrent': self.autoCommitCurrent,
                            'autoPushCurrent': self.autoPushCurrent, 'emailLogsCurrent': self.emailLogsCurrent,
                            'commands': self.commands, "webhookCommandCurrent": self.webhookCommandCurrent}

                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def initRepo(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            website = Websites.objects.get(domain=self.masterDomain)

            command = 'git -C %s init' % (self.folder)
            result = ProcessUtilities.outputExecutioner(command, website.externalApp)

            if result.find('Initialized empty Git repository in') > -1:

                command = 'git -C %s config --local user.email %s' % (self.folder, self.adminEmail)
                ProcessUtilities.executioner(command, website.externalApp)

                command = 'git -C %s config --local user.name "%s %s"' % (
                    self.folder, self.firstName, self.lastName)
                ProcessUtilities.executioner(command, website.externalApp)

                ## Fix permissions

                # from filemanager.filemanager import FileManager
                #
                # fm = FileManager(None, None)
                # fm.fixPermissions(self.masterDomain)

                data_ret = {'status': 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': result}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def setupRemote(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']
            self.gitHost = data['gitHost']
            self.gitUsername = data['gitUsername']
            self.gitReponame = data['gitReponame']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            ## Security checks

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            if self.gitHost.find(':') > -1:
                gitHostDomain = self.gitHost.split(':')[0]
                gitHostPort = self.gitHost.split(':')[1]

                if not validators.domain(gitHostDomain):
                    return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')

                try:
                    gitHostPort = int(gitHostPort)
                except:
                    return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')

            else:
                if not validators.domain(self.gitHost):
                    return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')

            if ACLManager.validateInput(self.gitUsername) and ACLManager.validateInput(self.gitReponame):
                pass
            else:
                return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')

            ### set default ssh key

            command = 'git -C %s config --local core.sshCommand "ssh -i /home/%s/.ssh/%s -o "StrictHostKeyChecking=no""' % (
                self.folder, self.masterDomain, self.externalAppLocal)
            ProcessUtilities.executioner(command, self.externalAppLocal)

            ## Check if remote exists

            command = 'git -C %s remote -v' % (self.folder)
            remoteResult = ProcessUtilities.outputExecutioner(command, self.externalAppLocal)

            ## Set new remote

            if remoteResult.find('origin') == -1:
                command = 'git -C %s remote add origin git@%s:%s/%s.git' % (
                    self.folder, self.gitHost, self.gitUsername, self.gitReponame)
            else:
                command = 'git -C %s remote set-url origin git@%s:%s/%s.git' % (
                    self.folder, self.gitHost, self.gitUsername, self.gitReponame)

            possibleError = ProcessUtilities.outputExecutioner(command, self.externalAppLocal)

            ## Check if set correctly.

            command = 'git -C %s remote -v' % (self.folder)
            remoteResult = ProcessUtilities.outputExecutioner(command, self.externalAppLocal)

            if remoteResult.find(self.gitUsername) > -1:

                # ## Fix permissions
                #
                # from filemanager.filemanager import FileManager
                #
                # fm = FileManager(None, None)
                # fm.fixPermissions(self.masterDomain)

                data_ret = {'status': 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': possibleError}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def changeGitBranch(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']
            self.branchName = data['branchName']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            ## Security check

            if ACLManager.validateInput(self.branchName):
                pass
            else:
                return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')

            if self.branchName.find('*') > -1:
                data_ret = {'status': 0, 'commandStatus': 'Already on this branch.',
                            'error_message': 'Already on this branch.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            command = 'git -C %s checkout %s' % (self.folder, self.branchName.strip(' '))
            commandStatus = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if commandStatus.find('Switched to branch') > -1:

                # ## Fix permissions
                #
                # from filemanager.filemanager import FileManager
                #
                # fm = FileManager(None, None)
                # fm.fixPermissions(self.masterDomain)

                data_ret = {'status': 1, 'commandStatus': commandStatus + 'Refreshing page in 3 seconds..'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': 'Failed to change branch', 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def createNewBranch(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']
            self.newBranchName = data['newBranchName']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            ## Security check

            if ACLManager.validateInput(self.newBranchName):
                pass
            else:
                return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')

            ##

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            command = 'git -C %s checkout -b "%s"' % (self.folder, self.newBranchName)
            commandStatus = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if commandStatus.find(self.newBranchName) > -1:

                # ## Fix permissions
                #
                # from filemanager.filemanager import FileManager
                #
                # fm = FileManager(None, None)
                # fm.fixPermissions(self.masterDomain)

                data_ret = {'status': 1, 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': 'Failed to create branch', 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def commitChanges(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']
            self.commitMessage = data['commitMessage']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            # security check

            if ACLManager.validateInput(self.commitMessage):
                pass
            else:
                return ACLManager.loadErrorJson()

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            ## Check if remote exists

            command = 'git -C %s add -A' % (self.folder)
            ProcessUtilities.outputExecutioner(command, self.externalApp)

            command = 'git -C %s commit -m "%s"' % (self.folder, self.commitMessage.replace('"', ''))
            commandStatus = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if commandStatus.find('nothing to commit') == -1:

                try:
                    if self.commands != 'NONE':

                        GitLogs(owner=self.masterWebsite, type='INFO',
                                message='Running commands after successful git commit..').save()

                        if self.commands.find('\n') > -1:
                            commands = self.commands.split('\n')

                            for command in commands:
                                GitLogs(owner=self.masterWebsite, type='INFO',
                                        message='Running: %s' % (command)).save()

                                result = ProcessUtilities.outputExecutioner(command, self.externalAppLocal)
                                GitLogs(owner=self.masterWebsite, type='INFO',
                                        message='Result: %s' % (result)).save()
                        else:
                            GitLogs(owner=self.masterWebsite, type='INFO',
                                    message='Running: %s' % (self.commands)).save()

                            result = ProcessUtilities.outputExecutioner(self.commands, self.externalAppLocal)
                            GitLogs(owner=self.masterWebsite, type='INFO',
                                    message='Result: %s' % (result)).save()

                        GitLogs(owner=self.masterWebsite, type='INFO',
                                message='Finished running commands.').save()
                except:
                    pass

                ## Fix permissions

                # from filemanager.filemanager import FileManager
                #
                # fm = FileManager(None, None)
                # fm.fixPermissions(self.masterDomain)

                data_ret = {'status': 1, 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': 'Nothing to commit.', 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg), 'commandStatus': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def gitPull(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            ### set default ssh key

            command = 'git -C %s config --local core.sshCommand "ssh -i /home/%s/.ssh/%s -o "StrictHostKeyChecking=no""' % (
                self.folder, self.masterDomain, self.externalAppLocal)
            ProcessUtilities.executioner(command, self.externalApp)

            ## Check if remote exists

            command = 'git -C %s pull' % (self.folder)
            commandStatus = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if commandStatus.find('Already up to date') == -1:

                ## Fix permissions

                # from filemanager.filemanager import FileManager
                #
                # fm = FileManager(None, None)
                # fm.fixPermissions(self.masterDomain)

                data_ret = {'status': 1, 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': 'Pull not required.', 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def gitPush(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            ### set default ssh key

            command = 'git -C %s config --local core.sshCommand "ssh -i /home/%s/.ssh/%s -o "StrictHostKeyChecking=no""' % (
                self.folder, self.masterDomain, self.externalAppLocal)
            ProcessUtilities.executioner(command, self.externalApp)

            ##

            command = 'git -C %s push' % (self.folder)
            commandStatus = ProcessUtilities.outputExecutioner(command, self.externalApp, False)

            if commandStatus.find('has no upstream branch') > -1:
                command = 'git -C %s rev-parse --abbrev-ref HEAD' % (self.folder)
                currentBranch = ProcessUtilities.outputExecutioner(command, self.externalApp, False).rstrip('\n')

                if currentBranch.find('fatal: ambiguous argument') > -1:
                    data_ret = {'status': 0, 'error_message': 'You need to commit first.',
                                'commandStatus': 'You need to commit first.'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                command = 'git -C %s push --set-upstream origin %s' % (self.folder, currentBranch)
                commandStatus = ProcessUtilities.outputExecutioner(command, self.externalApp, False)

            if commandStatus.find('Everything up-to-date') == -1 and commandStatus.find(
                    'rejected') == -1 and commandStatus.find('Permission denied') == -1:
                data_ret = {'status': 1, 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': 'Push failed.', 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg), 'commandStatus': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def attachRepoGIT(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']
            self.gitHost = data['gitHost']
            self.gitUsername = data['gitUsername']
            self.gitReponame = data['gitReponame']

            try:
                self.overrideData = data['overrideData']
            except:
                self.overrideData = False

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            if self.gitHost.find(':') > -1:
                gitHostDomain = self.gitHost.split(':')[0]
                gitHostPort = self.gitHost.split(':')[1]

                if not validators.domain(gitHostDomain):
                    return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')

                try:
                    gitHostPort = int(gitHostPort)
                except:
                    return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')
            else:
                if not validators.domain(self.gitHost):
                    return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')

            ## Security check

            if ACLManager.validateInput(self.gitUsername) and ACLManager.validateInput(self.gitReponame):
                pass
            else:
                return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')

            ##

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            if self.overrideData:
                command = 'rm -rf %s' % (self.folder)
                ProcessUtilities.executioner(command, self.externalApp)

            ## Set defauly key

            command = 'git config --global core.sshCommand "ssh -i /home/%s/.ssh/%s -o "StrictHostKeyChecking=no""' % (
                self.masterDomain, self.externalAppLocal)
            ProcessUtilities.executioner(command, self.externalApp)

            ##

            command = 'git clone git@%s:%s/%s.git %s' % (self.gitHost, self.gitUsername, self.gitReponame, self.folder)
            commandStatus = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if commandStatus.find('already exists') == -1 and commandStatus.find('Permission denied') == -1:

                # from filemanager.filemanager import FileManager
                #
                # fm = FileManager(None, None)
                # fm.fixPermissions(self.masterDomain)

                command = 'git -C %s config --local user.email %s' % (self.folder, self.adminEmail)
                ProcessUtilities.executioner(command, self.externalApp)

                command = 'git -C %s config --local user.name "%s %s"' % (self.folder, self.firstName, self.lastName)
                ProcessUtilities.executioner(command, self.externalApp)

                data_ret = {'status': 1, 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            else:

                # from filemanager.filemanager import FileManager
                #
                # fm = FileManager(None, None)
                # fm.fixPermissions(self.masterDomain)

                data_ret = {'status': 0, 'error_message': 'Failed to clone.', 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def removeTracking(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            command = 'rm -rf %s/.git' % (self.folder)
            ProcessUtilities.executioner(command, self.externalApp)

            gitConfFolder = '/home/cyberpanel/git'
            gitConFile = '%s/%s' % (gitConfFolder, self.masterDomain)
            finalFile = '%s/%s' % (gitConFile, self.folder.split('/')[-1])

            command = 'rm -rf %s' % (finalFile)
            ProcessUtilities.outputExecutioner(command, self.externalApp)

            ## Fix permissions

            # from filemanager.filemanager import FileManager
            #
            # fm = FileManager(None, None)
            # fm.fixPermissions(self.masterDomain)

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchGitignore(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            command = 'cat %s/.gitignore' % (self.folder)
            gitIgnoreContent = ProcessUtilities.outputExecutioner(command, self.externalAppLocal)

            if gitIgnoreContent.find('No such file or directory') > -1:
                gitIgnoreContent = 'File is currently empty.'

            data_ret = {'status': 1, 'gitIgnoreContent': gitIgnoreContent}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def saveGitIgnore(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']
            self.gitIgnoreContent = data['gitIgnoreContent']

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            ## Write to temp file

            writeToFile = open(tempPath, 'w')
            writeToFile.write(self.gitIgnoreContent)
            writeToFile.close()

            ## Move to original file

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            command = 'mv %s %s/.gitignore' % (tempPath, self.folder)
            ProcessUtilities.executioner(command, self.externalApp)

            ## Fix permissions

            # from filemanager.filemanager import FileManager
            #
            # fm = FileManager(None, None)
            # fm.fixPermissions(self.masterDomain)

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchCommits(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            initCommand = """log --pretty=format:"%h|%s|%cn|%cd" -50"""

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            command = 'git -C %s %s' % (self.folder, initCommand)
            commits = ProcessUtilities.outputExecutioner(command, self.externalApp).split('\n')

            json_data = "["
            checker = 0
            id = 1

            for commit in commits:
                cm = commit.split('|')

                dic = {'id': str(id), 'commit': cm[0], 'message': cm[1].replace('"', "'"), 'name': cm[2], 'date': cm[3]}
                id = id + 1

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            commits = json_data + ']'

            data_ret = {'status': 1, 'commits': commits}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except IndexError:
            data_ret = {'status': 0, 'error_message': 'No commits found.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchFiles(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']
            self.commit = data['commit']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            ## Security check

            if ACLManager.validateInput(self.commit):
                pass
            else:
                return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')

            ##

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            command = 'git -C %s diff-tree --no-commit-id --name-only -r %s' % (self.folder, self.commit)
            files = ProcessUtilities.outputExecutioner(command, self.externalApp).split('\n')

            FinalFiles = []

            for items in files:
                if items != '':
                    FinalFiles.append(items.rstrip('\n').lstrip('\n'))

            data_ret = {'status': 1, 'files': FinalFiles}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchChangesInFile(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']
            self.file = data['file']
            self.commit = data['commit']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            ## security check

            if ACLManager.validateInput(self.commit) and self.file.find('..') == -1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 'Invalid characters in your input.')

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            command = 'git -C %s show %s -- %s/%s' % (
                self.folder, self.commit, self.folder, self.file.strip('\n').strip(' '))
            fileChangedContent = ProcessUtilities.outputExecutioner(command, self.externalApp).split('\n')

            initialNumber = 0
            ## Find initial line numbers
            for items in fileChangedContent:
                if len(items) == 0:
                    initialNumber = initialNumber + 1
                elif items[0] == '@':
                    break
                else:
                    initialNumber = initialNumber + 1

            try:
                lineNumber = int(fileChangedContent[initialNumber].split('+')[1].split(',')[0])
            except:
                lineNumber = int(fileChangedContent[initialNumber].split('+')[1].split(' ')[0])

            fileLen = len(fileChangedContent)
            finalConent = '<tr><td style="border-top: none;color:blue">%s</td><td style="border-top: none;"><p style="color:blue">%s</p></td></tr>' % (
                '#', fileChangedContent[initialNumber])

            for i in range(initialNumber + 1, fileLen - 1):
                if fileChangedContent[i][0] == '@':
                    lineNumber = int(fileChangedContent[i].split('+')[1].split(',')[0])
                    finalConent = finalConent + '<tr><td style="border-top: none;color:blue">%s</td><td style="border-top: none;"><p style="color:blue">%s</p></td></tr>' % (
                        '#', fileChangedContent[i])
                    continue

                else:
                    if fileChangedContent[i][0] == '+':
                        content = '<p style="color:green">%s</p>' % (
                            fileChangedContent[i].replace('<', "&lt;").replace('>', "&gt;"))
                        finalConent = finalConent + '<tr style="color:green"><td style="border-top: none;">%s</td><td style="border-top: none;">%s</td></tr>' % (
                            str(lineNumber), content)
                        lineNumber = lineNumber + 1
                    elif fileChangedContent[i][0] == '-':
                        content = '<p style="color:red">%s</p>' % (
                            fileChangedContent[i].replace('<', "&lt;").replace('>', "&gt;"))
                        finalConent = finalConent + '<tr style="color:red"><td style="border-top: none;">%s</td><td style="border-top: none;">%s</td></tr>' % (
                            str(lineNumber), content)
                        lineNumber = lineNumber + 1
                    else:
                        content = '<p>%s</p>' % (fileChangedContent[i].replace('<', "&lt;").replace('>', "&gt;"))
                        finalConent = finalConent + '<tr><td style="border-top: none;">%s</td><td style="border-top: none;">%s</td></tr>' % (
                            str(lineNumber), content)
                        lineNumber = lineNumber + 1

            data_ret = {'status': 1, 'fileChangedContent': finalConent}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except IndexError:
            data_ret = {'status': 0, 'error_message': 'Not a text file.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def saveGitConfigurations(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']

            dic = {}

            dic['domain'] = self.domain

            dic['autoCommit'] = data['autoCommit']

            try:
                dic['autoPush'] = data['autoPush']
            except:
                dic['autoPush'] = 'Never'

            try:
                dic['emailLogs'] = data['emailLogs']
            except:
                dic['emailLogs'] = False

            try:
                dic['commands'] = data['commands']
            except:
                dic['commands'] = 'NONE'

            try:
                dic['webhookCommand'] = data['webhookCommand']
            except:
                dic['webhookCommand'] = False

            dic['folder'] = self.folder

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            ##

            if self.confCheck == 1:
                gitConfFolder = '/home/cyberpanel/git'
                gitConFile = '%s/%s' % (gitConfFolder, self.masterDomain)
                self.finalFile = '%s/%s' % (gitConFile, str(randint(1000, 9999)))

                if not os.path.exists(gitConfFolder):
                    os.mkdir(gitConfFolder)

                if not os.path.exists(gitConFile):
                    os.mkdir(gitConFile)

            writeToFile = open(self.finalFile, 'w')
            writeToFile.write(json.dumps(dic))
            writeToFile.close()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getLogsInJson(self, logs):
        json_data = "["
        checker = 0
        counter = 1

        for items in logs:
            dic = {'type': items.type, 'date': items.date.strftime('%m.%d.%Y_%H-%M-%S'), 'message': items.message}

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)
            counter = counter + 1

        json_data = json_data + ']'
        return json_data

    def fetchGitLogs(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            self.folder = data['folder']
            recordsToShow = int(data['recordsToShow'])
            page = int(data['page'])

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            if self.folderCheck():
                pass
            else:
                return ACLManager.loadErrorJson()

            logs = self.masterWebsite.gitlogs_set.all().order_by('-id')

            from s3Backups.s3Backups import S3Backups

            pagination = S3Backups.getPagination(len(logs), recordsToShow)
            endPageNumber, finalPageNumber = S3Backups.recordsPointer(page, recordsToShow)
            jsonData = self.getLogsInJson(logs[finalPageNumber:endPageNumber])

            data_ret = {'status': 1, 'logs': jsonData, 'pagination': pagination}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except IndexError:
            data_ret = {'status': 0, 'error_message': 'Not a text file.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def webhook(self, domain, data=None):
        try:

            self.domain = domain

            ### set default ssh key

            try:
                web = Websites.objects.get(domain=self.domain)
                self.web = web
                self.folder = '/home/%s/public_html' % (domain)
                self.masterDomain = domain
            except:
                web = ChildDomains.objects.get(domain=self.domain)
                self.folder = web.path
                self.masterDomain = web.master.domain
                self.web = web.master

            ## Check if remote exists

            self.externalApp = ACLManager.FetchExternalApp(self.domain)

            command = 'git -C %s pull' % (self.folder)
            commandStatus = ProcessUtilities.outputExecutioner(command, self.externalApp)

            if commandStatus.find('Already up to date') == -1:
                message = '[Webhook Fired] Status: %s.' % (commandStatus)
                GitLogs(owner=self.web, type='INFO', message=message).save()

                ### Fetch git configurations

                found = 0

                gitConfFolder = '/home/cyberpanel/git'
                gitConFile = '%s/%s' % (gitConfFolder, self.masterDomain)

                if not os.path.exists(gitConfFolder):
                    os.mkdir(gitConfFolder)

                if not os.path.exists(gitConFile):
                    os.mkdir(gitConFile)

                if os.path.exists(gitConFile):
                    files = os.listdir(gitConFile)

                    if len(files) >= 1:
                        for file in files:
                            finalFile = '%s/%s' % (gitConFile, file)
                            gitConf = json.loads(open(finalFile, 'r').read())
                            if gitConf['folder'] == self.folder:
                                found = 1
                                break
                if found:
                    try:
                        if gitConf['webhookCommand']:
                            if gitConf['commands'] != 'NONE':

                                GitLogs(owner=self.web, type='INFO',
                                        message='Running commands after successful git commit..').save()

                                if gitConf['commands'].find('\n') > -1:
                                    commands = gitConf['commands'].split('\n')

                                    for command in commands:
                                        GitLogs(owner=self.web, type='INFO',
                                                message='Running: %s' % (command)).save()

                                        result = ProcessUtilities.outputExecutioner(command, self.web.externalApp, None,
                                                                                    self.folder)
                                        GitLogs(owner=self.web, type='INFO',
                                                message='Result: %s' % (result)).save()
                                else:
                                    GitLogs(owner=self.web, type='INFO',
                                            message='Running: %s' % (gitConf['commands'])).save()

                                    result = ProcessUtilities.outputExecutioner(gitConf['commands'],
                                                                                self.web.externalApp, None, self.folder)
                                    GitLogs(owner=self.web, type='INFO',
                                            message='Result: %s' % (result)).save()

                                GitLogs(owner=self.web, type='INFO',
                                        message='Finished running commands.').save()
                    except:
                        pass

                ## Fix permissions

                # from filemanager.filemanager import FileManager
                #
                # fm = FileManager(None, None)
                # fm.fixPermissions(self.masterDomain)

                data_ret = {'status': 1, 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                message = '[Webhook Fired] Status: %s.' % (commandStatus)
                GitLogs(owner=self.web, type='ERROR', message=message).save()
                data_ret = {'status': 0, 'error_message': 'Pull not required.', 'commandStatus': commandStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getSSHConfigs(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            domain = data['domain']
            website = Websites.objects.get(domain=domain)

            if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            pathToKeyFile = "/home/%s/.ssh/authorized_keys" % (domain)

            cat = "cat " + pathToKeyFile
            data = ProcessUtilities.outputExecutioner(cat, website.externalApp).split('\n')

            json_data = "["
            checker = 0

            for items in data:
                if items.find("ssh-rsa") > -1:
                    keydata = items.split(" ")

                    try:
                        key = "ssh-rsa " + keydata[1][:50] + "  ..  " + keydata[2]
                        try:
                            userName = keydata[2][:keydata[2].index("@")]
                        except:
                            userName = keydata[2]
                    except:
                        key = "ssh-rsa " + keydata[1][:50]
                        userName = ''

                    dic = {'userName': userName,
                           'key': key,
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteSSHKey(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            domain = data['domain']

            if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            key = data['key']
            pathToKeyFile = "/home/%s/.ssh/authorized_keys" % (domain)
            website = Websites.objects.get(domain=domain)

            command = f'chown {website.externalApp}:{website.externalApp} {pathToKeyFile}'
            ProcessUtilities.outputExecutioner(command)

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/firewallUtilities.py"
            execPath = execPath + " deleteSSHKey --key '%s' --path %s" % (key, pathToKeyFile)

            output = ProcessUtilities.outputExecutioner(execPath, website.externalApp)

            if output.find("1,None") > -1:
                final_dic = {'status': 1, 'delete_status': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 1, 'delete_status': 1, "error_mssage": output}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'delete_status': 0, 'error_mssage': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def addSSHKey(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            domain = data['domain']
            website = Websites.objects.get(domain=domain)

            if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            key = data['key']
            pathToKeyFile = "/home/%s/.ssh/authorized_keys" % (domain)

            command = 'mkdir -p /home/%s/.ssh/' % (domain)
            ProcessUtilities.executioner(command)

            command = 'chown %s:%s /home/%s/.ssh/' % (website.externalApp, website.externalApp, domain)
            ProcessUtilities.executioner(command)

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            writeToFile = open(tempPath, "w")
            writeToFile.write(key)
            writeToFile.close()

            execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/firewallUtilities.py"
            execPath = execPath + " addSSHKey --tempPath %s --path %s" % (tempPath, pathToKeyFile)

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                final_dic = {'status': 1, 'add_status': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 0, 'add_status': 0, "error_mssage": output}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'add_status': 0, 'error_mssage': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def ApacheManager(self, request=None, userID=None, data=None):
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        phps = PHPManager.findPHPVersions()
        apachePHPs = PHPManager.findApachePHPVersions()

        if ACLManager.CheckForPremFeature('all'):
            apachemanager = 1
        else:
            apachemanager = 0

        proc = httpProc(request, 'websiteFunctions/ApacheManager.html',
                        {'domainName': self.domain, 'phps': phps, 'apachemanager': apachemanager, 'apachePHPs': apachePHPs})
        return proc.render()

    def resetApacheConfigToDefault(self, userID=None, data=None):
        """Reset Apache configuration to default template"""
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] != 1:
            return ACLManager.loadErrorJson('configstatus', 0)

        domainName = data['domainName']
        self.domain = domainName

        try:
            # Get the default Apache configuration template
            from plogical import vhostConfs
            
            # Determine if it's a child domain or main domain
            try:
                child_domain = ChildDomains.objects.get(domain=domainName)
                is_child = True
                master_domain = child_domain.master.domain
                admin_email = child_domain.master.adminEmail if child_domain.master.adminEmail else child_domain.master.admin.email
                path = child_domain.path
            except:
                is_child = False
                try:
                    website = Websites.objects.get(domain=domainName)
                    admin_email = website.adminEmail if website.adminEmail else website.admin.email
                except:
                    admin_email = "admin@" + domainName

            # Generate default Apache configuration
            if is_child:
                # Use child domain Apache template
                default_config = vhostConfs.apacheConfChild
                default_config = default_config.replace('{virtualHostName}', domainName)
                default_config = default_config.replace('{administratorEmail}', admin_email)
                default_config = default_config.replace('{php}', '8.1')  # Default PHP version
                default_config = default_config.replace('{adminEmails}', admin_email)
                default_config = default_config.replace('{externalApp}', "".join(re.findall("[a-zA-Z]+", domainName))[:5] + str(randint(1000, 9999)))
                default_config = default_config.replace('{path}', path)
                default_config = default_config.replace('{sockPath}', '/var/run/php/')  # Default socket path
            else:
                # Use main domain Apache template
                default_config = vhostConfs.apacheConf
                default_config = default_config.replace('{virtualHostName}', domainName)
                default_config = default_config.replace('{administratorEmail}', admin_email)
                default_config = default_config.replace('{php}', '8.1')  # Default PHP version
                default_config = default_config.replace('{adminEmails}', admin_email)
                default_config = default_config.replace('{externalApp}', "".join(re.findall("[a-zA-Z]+", domainName))[:5] + str(randint(1000, 9999)))
                default_config = default_config.replace('{sockPath}', '/var/run/php/')  # Default socket path

            # Save the default configuration
            mailUtilities.checkHome()
            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            
            vhost = open(tempPath, "w")
            vhost.write(default_config)
            vhost.close()

            filePath = ApacheVhost.configBasePath + domainName + '.conf'

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " saveApacheConfigsToFile --path " + filePath + " --tempPath " + tempPath

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                status = {"status": 1, "message": "Apache configuration reset to default successfully."}
            else:
                status = {"status": 0, "error_message": f"Failed to reset Apache configuration: {output}"}

            final_json = json.dumps(status)
            return HttpResponse(final_json)

        except Exception as e:
            status = {"status": 0, "error_message": f"Error resetting Apache configuration: {str(e)}"}
            final_json = json.dumps(status)
            return HttpResponse(final_json)

    def saveApacheConfigsToFile(self, userID=None, data=None):

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] != 1:
            return ACLManager.loadErrorJson('configstatus', 0)

        configData = data['configData']
        self.domain = data['domainName']

        mailUtilities.checkHome()

        tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

        vhost = open(tempPath, "w")

        vhost.write(configData)

        vhost.close()

        ## writing data temporary to file

        filePath = ApacheVhost.configBasePath + self.domain + '.conf'

        ## save configuration data

        execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
        execPath = execPath + " saveApacheConfigsToFile --path " + filePath + " --tempPath " + tempPath

        output = ProcessUtilities.outputExecutioner(execPath)

        if output.find("1,None") > -1:
            status = {"status": 1}
            final_json = json.dumps(status)
            return HttpResponse(final_json)
        else:
            final_dic = {'status': 0, 'error_message': output}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def CreateDockerPackage(self, request=None, userID=None, data=None, DeleteID=None):
        Data = {}

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        try:
            if DeleteID != None:
                DockerPackagesDelete = DockerPackages.objects.get(pk=DeleteID)
                DockerPackagesDelete.delete()
        except:
            pass

        Data['packages'] = DockerPackages.objects.all()

        proc = httpProc(request, 'websiteFunctions/CreateDockerPackage.html',
                        Data, 'createWebsite')
        return proc.render()

    def AssignPackage(self, request=None, userID=None, data=None, DeleteID=None):

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        try:
            if DeleteID != None:
                DockerPackagesDelete = PackageAssignment.objects.get(pk=DeleteID)
                DockerPackagesDelete.delete()
        except:
            pass

        adminNames = ACLManager.loadAllUsers(userID)
        dockerpackages = DockerPackages.objects.all()
        assignpackage = PackageAssignment.objects.all()
        Data = {'adminNames': adminNames, 'DockerPackages': dockerpackages, 'assignpackage': assignpackage}
        proc = httpProc(request, 'websiteFunctions/assignPackage.html',
                        Data, 'createWebsite')
        return proc.render()

    def CreateDockersite(self, request=None, userID=None, data=None):
        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        data = {
            "name": "docker-manager",
            "IP": ACLManager.GetServerIP()
        }

        import requests
        response = requests.post(url, data=json.dumps(data))
        Status = response.json()['status']

        if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
            adminNames = ACLManager.loadAllUsers(userID)
            Data = {'adminNames': adminNames}

            if PackageAssignment.objects.all().count() == 0:
                name = 'Default'
                cpu = 2
                Memory = 1024
                Bandwidth = '100'
                disk = '100'

                saveobj = DockerPackages(Name=name, CPUs=cpu, Ram=Memory, Bandwidth=Bandwidth, DiskSpace=disk, config='')
                saveobj.save()

                userobj = Administrator.objects.get(pk=1)

                sv = PackageAssignment(user=userobj, package=saveobj)
                sv.save()

            proc = httpProc(request, 'websiteFunctions/CreateDockerSite.html',
                            Data, 'createWebsite')
            return proc.render()
        else:
            from django.shortcuts import reverse
            return redirect(reverse('pricing'))

    def AddDockerpackage(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            admin = Administrator.objects.get(pk=userID)

            name = data['name']
            cpu = data['cpu']
            Memory = data['Memory']
            Bandwidth = data['Bandwidth']
            disk = data['disk']

            saveobj = DockerPackages(Name=name, CPUs=cpu, Ram=Memory, Bandwidth=Bandwidth, DiskSpace=disk, config='')
            saveobj.save()

            status = {"status": 1, 'error_message': None}
            final_json = json.dumps(status)
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def Getpackage(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            admin = Administrator.objects.get(pk=userID)
            id = data['id']

            docker_package = DockerPackages.objects.get(pk=id)

            # Convert DockerPackages object to dictionary
            package_data = {
                'Name': docker_package.Name,
                'CPU': docker_package.CPUs,
                'Memory': docker_package.Ram,
                'Bandwidth': docker_package.Bandwidth,
                'DiskSpace': docker_package.DiskSpace,
            }

            rdata = {'obj': package_data}

            status = {"status": 1, 'error_message': rdata}
            final_json = json.dumps(status)
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def Updatepackage(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            admin = Administrator.objects.get(pk=userID)
            id = data['id']
            CPU = data['CPU']
            RAM = data['RAM']
            Bandwidth = data['Bandwidth']
            DiskSpace = data['DiskSpace']

            docker_package = DockerPackages.objects.get(pk=id)

            docker_package.CPUs = CPU
            docker_package.Ram = RAM
            docker_package.Bandwidth = Bandwidth
            docker_package.DiskSpace = DiskSpace
            docker_package.save()

            status = {"status": 1, 'error_message': None}
            final_json = json.dumps(status)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def AddAssignment(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()


            admin = Administrator.objects.get(pk=userID)

            package = data['package']
            user = data['user']

            userobj = Administrator.objects.get(userName=user)

            try:
                delasg = PackageAssignment.objects.get(user=userobj)
                delasg.delete()
            except:
                pass

            docker_package = DockerPackages.objects.get(pk=int(package))

            sv = PackageAssignment(user=userobj, package=docker_package)
            sv.save()

            status = {"status": 1, 'error_message': None}
            final_json = json.dumps(status)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def submitDockerSiteCreation(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)
            currentACL = ACLManager.loadedACL(userID)

            sitename = data['sitename']
            Owner = data['Owner']
            Domain = data['Domain']
            MysqlCPU = int(data['MysqlCPU'])
            MYsqlRam = int(data['MYsqlRam'])
            SiteCPU = int(data['SiteCPU'])
            SiteRam = int(data['SiteRam'])
            App = data['App']
            WPusername = data['WPusername']
            WPemal = data['WPemal']
            WPpasswd = data['WPpasswd']

            if int(MYsqlRam) < 256:
                final_dic = {'status': 0, 'error_message': 'Minimum MySQL ram should be 256MB.'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            if int(SiteRam) < 256:
                final_dic = {'status': 0, 'error_message': 'Minimum site ram should be 256MB.'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)


            pattern = r"^[a-z0-9][a-z0-9]*$"

            if re.match(pattern, sitename):
                pass
            else:
                final_dic = {'status': 0, 'error_message': f'invalid site name "{sitename}": must consist only of lowercase alphanumeric characters, as well as start with a letter or number.'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            loggedUser = Administrator.objects.get(pk=userID)
            newOwner = Administrator.objects.get(userName=Owner)

            try:
                pkaobj = PackageAssignment.objects.get(user=newOwner)
            except:
                final_dic = {'status': 0, 'error_message': str('Please assign package to selected user')}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            Dpkgobj = DockerPackages.objects.get(pk=pkaobj.package.id)

            pkg_cpu = Dpkgobj.CPUs
            pkg_Ram = Dpkgobj.Ram

            totalcup = SiteCPU + MysqlCPU
            totalRam = SiteRam + MYsqlRam

            if (totalcup > pkg_cpu):
                final_dic = {'status': 0, 'error_message': str(f'You can add {pkg_cpu} or less then {pkg_cpu} CPUs.')}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            if (totalRam > pkg_Ram):
                final_dic = {'status': 0, 'error_message': str(f'You can add {pkg_Ram} or less then {pkg_Ram} Ram.')}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            if ACLManager.currentContextPermission(currentACL, 'createWebsite') == 0:
                return ACLManager.loadErrorJson('createWebSiteStatus', 0)

            if ACLManager.checkOwnerProtection(currentACL, loggedUser, newOwner) == 0:
                return ACLManager.loadErrorJson('createWebSiteStatus', 0)

            if ACLManager.CheckDomainBlackList(Domain) == 0:
                data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': "Blacklisted domain."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            data = {}

            data['JobID'] = tempStatusPath
            data['Domain'] = Domain
            data['WPemal'] = WPemal
            data['Owner'] = Owner
            data['userID'] = userID
            data['MysqlCPU'] = MysqlCPU
            data['MYsqlRam'] = MYsqlRam
            data['SiteCPU'] = SiteCPU
            data['SiteRam'] = SiteRam
            data['sitename'] = sitename
            data['WPusername'] = WPusername
            data['WPpasswd'] = WPpasswd
            data['externalApp'] = "".join(re.findall("[a-zA-Z]+", Domain))[:5] + str(randint(1000, 9999))
            data['App'] = App

            background = Docker_Sites('SubmitDockersiteCreation', data)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': tempStatusPath}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def ListDockerSites(self, request=None, userID=None, data=None, DeleteID=None):
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)
        fdata={}

        try:
            if DeleteID != None:

                DockerSitesDelete = DockerSites.objects.get(pk=DeleteID)
                if ACLManager.checkOwnership(DockerSitesDelete.admin.domain, admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadError()

                passdata={}
                passdata["domain"] = DockerSitesDelete.admin.domain
                passdata["JobID"] = None
                passdata['name'] = DockerSitesDelete.SiteName
                da = Docker_Sites(None, passdata)
                da.DeleteDockerApp()
                DockerSitesDelete.delete()
                fdata['Deleted'] = 1
        except BaseException as msg:
            fdata['LPError'] = 1
            fdata['LPMessage'] = str(msg)


        fdata['pagination'] = self.DockersitePagination(currentACL, userID)

        proc = httpProc(request, 'websiteFunctions/ListDockersite.html',
                        fdata)
        return proc.render()

    def fetchDockersite(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            pageNumber = int(data['page'])
            recordsToShow = int(data['recordsToShow'])


            endPageNumber, finalPageNumber = self.recordsPointer(pageNumber, recordsToShow)

            dockersites = ACLManager.findDockersiteObjects(currentACL, userID)
            pagination = self.getPagination(len(dockersites), recordsToShow)
            logging.CyberCPLogFileWriter.writeToFile("Our dockersite" + str(dockersites))


            json_data = self.findDockersitesListJson(dockersites[finalPageNumber:endPageNumber])


            final_dic = {'status': 1, 'listWebSiteStatus': 1, 'error_message': "None", "data": json_data,
                         'pagination': pagination}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'listWebSiteStatus': 1, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def Dockersitehome(self, request=None, userID=None, data=None, DeleteID=None):
        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        data = {
            "name": "docker-manager",
            "IP": ACLManager.GetServerIP()
        }

        import requests
        response = requests.post(url, data=json.dumps(data))
        Status = response.json()['status']

        if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            ds = DockerSites.objects.get(pk=self.domain)

            if ACLManager.checkOwnership(ds.admin.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            proc = httpProc(request, 'websiteFunctions/DockerSiteHome.html',
                            {'dockerSite': ds})
            return proc.render()
        else:
            from django.shortcuts import reverse
            return redirect(reverse('pricing'))
        
    def fetchWPSitesForDomain(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            
            domain = data['domain']
            website = Websites.objects.get(domain=domain)
            
            if ACLManager.checkOwnership(domain, admin, currentACL) != 1:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            wp_sites = WPSites.objects.filter(owner=website)
            sites = []
            
            Vhuser = website.externalApp
            PHPVersion = website.phpSelection

            php = ACLManager.getPHPString(PHPVersion)
            FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)
            
            for site in wp_sites:
                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp core version --skip-plugins --skip-themes --path=%s 2>/dev/null' % (
                    Vhuser, FinalPHPPath, site.path)
                version = ProcessUtilities.outputExecutioner(command, None, True)
                version = html.escape(version)

                # Get current theme
                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp theme list --status=active --field=name --skip-plugins --skip-themes --path=%s 2>/dev/null' % (
                    Vhuser, FinalPHPPath, site.path)
                currentTheme = ProcessUtilities.outputExecutioner(command, None, True)
                currentTheme = currentTheme.strip()

                # Get number of plugins
                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin list --field=name --skip-plugins --skip-themes --path=%s 2>/dev/null' % (
                    Vhuser, FinalPHPPath, site.path)
                plugins = ProcessUtilities.outputExecutioner(command, None, True)
                pluginCount = len([p for p in plugins.split('\n') if p.strip()])

                # Generate screenshot URL
                site_url = site.FinalURL
                if not site_url.startswith(('http://', 'https://')):
                    site_url = f'https://{site_url}'


                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp config list --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, site.path)
                stdout = ProcessUtilities.outputExecutioner(command)
                debugging = 0
                for items in stdout.split('\n'):
                    if items.find('WP_DEBUG	true	constant') > -1:
                        debugging = 1
                        break

                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp option get blog_public --skip-plugins --skip-themes --path=%s' % (
                    Vhuser, FinalPHPPath, site.path)
                stdoutput = ProcessUtilities.outputExecutioner(command)
                searchindex = int(stdoutput.splitlines()[-1])
                

                command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp maintenance-mode status --skip-plugins --skip-themes --path=%s' % (
                    Vhuser, FinalPHPPath, site.path)
                maintenanceMod = ProcessUtilities.outputExecutioner(command)

                result = maintenanceMod.splitlines()[-1]
                if result.find('not active') > -1:
                    maintenanceMode = 0
                else:
                    maintenanceMode = 1

                sites.append({
                    'id': site.id,
                    'title': site.title,
                    'url': site.FinalURL,
                    'path': site.path,
                    'version': version,
                    'phpVersion': site.owner.phpSelection,
                    'theme': currentTheme,
                    'activePlugins': pluginCount,
                    'debugging': debugging,
                    'searchIndex': searchindex,
                    'maintenanceMode': maintenanceMode,
                    'screenshot': f'https://api.microlink.io/?url={site_url}&screenshot=true&meta=false&embed=screenshot.url'
                })
                
            data_ret = {'status': 1, 'fetchStatus': 1, 'error_message': "None", "sites": sites}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchWPBackups(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            WPid = data['WPid']
            
            # Get the WordPress site
            wpsite = WPSites.objects.get(pk=WPid)
            
            # Check ownership
            if currentACL['admin'] != 1:
                if wpsite.owner != admin:
                    data_ret = {'status': 0, 'error_message': 'Not authorized to view this site backups'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
            
            # Get backups for this WordPress site
            backups = WPSitesBackup.objects.filter(WPSiteID=WPid).order_by('-id')
            
            backup_list = []
            for backup in backups:
                try:
                    config = json.loads(backup.config)
                    # Extract date from backup name (format: backup-wpsite.com-11.28.23_01-12-36)
                    backup_name = config.get('name', 'Unknown')
                    date_str = 'Unknown'
                    if 'backup-' in backup_name:
                        try:
                            # Extract date part from name
                            date_part = backup_name.split('-')[-1]  # Gets "11.28.23_01-12-36"
                            date_components = date_part.split('_')
                            if len(date_components) == 2:
                                date_str = date_components[0].replace('.', '/') + ' ' + date_components[1].replace('-', ':')
                        except:
                            date_str = backup_name
                    
                    backup_list.append({
                        'id': backup.id,
                        'name': backup_name,
                        'date': date_str,
                        'type': config.get('Backuptype', 'Full Backup'),
                        'size': config.get('size', '0')
                    })
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error parsing backup config: {str(e)}")
                    continue
            
            data_ret = {'status': 1, 'backups': backup_list}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
            
        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fixSubdomainLogs(self, request):
        """Display subdomain log fix interface"""
        try:
            currentACL = ACLManager.loadedACL(request.user.pk)
            admin = ACLManager.loadedAdmin(request.user.pk)

            if ACLManager.currentContextPermission(currentACL, 'websites') == 0:
                return ACLManager.loadErrorJson('websites', 0)

            return render(request, 'websiteFunctions/fixSubdomainLogs.html', {
                'acls': currentACL,
                'admin': admin
            })

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [fixSubdomainLogs]")
            return ACLManager.loadErrorJson('websites', 0)

    def fixSubdomainLogsAction(self, request):
        """Execute subdomain log fix"""
        try:
            currentACL = ACLManager.loadedACL(request.user.pk)
            admin = ACLManager.loadedAdmin(request.user.pk)

            if ACLManager.currentContextPermission(currentACL, 'websites') == 0:
                return ACLManager.loadErrorJson('websites', 0)

            action = request.POST.get('action')
            domain = request.POST.get('domain', '').strip()
            dry_run = request.POST.get('dry_run', 'false').lower() == 'true'
            create_backup = request.POST.get('create_backup', 'false').lower() == 'true'

            if action == 'fix_all':
                # Fix all child domains
                from websiteFunctions.models import ChildDomains
                child_domains = ChildDomains.objects.all()
                fixed_count = 0
                failed_domains = []
                
                for child_domain in child_domains:
                    if self._fix_single_domain_logs(child_domain.domain, dry_run, create_backup):
                        fixed_count += 1
                    else:
                        failed_domains.append(child_domain.domain)
                
                if failed_domains:
                    message = f"Fixed {fixed_count} domains. Failed: {', '.join(failed_domains)}"
                else:
                    message = f"Successfully fixed {fixed_count} child domains"
                    
                data_ret = {'status': 1, 'message': message}
                
            elif action == 'fix_domain' and domain:
                # Fix specific domain
                if self._fix_single_domain_logs(domain, dry_run, create_backup):
                    data_ret = {'status': 1, 'message': f"Successfully fixed logs for {domain}"}
                else:
                    data_ret = {'status': 0, 'error_message': f"Failed to fix logs for {domain}"}
            else:
                data_ret = {'status': 0, 'error_message': "Invalid action or missing domain"}
            
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [fixSubdomainLogsAction]")
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def _fix_single_domain_logs(self, domain_name, dry_run=False, create_backup=False):
        """Fix log configuration for a single domain"""
        try:
            import re
            import shutil
            from datetime import datetime
            from websiteFunctions.models import ChildDomains
            
            # Get child domain info
            try:
                child_domain = ChildDomains.objects.get(domain=domain_name)
                master_domain = child_domain.master.domain
                domain_path = child_domain.path
            except ChildDomains.DoesNotExist:
                logging.CyberCPLogFileWriter.writeToFile(f'Domain {domain_name} is not a child domain')
                return False
            
            vhost_conf_path = f"/usr/local/lsws/conf/vhosts/{domain_name}/vhost.conf"
            
            if not os.path.exists(vhost_conf_path):
                logging.CyberCPLogFileWriter.writeToFile(f'VHost config not found for {domain_name}')
                return False
            
            # Read current configuration
            with open(vhost_conf_path, 'r') as f:
                config_content = f.read()
            
            # Check if fix is needed
            if f'{master_domain}.error_log' not in config_content and f'{master_domain}.access_log' not in config_content:
                logging.CyberCPLogFileWriter.writeToFile(f'{domain_name} already has correct log configuration')
                return True
            
            if dry_run:
                logging.CyberCPLogFileWriter.writeToFile(f'[DRY RUN] Would fix log paths for {domain_name}')
                return True
            
            # Create backup if requested
            if create_backup:
                backup_path = f"{vhost_conf_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(vhost_conf_path, backup_path)
                logging.CyberCPLogFileWriter.writeToFile(f'Created backup: {backup_path}')
            
            # Fix the configuration
            fixed_content = config_content
            
            # Fix error log path
            fixed_content = re.sub(
                rf'errorlog\s+\$VH_ROOT/logs/{re.escape(master_domain)}\.error_log',
                f'errorlog $VH_ROOT/logs/{domain_name}.error_log',
                fixed_content
            )
            
            # Fix access log path
            fixed_content = re.sub(
                rf'accesslog\s+\$VH_ROOT/logs/{re.escape(master_domain)}\.access_log',
                f'accesslog $VH_ROOT/logs/{domain_name}.access_log',
                fixed_content
            )
            
            # Fix CustomLog paths (for Apache configurations)
            fixed_content = re.sub(
                rf'CustomLog\s+/home/{re.escape(master_domain)}/logs/{re.escape(master_domain)}\.access_log',
                f'CustomLog /home/{domain_name}/logs/{domain_name}.access_log',
                fixed_content
            )
            
            # Write the fixed configuration
            with open(vhost_conf_path, 'w') as f:
                f.write(fixed_content)
            
            # Set proper ownership
            ProcessUtilities.executioner(f'chown lsadm:lsadm {vhost_conf_path}')
            
            # Create the log directory if it doesn't exist
            log_dir = f"/home/{master_domain}/logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                ProcessUtilities.executioner(f'chown -R {child_domain.master.externalApp}:{child_domain.master.externalApp} {log_dir}')
            
            # Create separate log files for the child domain
            error_log_path = f"{log_dir}/{domain_name}.error_log"
            access_log_path = f"{log_dir}/{domain_name}.access_log"
            
            # Create empty log files if they don't exist
            for log_path in [error_log_path, access_log_path]:
                if not os.path.exists(log_path):
                    with open(log_path, 'w') as f:
                        f.write('')
                    ProcessUtilities.executioner(f'chown {child_domain.master.externalApp}:{child_domain.master.externalApp} {log_path}')
                    ProcessUtilities.executioner(f'chmod 644 {log_path}')
            
            # Restart LiteSpeed to apply changes
            ProcessUtilities.executioner('systemctl restart lsws')
            
            logging.CyberCPLogFileWriter.writeToFile(f'Fixed subdomain log configuration for {domain_name}')
            return True
            
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error fixing subdomain logs for {domain_name}: {str(e)}')
            return False

    def enableFTPQuota(self, userID=None, data=None):
        """
        Enable FTP quota system
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            
            # Check if user has permission
            if not (currentACL.get('admin', 0) == 1):
                return ACLManager.loadErrorJson('status', 0)
            
            # Backup existing configurations
            logging.CyberCPLogFileWriter.writeToFile("Backing up existing Pure-FTPd configurations...")
            
            import shutil
            from datetime import datetime
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Backup pure-ftpd.conf
            if os.path.exists('/etc/pure-ftpd/pure-ftpd.conf'):
                shutil.copy('/etc/pure-ftpd/pure-ftpd.conf', f'/etc/pure-ftpd/pure-ftpd.conf.backup.{timestamp}')
            
            # Backup pureftpd-mysql.conf
            if os.path.exists('/etc/pure-ftpd/pureftpd-mysql.conf'):
                shutil.copy('/etc/pure-ftpd/pureftpd-mysql.conf', f'/etc/pure-ftpd/pureftpd-mysql.conf.backup.{timestamp}')
            
            # Apply new configurations
            logging.CyberCPLogFileWriter.writeToFile("Applying FTP quota configurations...")
            
            # Copy updated configurations
            if os.path.exists('/usr/local/CyberCP/install/pure-ftpd/pure-ftpd.conf'):
                shutil.copy('/usr/local/CyberCP/install/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pure-ftpd.conf')
            
            if os.path.exists('/usr/local/CyberCP/install/pure-ftpd/pureftpd-mysql.conf'):
                shutil.copy('/usr/local/CyberCP/install/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-mysql.conf')
            
            # Restart Pure-FTPd
            logging.CyberCPLogFileWriter.writeToFile("Restarting Pure-FTPd service...")
            ProcessUtilities.executioner('systemctl restart pure-ftpd')
            
            # Verify configuration
            if ProcessUtilities.executioner('systemctl is-active --quiet pure-ftpd'):
                logging.CyberCPLogFileWriter.writeToFile("FTP quota system enabled successfully")
                
                data_ret = {
                    'status': 1,
                    'message': 'FTP quota system enabled successfully'
                }
            else:
                data_ret = {
                    'status': 0,
                    'message': 'Failed to restart Pure-FTPd service'
                }
            
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
            
        except Exception as e:
            data_ret = {
                'status': 0,
                'message': f'Error enabling FTP quota: {str(e)}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getFTPQuotas(self, userID=None, data=None):
        """
        Get FTP quota list
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            
            # Check if user has permission
            if not (currentACL.get('admin', 0) == 1):
                return ACLManager.loadErrorJson('status', 0)
            
            quotas = FTPQuota.objects.all().order_by('-created_at')
            
            quota_list = []
            for quota in quotas:
                quota_list.append({
                    'id': quota.id,
                    'ftp_user': quota.ftp_user,
                    'domain': quota.domain.domain if quota.domain else 'N/A',
                    'quota_size_mb': quota.quota_size_mb,
                    'quota_used_mb': quota.quota_used_mb,
                    'quota_percentage': quota.get_quota_percentage(),
                    'quota_files': quota.quota_files,
                    'quota_files_used': quota.quota_files_used,
                    'is_active': quota.is_active,
                    'created_at': quota.created_at.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            data_ret = {
                'status': 1,
                'quotas': quota_list
            }
            
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
            
        except Exception as e:
            data_ret = {
                'status': 0,
                'message': f'Error getting FTP quotas: {str(e)}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def updateFTPQuota(self, userID=None, data=None):
        """
        Update FTP quota
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            
            # Check if user has permission
            if not (currentACL.get('admin', 0) == 1):
                return ACLManager.loadErrorJson('status', 0)
            
            quota_id = data.get('quota_id')
            quota_size_mb = int(data.get('quota_size_mb', 0))
            quota_files = int(data.get('quota_files', 0))
            
            try:
                quota = FTPQuota.objects.get(id=quota_id)
                quota.quota_size_mb = quota_size_mb
                quota.quota_files = quota_files
                quota.save()
                
                data_ret = {
                    'status': 1,
                    'message': 'FTP quota updated successfully'
                }
            except FTPQuota.DoesNotExist:
                data_ret = {
                    'status': 0,
                    'message': 'FTP quota not found'
                }
            
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
            
        except Exception as e:
            data_ret = {
                'status': 0,
                'message': f'Error updating FTP quota: {str(e)}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def resetBandwidth(self, userID=None, data=None):
        """
        Reset bandwidth usage
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            
            # Check if user has permission
            if not (currentACL.get('admin', 0) == 1):
                return ACLManager.loadErrorJson('status', 0)
            
            reset_type = data.get('reset_type', 'manual')
            domain_name = data.get('domain', None)
            
            # Import bandwidth reset functionality
            from plogical.bandwidthReset import BandwidthReset
            
            if domain_name:
                # Reset individual domain
                try:
                    website = Websites.objects.get(domain=domain_name)
                    BandwidthReset.resetDomainBandwidth(domain_name)
                    
                    # Log the reset
                    BandwidthResetLog.objects.create(
                        reset_type=reset_type,
                        domain=website,
                        reset_by=admin,
                        domains_affected=1,
                        notes=f"Reset bandwidth for domain {domain_name}"
                    )
                    
                    data_ret = {
                        'status': 1,
                        'message': f'Bandwidth reset for {domain_name} completed successfully'
                    }
                except Websites.DoesNotExist:
                    data_ret = {
                        'status': 0,
                        'message': 'Domain not found'
                    }
            else:
                # Reset all domains
                reset_count, total_reset_mb = BandwidthReset.resetWebsiteBandwidth()
                
                # Log the reset
                BandwidthResetLog.objects.create(
                    reset_type=reset_type,
                    reset_by=admin,
                    domains_affected=reset_count,
                    bandwidth_reset_mb=total_reset_mb,
                    notes="Reset bandwidth for all domains"
                )
                
                data_ret = {
                    'status': 1,
                    'message': f'Bandwidth reset completed successfully. {reset_count} domains affected.'
                }
            
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
            
        except Exception as e:
            data_ret = {
                'status': 0,
                'message': f'Error resetting bandwidth: {str(e)}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getBandwidthResetLogs(self, userID=None, data=None):
        """
        Get bandwidth reset logs
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            
            # Check if user has permission
            if not (currentACL.get('admin', 0) == 1):
                return ACLManager.loadErrorJson('status', 0)
            
            logs = BandwidthResetLog.objects.all().order_by('-reset_at')[:50]  # Last 50 entries
            
            log_list = []
            for log in logs:
                log_list.append({
                    'id': log.id,
                    'reset_type': log.get_reset_type_display(),
                    'domain': log.domain.domain if log.domain else 'All Domains',
                    'reset_by': log.reset_by.userName,
                    'reset_at': log.reset_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'domains_affected': log.domains_affected,
                    'bandwidth_reset_mb': log.bandwidth_reset_mb,
                    'notes': log.notes or ''
                })
            
            data_ret = {
                'status': 1,
                'logs': log_list
            }
            
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
            
        except Exception as e:
            data_ret = {
                'status': 0,
                'message': f'Error getting bandwidth reset logs: {str(e)}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def scheduleBandwidthReset(self, userID=None, data=None):
        """
        Schedule automatic bandwidth reset
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            
            # Check if user has permission
            if not (currentACL.get('admin', 0) == 1):
                return ACLManager.loadErrorJson('status', 0)
            
            schedule_type = data.get('schedule_type', 'monthly')  # monthly, weekly, daily
            day_of_month = int(data.get('day_of_month', 1))  # 1-31 for monthly
            hour = int(data.get('hour', 2))  # 0-23
            minute = int(data.get('minute', 0))  # 0-59
            
            # Create cron job for bandwidth reset
            from plogical.cronUtil import CronUtil
            
            if schedule_type == 'monthly':
                cron_expression = f"{minute} {hour} {day_of_month} * *"
                job_name = "cyberpanel_bandwidth_reset_monthly"
            elif schedule_type == 'weekly':
                cron_expression = f"{minute} {hour} * * 0"  # Sunday
                job_name = "cyberpanel_bandwidth_reset_weekly"
            else:  # daily
                cron_expression = f"{minute} {hour} * * *"
                job_name = "cyberpanel_bandwidth_reset_daily"
            
            # Create the cron job
            command = f"/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/bandwidthReset.py --reset-all"
            
            # Remove existing bandwidth reset cron jobs
            CronUtil.removeCronByCommand(command)
            
            # Add new cron job
            CronUtil.addCronByCommand(command, cron_expression, job_name)
            
            data_ret = {
                'status': 1,
                'message': f'Bandwidth reset scheduled for {schedule_type} at {hour:02d}:{minute:02d}'
            }
            
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
            
        except Exception as e:
            data_ret = {
                'status': 0,
                'message': f'Error scheduling bandwidth reset: {str(e)}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def blockIPAddress(self, userID=None, data=None):
        """
        Block an IP address
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            
            # Check if user has permission
            if not (currentACL.get('admin', 0) == 1):
                return ACLManager.loadErrorJson('status', 0)
            
            ip_address = data.get('ip_address')
            reason = data.get('reason', 'Manual block via CyberPanel')
            
            if not ip_address:
                data_ret = {
                    'status': 0,
                    'message': 'IP address is required'
                }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            
            # Import firewall utilities
            from plogical.firewallUtilities import FirewallUtilities
            
            # Block the IP
            success, message = FirewallUtilities.blockIP(ip_address, reason)
            
            if success:
                data_ret = {
                    'status': 1,
                    'message': message
                }
            else:
                data_ret = {
                    'status': 0,
                    'message': message
                }
            
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
            
        except Exception as e:
            data_ret = {
                'status': 0,
                'message': f'Error blocking IP: {str(e)}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def unblockIPAddress(self, userID=None, data=None):
        """
        Unblock an IP address
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            
            # Check if user has permission
            if not (currentACL.get('admin', 0) == 1):
                return ACLManager.loadErrorJson('status', 0)
            
            ip_address = data.get('ip_address')
            
            if not ip_address:
                data_ret = {
                    'status': 0,
                    'message': 'IP address is required'
                }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            
            # Import firewall utilities
            from plogical.firewallUtilities import FirewallUtilities
            
            # Unblock the IP
            success, message = FirewallUtilities.unblockIP(ip_address)
            
            if success:
                data_ret = {
                    'status': 1,
                    'message': message
                }
            else:
                data_ret = {
                    'status': 0,
                    'message': message
                }
            
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
            
        except Exception as e:
            data_ret = {
                'status': 0,
                'message': f'Error unblocking IP: {str(e)}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getBlockedIPs(self, userID=None, data=None):
        """
        Get list of blocked IP addresses
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            
            # Check if user has permission
            if not (currentACL.get('admin', 0) == 1):
                return ACLManager.loadErrorJson('status', 0)
            
            # Import firewall utilities
            from plogical.firewallUtilities import FirewallUtilities
            
            # Get blocked IPs
            blocked_ips = FirewallUtilities.getBlockedIPs()
            
            data_ret = {
                'status': 1,
                'blocked_ips': blocked_ips
            }
            
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
            
        except Exception as e:
            data_ret = {
                'status': 0,
                'message': f'Error getting blocked IPs: {str(e)}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def checkIPStatus(self, userID=None, data=None):
        """
        Check if an IP is blocked
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            
            # Check if user has permission
            if not (currentACL.get('admin', 0) == 1):
                return ACLManager.loadErrorJson('status', 0)
            
            ip_address = data.get('ip_address')
            
            if not ip_address:
                data_ret = {
                    'status': 0,
                    'message': 'IP address is required'
                }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            
            # Import firewall utilities
            from plogical.firewallUtilities import FirewallUtilities
            
            # Check if IP is blocked
            is_blocked = FirewallUtilities.isIPBlocked(ip_address)
            
            data_ret = {
                'status': 1,
                'ip_address': ip_address,
                'is_blocked': is_blocked
            }
            
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
            
        except Exception as e:
            data_ret = {
                'status': 0,
                'message': f'Error checking IP status: {str(e)}'
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

