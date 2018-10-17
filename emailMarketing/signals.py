from django.dispatch import receiver
from django.shortcuts import render
from websiteFunctions.signals import preDomain
from emACL import emACL



@receiver(preDomain)
def loadDomainHome(sender, **kwargs):
    from websiteFunctions.models import Websites
    from loginSystem.models import Administrator
    from plogical.virtualHostUtilities import virtualHostUtilities
    import subprocess, shlex
    import plogical.CyberCPLogFileWriter as logging
    from plogical.acl import ACLManager

    request = kwargs['request']
    domain = request.GET['domain']
    userID = request.session['userID']

    if Websites.objects.filter(domain=domain).exists():

        currentACL = ACLManager.loadedACL(userID)
        website = Websites.objects.get(domain=domain)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        marketingStatus = emACL.checkIfEMEnabled(admin.userName)

        Data = {}

        Data['ftpTotal'] = website.package.ftpAccounts
        Data['ftpUsed'] = website.users_set.all().count()

        Data['databasesUsed'] = website.databases_set.all().count()
        Data['databasesTotal'] = website.package.dataBases
        Data['marketingStatus'] = marketingStatus

        Data['domain'] = domain

        diskUsageDetails = virtualHostUtilities.getDiskUsage("/home/" + domain, website.package.diskSpace)

        try:
            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " findDomainBW --virtualHostName " + domain + " --bandwidth " + str(
                website.package.bandwidth)

            output = subprocess.check_output(shlex.split(execPath))
            bwData = output.split(",")
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            bwData = [0, 0]

        ## bw usage calculations

        Data['bwInMBTotal'] = website.package.bandwidth
        Data['bwInMB'] = bwData[0]
        Data['bwUsage'] = bwData[1]

        if diskUsageDetails != None:
            if diskUsageDetails[1] > 100:
                diskUsageDetails[1] = 100

            Data['diskUsage'] = diskUsageDetails[1]
            Data['diskInMB'] = diskUsageDetails[0]
            Data['diskInMBTotal'] = website.package.diskSpace
        else:
            Data['diskUsage'] = 0
            Data['diskInMB'] = 0
            Data['diskInMBTotal'] = website.package.diskSpace

        return render(request, 'emailMarketing/website.html', Data)
    else:
        return render(request, 'emailMarketing/website.html',
                        {"error": 1, "domain": "This domain does not exists."})