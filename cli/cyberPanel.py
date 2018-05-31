#!/usr/bin/env python2.7
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import argparse
from inspect import stack
from cliLogger import cliLogger as logger
import json
from plogical.virtualHostUtilities import virtualHostUtilities
import re
from websiteFunctions.models import Websites, ChildDomains
from plogical.vhost import vhost

class cyberPanel:
    def printStatus(self, operationStatus, errorMessage):
        data = json.dumps({'success': operationStatus,
                           'errorMessage': errorMessage
                        })

        print data

    def createWebsite(self, package, owner, domainName, email, php, ssl, dkim, openBasedir):
        try:
            externalApp = "".join(re.findall("[a-zA-Z]+", domainName))[:7]
            numberOfWebsites = str(Websites.objects.count() + ChildDomains.objects.count())
            sslpath = "/home/" + domainName + "/public_html"
            phpSelection = 'PHP ' + php

            result = virtualHostUtilities.createVirtualHost(domainName, email, phpSelection, externalApp, numberOfWebsites, ssl, sslpath, dkim,
                              openBasedir, owner, package)

            if result[0] == 1:
                self.printStatus(1,'None')
            else:
                self.printStatus(0, result[1])

        except BaseException, msg:
            logger.writeforCLI(str(msg), "Error", stack()[0][3])
            self.printStatus(0, str(msg))

    def deleteWebsite(self, domainName):
        try:

            numberOfWebsites = Websites.objects.count() + ChildDomains.objects.count()
            vhost.deleteVirtualHostConfigurations(domainName, numberOfWebsites)
            self.printStatus(1, 'None')

        except BaseException, msg:
            logger.writeforCLI(str(msg), "Error", stack()[0][3])
            print 0



def main():

    parser = argparse.ArgumentParser(description='CyberPanel Command Line Interface!')
    parser.add_argument('function', help='Specific a operation to perform!')


    ## Website creation arguemtns
    parser.add_argument('--package', help='Select a package for website.')
    parser.add_argument('--owner', help='Select a website owner.')
    parser.add_argument('--domainName', help='Domain name!')
    parser.add_argument('--email', help='Administrator email.')
    parser.add_argument('--php', help='Administrator email.')
    parser.add_argument('--ssl', help='Weather to obtain SSL.')
    parser.add_argument('--dkim', help='DKIM Signing')
    parser.add_argument('--openBasedir', help='To enable or disable open_basedir protection for domain.')


    args = parser.parse_args()

    if args.function == "createWebsite":

        completeCommandExample = 'cyberpanel createWebsite --package Detault --owner admin --domainName cyberpanel.net --email support@cyberpanel.net --php 5.6'

        if not args.package:
            print "\n\nPlease enter the package name. For example:\n\n" + completeCommandExample + "\n\n"

        if not args.owner:
            print "\n\nPlease enter the owner name. For example:\n\n" + completeCommandExample + "\n\n"

        if not args.domainName:
            print "\n\nPlease enter the domain name. For example:\n\n" + completeCommandExample + "\n\n"

        if not args.email:
            print "\n\nPlease enter the email. For example:\n\n" + completeCommandExample + "\n\n"

        if not args.php:
            print "\n\nPlease enter the PHP version such as 5.6 for PHP version 5.6. For example:\n\n" + completeCommandExample + "\n\n"

        if args.ssl:
            ssl = args.ssl
        else:
            ssl = 0

        if args.dkim:
            dkim = args.dkim
        else:
            dkim = 0

        if args.openBasedir:
            openBasedir = args.openBasedir
        else:
            openBasedir = 0

        cyberpanel = cyberPanel()
        cyberpanel.createWebsite(args.package, args.owner, args.domainName, args.email, args.php, ssl, dkim, openBasedir)
    elif args.function == "deleteWebsite":

        completeCommandExample = 'cyberpanel deleteWebsite --domainName cyberpanel.net'

        if not args.domainName:
            print "\n\nPlease enter the domain to delete. For example:\n\n" + completeCommandExample + "\n\n"
            return

        cyberpanel = cyberPanel()
        cyberpanel.deleteWebsite(args.domainName)

if __name__ == "__main__":
    main()