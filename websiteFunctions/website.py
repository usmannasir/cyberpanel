#!/usr/local/CyberCP/bin/python
import html
import os
import os.path
import sys
import django

from databases.models import Databases
from plogical.httpProc import httpProc

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from plogical.acl import ACLManager
import plogical.CyberCPLogFileWriter as logging
from websiteFunctions.models import Websites, ChildDomains, GitLogs, wpplugins, WPSites, WPStaging, WPSitesBackup, \
    RemoteBackupConfig, RemoteBackupSchedule, RemoteBackupsites
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
from emailMarketing.emACL import emACL
from plogical.processUtilities import ProcessUtilities
from managePHP.phpManager import PHPManager
from ApachController.ApacheVhosts import ApacheVhost
from plogical.vhostConfs import vhostConfs
from plogical.cronUtil import CronUtil
from .StagingSetup import StagingSetup
import validators


class WebsiteManager:
    apache = 1
    ols = 2
    lsws = 3

    def __init__(self, domain=None, childDomain=None):
        self.domain = domain
        self.childDomain = childDomain

    def createWebsite(self, request=None, userID=None, data=None):
        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"

        test_domain_data = {
            "name": "test-domain",
            "IP": ACLManager.GetServerIP(),
        }

        import requests
        response = requests.post(url, data=json.dumps(test_domain_data))
        test_domain_status = response.json()['status']

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

            test_domain_data = {
                "name": "test-domain",
                "IP": ACLManager.GetServerIP(),
            }

            import requests
            response = requests.post(url, data=json.dumps(test_domain_data))
            test_domain_status = response.json()['status']

            Data = {'packageList': packagesName, "owernList": adminNames, 'WPVersions': FinalVersions,
                    'Plugins': Plugins, 'Randam_String': rnpss.lower(), 'test_domain_data': test_domain_status}
            proc = httpProc(request, 'websiteFunctions/WPCreate.html',
                            Data, 'createWebsite')
            return proc.render()
        else:
            from django.shortcuts import reverse
            return redirect(reverse('pricing'))

    def ListWPSites(self, request=None, userID=None, DeleteID=None):
        currentACL = ACLManager.loadedACL(userID)

        admin = Administrator.objects.get(pk=userID)
        tata = {}
        tata['wp'] = []
        tata['wpsites'] = []
        tata['wp'] = ACLManager.GetALLWPObjects(currentACL, userID)

        try:
            if DeleteID != None:
                WPDelete = WPSites.objects.get(pk=DeleteID)

                if ACLManager.checkOwnership(WPDelete.owner.domain, admin, currentACL) == 1:
                    WPDelete.delete()

        except BaseException as msg:
            pass

        for sub in tata['wp']:
            tata['wpsites'].append({'id': sub.id,
                                    'title': sub.title,
                                    'url': sub.FinalURL
                                    })

        proc = httpProc(request, 'websiteFunctions/WPsitesList.html',
                        {"wpsite": tata['wpsites']})
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

            test_domain_url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"

            test_domain_data = {
                "name": "test-domain",
                "IP": ACLManager.GetServerIP(),
            }

            import requests
            response = requests.post(test_domain_url, data=json.dumps(test_domain_data))
            test_domain_status = response.json()['status']
            Data['test_domain_data'] = test_domain_status

            rnpss = randomPassword.generate_pass(10)

            Data['Randam_String'] = rnpss.lower()

            if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
                Data['wpsite'] = WPobj

                try:
                    DeleteID = request.GET.get('DeleteID', None)

                    if DeleteID != None:
                        wstagingDelete = WPStaging.objects.get(pk=DeleteID, owner=WPobj)
                        wstagingDelete.delete()

                except BaseException as msg:
                    da = str(msg)

                proc = httpProc(request, 'websiteFunctions/WPsiteHome.html',
                                Data, 'createWebsite')
                return proc.render()
            else:
                from django.shortcuts import reverse
                return redirect(reverse('pricing'))
        except:
            proc = httpProc(request, 'websiteFunctions/WPsiteHome.html',
                            Data, 'createWebsite')
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
            except:
                Data['Backuptype'] = None
            Data['WPsites'] = ACLManager.GetALLWPObjects(currentACL, userID)
            proc = httpProc(request, 'websiteFunctions/WPRestoreHome.html',
                            Data, 'createWebsite')
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
                            Data, 'createWebsite')
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
                            Data, 'createWebsite')
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
                            Data, 'createWebsite')
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

            if ACLManager.CheckIPBackupObjectOwner(currentACL, backobj, admin) == 1:
                pass
            else:
                return ACLManager.loadError()

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
                            Data, 'createWebsite')
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

        # php = VirtualHost.getPHPString(self.data['PHPVersion'])
        # FinalPHPPath = '/usr/local/lsws/lsphp%s/bin/php' % (php)

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

            command = 'sudo -u %s wp user create autologin %s --role=administrator --user_pass="%s" --path=%s --skip-plugins --skip-themes' % (
            WPobj.owner.externalApp, 'autologin@cloudpages.cloud', password, WPobj.path)
            ProcessUtilities.executioner(command)

            command = 'sudo -u %s wp user update autologin --user_pass="%s" --path=%s --skip-plugins --skip-themes' % (
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
                            data, 'createWebsite')
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
                            Data, 'createWebsite')
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
                            Data, 'createWebsite')
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
                        Data, 'createWebsite')
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

        test_domain_url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"

        test_domain_data = {
            "name": "test-domain",
            "IP": ACLManager.GetServerIP(),
        }

        import requests
        response = requests.post(test_domain_url, data=json.dumps(test_domain_data))
        test_domain_status = response.json()['status']

        rnpss = randomPassword.generate_pass(10)
        proc = httpProc(request, 'websiteFunctions/createDomain.html',
                        {'websiteList': websitesName, 'phps': PHPManager.findPHPVersions(), 'Randam_String': rnpss, 'test_domain_data':test_domain_status})
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

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp core version --skip-plugins --skip-themes --path=%s' % (
            Vhuser, FinalPHPPath, path)
            version = ProcessUtilities.outputExecutioner(command)
            version = html.escape(version)

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin status litespeed-cache --skip-plugins --skip-themes --path=%s' % (
            Vhuser, FinalPHPPath, path)
            lscachee = ProcessUtilities.outputExecutioner(command)

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
                'wpcron': wpcron

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

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp config get DB_NAME  --skip-plugins --skip-themes --path={wpsite.path}'
            retStatus, stdoutput = ProcessUtilities.outputExecutioner(command, wpsite.owner.externalApp, None, None, 1)

            if stdoutput.find('Error:') == -1:
                DataBaseName = stdoutput.rstrip("\n")
                DataBaseName = html.escape(DataBaseName)
            else:
                data_ret = {'status': 0, 'error_message': stdoutput}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp config get DB_USER  --skip-plugins --skip-themes --path={wpsite.path}'
            retStatus, stdoutput = ProcessUtilities.outputExecutioner(command, wpsite.owner.externalApp, None, None, 1)

            if stdoutput.find('Error:') == -1:
                DataBaseUser = stdoutput.rstrip("\n")
                DataBaseUser = html.escape(DataBaseUser)
            else:
                data_ret = {'status': 0, 'error_message': stdoutput}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            command = f'{FinalPHPPath} -d error_reporting=0 /usr/bin/wp config get table_prefix  --skip-plugins --skip-themes --path={wpsite.path}'
            retStatus, stdoutput = ProcessUtilities.outputExecutioner(command, wpsite.owner.externalApp, None, None, 1)

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
                #This code is only supposed to run if backups are s3, not for SFTP
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
                config = {}
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
                result, stdout = ProcessUtilities.outputExecutioner(command, None, None, None, 1)

                if result == 1:
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
                result, stdout = ProcessUtilities.outputExecutioner(command, None, None, None, 1)

                if result == 1:
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

            command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp core version --skip-plugins --skip-themes --path=%s' % (
                Vhuser, FinalPHPPath, path)
            version = ProcessUtilities.outputExecutioner(command)
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
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            WPManagerID = data['WPid']
            setting = data['setting']

            if setting == 'PasswordProtection':
                PPUsername = data['PPUsername']
                PPPassword = data['PPPassword']
            else:
                settingValue = data['settingValue']

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

            if setting == 'lscache':
                if settingValue:

                    command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin install litespeed-cache --path=%s --skip-plugins --skip-themes" % (
                    Vhuser, FinalPHPPath, path)
                    stdoutput = ProcessUtilities.outputExecutioner(command)

                    command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin activate litespeed-cache --path=%s --skip-plugins --skip-themes" % (
                    Vhuser, FinalPHPPath, path)
                    stdoutput = ProcessUtilities.outputExecutioner(command)


                else:
                    command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp plugin deactivate litespeed-cache --path=%s --skip-plugins --skip-themes' % (
                    Vhuser, FinalPHPPath, path)
                    stdoutput = ProcessUtilities.outputExecutioner(command)
            elif setting == 'debugging':

                command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp litespeed-purge all --path=%s --skip-plugins --skip-themes" % (
                Vhuser, FinalPHPPath, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)

                if settingValue:
                    command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp config set WP_DEBUG true --path=%s --skip-plugins --skip-themes" % (
                    Vhuser, FinalPHPPath, path)
                    stdoutput = ProcessUtilities.outputExecutioner(command)
                    logging.CyberCPLogFileWriter.writeToFile("Debugging mk true 1  output:" + str(stdoutput))

                    command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp config list --skip-plugins --skip-themes --path=%s' % (
                        Vhuser, FinalPHPPath, path)
                    stdout = ProcessUtilities.outputExecutioner(command)
                    logging.CyberCPLogFileWriter.writeToFile("Debugging output:" + str(stdout))


                else:
                    command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp config set WP_DEBUG false --path=%s --skip-plugins --skip-themes" % (
                    Vhuser, FinalPHPPath, path)
                    stdoutput = ProcessUtilities.outputExecutioner(command)
                    logging.CyberCPLogFileWriter.writeToFile("Debugging mk false 0  output:" + str(stdoutput))

                    command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp config list --skip-plugins --skip-themes --path=%s' % (
                        Vhuser, FinalPHPPath, path)
                    stdout = ProcessUtilities.outputExecutioner(command)
                    logging.CyberCPLogFileWriter.writeToFile("Debugging output:" + str(stdout))
            elif setting == 'searchIndex':

                command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp litespeed-purge all --path=%s --skip-plugins --skip-themes" % (
                Vhuser, FinalPHPPath, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)

                if settingValue:
                    command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp option update blog_public 1 --path=%s --skip-plugins --skip-themes" % (
                    Vhuser, FinalPHPPath, path)
                    stdoutput = ProcessUtilities.outputExecutioner(command)


                else:
                    command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp option update blog_public 0 --path=%s --skip-plugins --skip-themes" % (
                    Vhuser, FinalPHPPath, path)
                    stdoutput = ProcessUtilities.outputExecutioner(command)
            elif setting == 'maintenanceMode':

                command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp litespeed-purge all --path=%s --skip-plugins --skip-themes" % (
                Vhuser, FinalPHPPath, path)
                stdoutput = ProcessUtilities.outputExecutioner(command)

                if settingValue:

                    command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp maintenance-mode activate --path=%s --skip-plugins --skip-themes" % (
                    Vhuser, FinalPHPPath, path)
                    stdoutput = ProcessUtilities.outputExecutioner(command)


                else:
                    command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp maintenance-mode deactivate --path=%s --skip-plugins --skip-themes" % (
                    Vhuser, FinalPHPPath, path)
                    stdoutput = ProcessUtilities.outputExecutioner(command)
            elif setting == 'PasswordProtection':
                execPath = f"/usr/local/CyberCP/bin/python {virtualHostUtilities.cyberPanel}/plogical/virtualHostUtilities.py"
                execPath = f"{execPath} EnableDisablePP --username '{PPUsername}' --password '{PPPassword}' " \
                           f"--virtualHostName {Webobj.domain} --path {path} --wpid {str(wpsite.id)} --virtualHostUser {Webobj.externalApp}"
                ProcessUtilities.executioner(execPath)

            elif setting == 'Wpcron':

                command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp litespeed-purge all --path=%s --skip-plugins --skip-themes" % (
                    Vhuser, FinalPHPPath, path)

                stdoutput = ProcessUtilities.outputExecutioner(command)

                if settingValue:

                    command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp config set DISABLE_WP_CRON true --path=%s --skip-plugins --skip-themes" % (
                        Vhuser, FinalPHPPath, path)

                    stdoutput = ProcessUtilities.outputExecutioner(command)

                    logging.CyberCPLogFileWriter.writeToFile("Debugging mk true 1  output:" + str(stdoutput))

                    command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp config list --skip-plugins --skip-themes --path=%s' % (

                        Vhuser, FinalPHPPath, path)

                    stdout = ProcessUtilities.outputExecutioner(command)

                    logging.CyberCPLogFileWriter.writeToFile("Debugging output:" + str(stdout))



                else:

                    command = "sudo -u %s %s -d error_reporting=0 /usr/bin/wp config set DISABLE_WP_CRON false --path=%s --skip-plugins --skip-themes" % (
                        Vhuser, FinalPHPPath, path)

                    stdoutput = ProcessUtilities.outputExecutioner(command)

                    logging.CyberCPLogFileWriter.writeToFile("Debugging mk false 0  output:" + str(stdoutput))

                    command = 'sudo -u %s %s -d error_reporting=0 /usr/bin/wp config list --skip-plugins --skip-themes --path=%s' % (

                        Vhuser, FinalPHPPath, path)

                    stdout = ProcessUtilities.outputExecutioner(command)

                    logging.CyberCPLogFileWriter.writeToFile("Debugging output:" + str(stdout))

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

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
                       "' --virtualHostUser " + externalApp + " --ssl " + str(data['ssl']) + " --dkimCheck " \
                       + str(data['dkimCheck']) + " --openBasedir " + str(data['openBasedir']) + \
                       ' --websiteOwner "' + websiteOwner + '" --package "' + packageName + '" --tempStatusPath ' + tempStatusPath + " --apache " + apacheBackend + " --mailDomain %s" % (
                           mailDomain)

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

    def submitDomainCreation(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            masterDomain = data['masterDomain']
            domain = data['domainName']
            phpSelection = data['phpSelection']
            path = data['path']
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

            if len(path) > 0:
                path = path.lstrip("/")
                path = "/home/" + masterDomain + "/" + path
            else:
                path = "/home/" + masterDomain + "/" + domain

            try:
                apacheBackend = str(data['apacheBackend'])
            except:
                apacheBackend = "0"

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " createDomain --masterDomain " + masterDomain + " --virtualHostName " + domain + \
                       " --phpVersion '" + phpSelection + "' --ssl " + str(data['ssl']) + " --dkimCheck " + str(
                data['dkimCheck']) \
                       + " --openBasedir " + str(data['openBasedir']) + ' --path ' + path + ' --websiteOwner ' \
                       + admin.userName + ' --tempStatusPath ' + tempStatusPath + " --apache " + apacheBackend

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

            if ACLManager.checkOwnership(masterDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            cdManager = ChildDomainManager(masterDomain)
            json_data = cdManager.findChildDomainsJson()

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

            endPageNumber, finalPageNumber = self.recordsPointer(pageNumber, recordsToShow)
            websites = ACLManager.findWebsiteObjects(currentACL, userID)
            pagination = self.getPagination(len(websites), recordsToShow)
            json_data = self.findWebsitesListJson(websites[finalPageNumber:endPageNumber])

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
                    childDomains.append(child)

            pagination = self.getPagination(len(childDomains), recordsToShow)
            json_data = self.findChildsListJson(childDomains[finalPageNumber:endPageNumber])

            final_dic = {'status': 1, 'listWebSiteStatus': 1, 'error_message': "None", "data": json_data,
                         'pagination': pagination}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException as msg:
            dic = {'status': 1, 'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def findWebsitesListJson(self, websites):

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
                command = "mv " + confPath + " " + confPath + "-suspended"
                ProcessUtilities.popenExecutioner(command)

                childDomains = website.childdomains_set.all()

                for items in childDomains:
                    confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + items.domain
                    command = "mv " + confPath + " " + confPath + "-suspended"
                    ProcessUtilities.executioner(command)

                installUtilities.reStartLiteSpeedSocket()
                website.state = 0
            else:
                confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + websiteName

                command = "mv " + confPath + "-suspended" + " " + confPath
                ProcessUtilities.executioner(command)

                command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + confPath
                ProcessUtilities.popenExecutioner(command)

                childDomains = website.childdomains_set.all()

                for items in childDomains:
                    confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + items.domain

                    command = "mv " + confPath + "-suspended" + " " + confPath
                    ProcessUtilities.executioner(command)

                    command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + confPath
                    ProcessUtilities.popenExecutioner(command)

                installUtilities.reStartLiteSpeedSocket()
                website.state = 1

            website.save()

            data_ret = {'websiteStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:

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

            data_ret = {'status': 1, 'modifyStatus': 1, 'error_message': "None", "adminEmail": email,
                        "packages": json_data, "current_pack": currentPack, "adminNames": admin_data,
                        'currentAdmin': owner}
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

            ## Fix https://github.com/usmannasir/cyberpanel/issues/998

            #from plogical.IncScheduler import IncScheduler
            #isPU = IncScheduler('CalculateAndUpdateDiskUsage', {})
            #isPU.start()

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

            marketingStatus = emACL.checkIfEMEnabled(admin.userName)

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

                if Data['authority'] == 'Denial':
                    Data['authority'] = '%s has SELF-SIGNED SSL.' % (self.domain)
                else:
                    Data['authority'] = '%s has SSL from %s.' % (self.domain, Data['authority'])

            except BaseException as msg:
                Data['viewSSL'] = 0
                logging.CyberCPLogFileWriter.writeToFile(str(msg))

            servicePath = '/home/cyberpanel/pureftpd'
            if os.path.exists(servicePath):
                Data['ftp'] = 1
            else:
                Data['ftp'] = 0

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

                if Data['authority'] == 'Denial':
                    Data['authority'] = '%s has SELF-SIGNED SSL.' % (self.childDomain)
                else:
                    Data['authority'] = '%s has SSL from %s.' % (self.childDomain, Data['authority'])

            except BaseException as msg:
                Data['viewSSL'] = 0
                logging.CyberCPLogFileWriter.writeToFile(str(msg))

            proc = httpProc(request, 'websiteFunctions/launchChild.html', Data)
            return proc.render()
        else:
            proc = httpProc(request, 'websiteFunctions/launchChild.html',
                            {"error": 1, "domain": "This child domain does not exists"})
            return proc.render()

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

        if logType == 1:
            fileName = "/home/" + self.domain + "/logs/" + self.domain + ".access_log"
        else:
            fileName = "/home/" + self.domain + "/logs/" + self.domain + ".error_log"

        command = 'ls -la %s' % fileName
        result = ProcessUtilities.outputExecutioner(command)

        if result.find('->') > -1:
            final_json = json.dumps(
                {'status': 0, 'logstatus': 0,
                 'error_message': "Symlink attack."})
            return HttpResponse(final_json)

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
                logData = items.split(" ")
                domain = logData[5].strip('"')
                ipAddress = logData[0].strip('"')
                time = (logData[3]).strip("[").strip("]")
                resource = logData[6].strip('"')
                size = logData[9].replace('"', '')

                dic = {'domain': domain,
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

        fileName = "/home/" + self.domain + "/logs/" + self.domain + ".error_log"

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

    def saveConfigsToFile(self, userID=None, data=None):

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] != 1:
            return ACLManager.loadErrorJson('configstatus', 0)

        configData = data['configData']
        self.domain = data['virtualHost']

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

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                command = 'chmod 600 %s' % (cronPath)
                ProcessUtilities.executioner(command)

                command = 'systemctl restart cron'
                ProcessUtilities.executioner(command)

            CronUtil.CronPrem(0)

            if output.find("1,") > -1:

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
            data['dkimCheck'] = 0
            data['openBasedir'] = 1
            data['adminEmail'] = data['ownerEmail']
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

        phpFPMConf = vhostConfs.phpFpmPoolReplace
        phpFPMConf = phpFPMConf.replace('{externalApp}', externalApp)
        phpFPMConf = phpFPMConf.replace('{pmMaxChildren}', pmMaxChildren)
        phpFPMConf = phpFPMConf.replace('{pmStartServers}', pmStartServers)
        phpFPMConf = phpFPMConf.replace('{pmMinSpareServers}', pmMinSpareServers)
        phpFPMConf = phpFPMConf.replace('{pmMaxSpareServers}', pmMaxSpareServers)
        phpFPMConf = phpFPMConf.replace('{www}', "".join(re.findall("[a-zA-Z]+", domainName))[:7])
        phpFPMConf = phpFPMConf.replace('{Sock}', domainName)

        writeToFile = open(tempStatusPath, 'w')
        writeToFile.writelines(phpFPMConf)
        writeToFile.close()

        command = 'sudo mv %s %s' % (tempStatusPath, phpPath)
        ProcessUtilities.executioner(command)

        phpPath = phpPath.split('/')

        if phpPath[1] == 'etc':
            phpVersion = phpPath[4][3] + phpPath[4][4]
        else:
            phpVersion = phpPath[3][3] + phpPath[3][4]

        command = "systemctl stop php%s-php-fpm" % (phpVersion)
        ProcessUtilities.executioner(command)

        command = "systemctl restart php%s-php-fpm" % (phpVersion)
        ProcessUtilities.executioner(command)

        data_ret = {'status': 1}
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

        proc = httpProc(request, 'websiteFunctions/sshAccess.html',
                        {'domainName': self.domain, 'externalApp': externalApp})
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

            if website.externalApp != data['externalApp']:
                data_ret = {'status': 0, 'error_message': 'External app mis-match.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            uBuntuPath = '/etc/lsb-release'

            if os.path.exists(uBuntuPath):
                command = "echo '%s:%s' | chpasswd" % (data['externalApp'], data['password'])
            else:
                command = 'echo "%s" | passwd --stdin %s' % (data['password'], data['externalApp'])

            ProcessUtilities.executioner(command)

            data_ret = {'status': 1, 'error_message': 'None'}
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

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/firewallUtilities.py"
            execPath = execPath + " deleteSSHKey --key '%s' --path %s" % (key, pathToKeyFile)

            output = ProcessUtilities.outputExecutioner(execPath)

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
