#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django
from plogical.httpProc import httpProc
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from django.shortcuts import redirect
from django.http import HttpResponse
from loginSystem.views import loadLoginPage
from loginSystem.models import Administrator
import json
from .models import Package
from plogical.acl import ACLManager
from plogical.processUtilities import ProcessUtilities

class PackagesManager:
    def __init__(self, request = None):
        self.request  = request

    @staticmethod
    def checkAddonAccess():
        """
        Check if server has addon access for resource limits feature
        Returns True if addons are available, False otherwise
        """
        url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        addon_data = {
            "name": "all",
            "IP": ACLManager.GetServerIP()
        }
        import requests
        try:
            response = requests.post(url, data=json.dumps(addon_data), timeout=5)
            Status = response.json().get('status', 0)
        except Exception:
            Status = 0
        return (Status == 1) or (ProcessUtilities.decideServer() == ProcessUtilities.ent)

    def packagesHome(self):
        proc = httpProc(self.request, 'packages/index.html',
                        None, 'createPackage')
        return proc.render()

    def createPacakge(self):
        userID = self.request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        has_addons = self.checkAddonAccess()
        proc = httpProc(self.request, 'packages/createPackage.html',
                        {"adminNamePackage": admin.userName, "has_addons": has_addons}, 'createPackage')
        return proc.render()

    def deletePacakge(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        packageList = ACLManager.loadPackages(userID, currentACL)
        proc = httpProc(self.request, 'packages/deletePackage.html',
                        {"packageList": packageList}, 'deletePackage')
        return proc.render()

    def submitPackage(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'createPackage') == 0:
                return ACLManager.loadErrorJson('saveStatus', 0)

            data = json.loads(self.request.body)
            packageName = data['packageName'].replace(' ', '')
            packageSpace = int(data['diskSpace'])
            packageBandwidth = int(data['bandwidth'])
            packageDatabases = int(data['dataBases'])
            ftpAccounts = int(data['ftpAccounts'])
            emails = int(data['emails'])
            allowedDomains = int(data['allowedDomains'])

            try:
                api = data['api']
            except:
                api = '0'

            try:
                allowFullDomain = int(data['allowFullDomain'])
            except:
                allowFullDomain = 1

            try:
                enforceDiskLimits = int(data['enforceDiskLimits'])
            except:
                enforceDiskLimits = 0

            # Resource Limits - with backward compatibility
            try:
                memoryLimitMB = int(data['memoryLimitMB'])
            except:
                memoryLimitMB = 1024

            try:
                cpuCores = int(data['cpuCores'])
            except:
                cpuCores = 1

            try:
                ioLimitMBPS = int(data['ioLimitMBPS'])
            except:
                ioLimitMBPS = 10

            try:
                inodeLimit = int(data['inodeLimit'])
            except:
                inodeLimit = 400000

            try:
                maxConnections = int(data['maxConnections'])
            except:
                maxConnections = 10

            try:
                procSoftLimit = int(data['procSoftLimit'])
            except:
                procSoftLimit = 400

            try:
                procHardLimit = int(data['procHardLimit'])
            except:
                procHardLimit = 500

            if packageSpace < 0 or packageBandwidth < 0 or packageDatabases < 0 or ftpAccounts < 0 or emails < 0 or allowedDomains < 0:
                data_ret = {'saveStatus': 0, 'error_message': "All values should be positive or 0."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Check addon access for resource limits feature
            has_addons = self.checkAddonAccess()
            if not has_addons and enforceDiskLimits == 1:
                data_ret = {'saveStatus': 0, 'error_message': "Resource limits feature requires CyberPanel addons. Please visit https://cyberpanel.net/cyberpanel-addons to purchase."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Reset resource limits to defaults if addons not available
            if not has_addons:
                enforceDiskLimits = 0
                memoryLimitMB = 1024
                cpuCores = 1
                ioLimitMBPS = 10
                inodeLimit = 400000
                maxConnections = 10
                procSoftLimit = 400
                procHardLimit = 500

            # Validate resource limits
            if memoryLimitMB < 256 or cpuCores < 1 or ioLimitMBPS < 1 or inodeLimit < 10000 or maxConnections < 1 or procSoftLimit < 1 or procHardLimit < 1:
                data_ret = {'saveStatus': 0, 'error_message': "Resource limits must be positive and within valid ranges."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            admin = Administrator.objects.get(pk=userID)

            if api == '0':
                packageName = admin.userName + "_" + packageName

            package = Package(admin=admin, packageName=packageName, diskSpace=packageSpace,
                              bandwidth=packageBandwidth, ftpAccounts=ftpAccounts, dataBases=packageDatabases,
                              emailAccounts=emails, allowedDomains=allowedDomains, allowFullDomain=allowFullDomain,
                              enforceDiskLimits=enforceDiskLimits, memoryLimitMB=memoryLimitMB, cpuCores=cpuCores,
                              ioLimitMBPS=ioLimitMBPS, inodeLimit=inodeLimit, maxConnections=maxConnections,
                              procSoftLimit=procSoftLimit, procHardLimit=procHardLimit)

            package.save()

            data_ret = {'status': 1, 'saveStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitDelete(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deletePackage') == 0:
                return ACLManager.loadErrorJson('deleteStatus', 0)

            data = json.loads(self.request.body)
            packageName = data['packageName']

            delPackage = Package.objects.get(packageName=packageName)

            ## Check package ownership
            admin = Administrator.objects.get(pk=userID)
            if ACLManager.CheckPackageOwnership(delPackage, admin, currentACL) == 0:
                return ACLManager.loadErrorJson('deleteStatus', 0)

            delPackage.delete()

            data_ret = {'status': 1, 'deleteStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'status': 0, 'deleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def modifyPackage(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        packageList = ACLManager.loadPackages(userID, currentACL)
        has_addons = self.checkAddonAccess()
        proc = httpProc(self.request, 'packages/modifyPackage.html',
                        {"packList": packageList, "has_addons": has_addons}, 'modifyPackage')
        return proc.render()

    def submitModify(self):
        try:
            userID = self.request.session['userID']
            data = json.loads(self.request.body)
            packageName = data['packageName']

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'modifyPackage') == 0:
                return ACLManager.loadErrorJson('modifyStatus', 0)

            modifyPack = Package.objects.get(packageName=packageName)

            ## Check package ownership
            admin = Administrator.objects.get(pk=userID)
            if ACLManager.CheckPackageOwnership(modifyPack, admin, currentACL) == 0:
                return ACLManager.loadErrorJson('deleteStatus', 0)

            diskSpace = modifyPack.diskSpace
            bandwidth = modifyPack.bandwidth
            ftpAccounts = modifyPack.ftpAccounts
            dataBases = modifyPack.dataBases
            emails = modifyPack.emailAccounts


            data_ret = {'emails': emails, 'modifyStatus': 1, 'error_message': "None",
                        "diskSpace": diskSpace, "bandwidth": bandwidth, "ftpAccounts": ftpAccounts,
                        "dataBases": dataBases, "allowedDomains": modifyPack.allowedDomains,
                        'allowFullDomain': modifyPack.allowFullDomain, 'enforceDiskLimits': modifyPack.enforceDiskLimits,
                        'memoryLimitMB': modifyPack.memoryLimitMB, 'cpuCores': modifyPack.cpuCores,
                        'ioLimitMBPS': modifyPack.ioLimitMBPS, 'inodeLimit': modifyPack.inodeLimit,
                        'maxConnections': modifyPack.maxConnections, 'procSoftLimit': modifyPack.procSoftLimit,
                        'procHardLimit': modifyPack.procHardLimit}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'modifyStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def saveChanges(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            admin = Administrator.objects.get(pk=userID)

            if ACLManager.currentContextPermission(currentACL, 'modifyPackage') == 0:
                return ACLManager.loadErrorJson('saveStatus', 0)

            data = json.loads(self.request.body)
            packageName = data['packageName']

            if data['diskSpace'] < 0 or data['bandwidth'] < 0 or data['ftpAccounts'] < 0 or data[
                'dataBases'] < 0 or \
                            data['emails'] < 0 or data['allowedDomains'] < 0:
                data_ret = {'saveStatus': 0, 'error_message': "All values should be positive or 0."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            modifyPack = Package.objects.get(packageName=packageName)

            if modifyPack.admin == admin:

                modifyPack.diskSpace = data['diskSpace']
                modifyPack.bandwidth = data['bandwidth']
                modifyPack.ftpAccounts = data['ftpAccounts']
                modifyPack.dataBases = data['dataBases']
                modifyPack.emailAccounts = data['emails']
                modifyPack.allowedDomains = data['allowedDomains']

                try:
                    modifyPack.allowFullDomain = int(data['allowFullDomain'])
                except:
                    modifyPack.allowFullDomain = 1

                try:
                    modifyPack.enforceDiskLimits = int(data['enforceDiskLimits'])
                except:
                    modifyPack.enforceDiskLimits = 0

                # Check addon access for resource limits feature
                has_addons = self.checkAddonAccess()
                if not has_addons and modifyPack.enforceDiskLimits == 1:
                    data_ret = {'saveStatus': 0, 'error_message': "Resource limits feature requires CyberPanel addons. Please visit https://cyberpanel.net/cyberpanel-addons to purchase."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                # Reset resource limits to defaults if addons not available
                if not has_addons:
                    modifyPack.enforceDiskLimits = 0
                    modifyPack.memoryLimitMB = 1024
                    modifyPack.cpuCores = 1
                    modifyPack.ioLimitMBPS = 10
                    modifyPack.inodeLimit = 400000
                    modifyPack.maxConnections = 10
                    modifyPack.procSoftLimit = 400
                    modifyPack.procHardLimit = 500

                # Update resource limits (only if addons available)
                if has_addons:
                    try:
                        modifyPack.memoryLimitMB = int(data['memoryLimitMB'])
                    except:
                        pass  # Keep existing value

                    try:
                        modifyPack.cpuCores = int(data['cpuCores'])
                    except:
                        pass  # Keep existing value

                    try:
                        modifyPack.ioLimitMBPS = int(data['ioLimitMBPS'])
                    except:
                        pass  # Keep existing value

                    try:
                        modifyPack.inodeLimit = int(data['inodeLimit'])
                    except:
                        pass  # Keep existing value

                    try:
                        modifyPack.maxConnections = int(data['maxConnections'])
                    except:
                        pass  # Keep existing value

                    try:
                        modifyPack.procSoftLimit = int(data['procSoftLimit'])
                    except:
                        pass  # Keep existing value

                    try:
                        modifyPack.procHardLimit = int(data['procHardLimit'])
                    except:
                        pass  # Keep existing value

                modifyPack.save()

                ## Fix https://github.com/usmannasir/cyberpanel/issues/998

                # from plogical.IncScheduler import IncScheduler
                # isPU = IncScheduler('CalculateAndUpdateDiskUsage', {})
                # isPU.start()

                from plogical.processUtilities import ProcessUtilities
                command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/IncScheduler.py UpdateDiskUsageForce'
                ProcessUtilities.outputExecutioner(command)

                data_ret = {'status': 1, 'saveStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'saveStatus': 0, 'error_message': "You don't own this package."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


    def listPackages(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        packageList = ACLManager.loadPackages(userID, currentACL)
        proc = httpProc(self.request, 'packages/listPackages.html',
                        {"packList": packageList}, 'listPackages')
        return proc.render()

    def listPackagesAPI(self,data=None):
        """
            List of packages for API
        :param data:
        :return HttpResponse:
        """
        try:
            adminUser = data['adminUser']
            admin = Administrator.objects.get(userName=adminUser)
            currentACL = ACLManager.loadedACL(admin.id)
            packageList = ACLManager.loadPackages(admin.id, currentACL)
            return HttpResponse(json.dumps(packageList))
        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchPackagesTable(self):
        try:
            userID = self.request.session['userID']

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listPackages') == 0:
                return ACLManager.loadErrorJson()


            packages = ACLManager.loadPackageObjects(userID, currentACL)

            json_data = "["
            checker = 0

            for items in packages:

                dic = {'package': items.packageName,
                       'diskSpace': items.diskSpace,
                       'bandwidth': items.bandwidth,
                       'emailAccounts': items.emailAccounts,
                       'dataBases': items.dataBases,
                       'ftpAccounts': items.ftpAccounts,
                       'allowedDomains': items.allowedDomains,
                       'allowFullDomain': items.allowFullDomain,
                       'enforceDiskLimits': items.enforceDiskLimits
                       }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except KeyError:
            return redirect(loadLoginPage)
