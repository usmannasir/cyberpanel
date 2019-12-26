# -*- coding: utf-8 -*-

import sys
import importlib

importlib.reload(sys)
from django.shortcuts import render, redirect
from loginSystem.views import loadLoginPage
from .models import PHP, installedPackages, ApachePHP, installedPackagesApache
from django.http import HttpResponse
import json
from plogical.phpUtilities import phpUtilities
import os
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import re
from plogical.virtualHostUtilities import virtualHostUtilities
import shlex
from random import randint
from xml.etree import ElementTree
from plogical.acl import ACLManager
from plogical.processUtilities import ProcessUtilities
from .phpManager import PHPManager


# Create your views here.


def loadPHPHome(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        return render(request, 'managePHP/index.html')
    except KeyError:
        return redirect(loadLoginPage)


def installExtensions(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        if PHP.objects.count() == 0:
            for i in range(3, 7):
                php = "php" + str(5) + str(i)
                newPHP = PHP(phpVers=php)
                newPHP.save()

            newPHP = PHP(phpVers="php70")
            newPHP.save()
            newPHP = PHP(phpVers="php71")
            newPHP.save()

            ### Gather php 53 information

            php53 = PHP.objects.get(phpVers="php53")

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-bcmath",
                                             description="A module for PHP applications for using the bcmath library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-common",
                                             description="Common files for PHP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-dba",
                                             description="A database abstraction layer module for PHP applications",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-enchant",
                                             description="Human Language and Character Encoding Support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-gd",
                                             description="A module for PHP applications for using the gd graphics library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-imap",
                                             description="A module for PHP applications that use IMAP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-intl",
                                             description="Internationalization extension for PHP application",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-ioncube-loader",
                                             description="Ioncube Loader",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-ldap",
                                             description="A module for PHP applications that use LDAP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-mbstring",
                                             description="A module for PHP applications which need multi-byte string handling",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-mcrypt",
                                             description="Standard PHP module provides mcrypt library support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-mysql",
                                             description="A module for PHP applications that use MySQL databases",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-odbc",
                                             description="A module for PHP applications that use ODBC databases",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-pdo",
                                             description="A database access abstraction module for PHP applications",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-pear",
                                             description="PHP Extension and Application Repository framework",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-pecl-apc",
                                             description="APC caches and optimizes PHP intermediate code",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-pgsql",
                                             description="A PostgreSQL database module for PHP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-process",
                                             description="Modules for PHP script using system process interfaces",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-pspell",
                                             description="A module for PHP applications for using pspell interfaces",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-recode",
                                             description="A module for PHP applications for using the recode library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-snmp",
                                             description="A module for PHP applications that query SNMP-managed devices",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-soap",
                                             description="A module for PHP applications that use the SOAP protocol",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-tidy",
                                             description="Standard PHP module provides tidy library support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-xml",
                                             description="A module for PHP applications which use XML",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-xmlrpc",
                                             description="A module for PHP applications which use the XML-RPC protocol",
                                             status=1)

            phpExtension.save()

            ## non-active packages


            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-debuginfo",
                                             description="Debug information for package lsphp53",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-lsphp53-devel",
                                             description="Files needed for building PHP extensions",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-mysql56",
                                             description="PHP scripting language for creating dynamic web sites",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-mysqlnd",
                                             description="A module for PHP applications that use MySQL databases",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-opcache",
                                             description="The Zend OPcache",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-pecl-apc-devel",
                                             description="APC developer files (header)",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-pecl-apc-panel",
                                             description="APC control panel",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-sqlite",
                                             description="Extension for the SQLite V2 Embeddable SQL Database Engine",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-xcache",
                                             description="PHP accelerator, optimizer, encoder and dynamic content cacher",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp53-xcache-admin",
                                             description="XCache Administration",
                                             status=0)

            phpExtension.save()

            ### ################ #################

            ##### Gather php 54 information

            ### ################ #################

            php54 = PHP.objects.get(phpVers="php54")

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-bcmath",
                                             description="A module for PHP applications for using the bcmath library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-common",
                                             description="Common files for PHP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp53-dba",
                                             description="A database abstraction layer module for PHP applications",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp54-enchant",
                                             description="Human Language and Character Encoding Support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-gd",
                                             description="A module for PHP applications for using the gd graphics library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-imap",
                                             description="A module for PHP applications that use IMAP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp54-intl",
                                             description="Internationalization extension for PHP application",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-ioncube-loader",
                                             description="Ioncube Loader",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-ldap",
                                             description="A module for PHP applications that use LDAP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-mbstring",
                                             description="A module for PHP applications which need multi-byte string handling",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-mcrypt",
                                             description="Standard PHP module provides mcrypt library support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-mysql",
                                             description="A module for PHP applications that use MySQL databases",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-odbc",
                                             description="A module for PHP applications that use ODBC databases",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-pdo",
                                             description="A database access abstraction module for PHP applications",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-pear",
                                             description="PHP Extension and Application Repository framework",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-pecl-apc",
                                             description="APC caches and optimizes PHP intermediate code",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php53,
                                             extensionName="lsphp54-pgsql",
                                             description="A PostgreSQL database module for PHP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-process",
                                             description="Modules for PHP script using system process interfaces",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-pspell",
                                             description="A module for PHP applications for using pspell interfaces",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-recode",
                                             description="A module for PHP applications for using the recode library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-snmp",
                                             description="A module for PHP applications that query SNMP-managed devices",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-soap",
                                             description="A module for PHP applications that use the SOAP protocol",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-tidy",
                                             description="Standard PHP module provides tidy library support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-xml",
                                             description="A module for PHP applications which use XML",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-xmlrpc",
                                             description="A module for PHP applications which use the XML-RPC protocol",
                                             status=1)

            phpExtension.save()

            ## non-active packages


            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-debuginfo",
                                             description="Debug information for package lsphp54",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-mysql56-debuginfo",
                                             description="Debug information for package lsphp54-mysql56",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-lsphp53-devel",
                                             description="Files needed for building PHP extensions",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-mysql56",
                                             description="PHP scripting language for creating dynamic web sites",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-mysqlnd",
                                             description="A module for PHP applications that use MySQL databases",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-opcache",
                                             description="The Zend OPcache",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-pecl-apc-devel",
                                             description="APC developer files (header)",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-pecl-apc-panel",
                                             description="APC control panel",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-sqlite",
                                             description="Extension for the SQLite V2 Embeddable SQL Database Engine",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-xcache",
                                             description="PHP accelerator, optimizer, encoder and dynamic content cacher",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp54-xcache-admin",
                                             description="XCache Administration",
                                             status=0)

            phpExtension.save()

            ### ################ #################

            ##### Gather php 55 information

            ### ################ #################

            php55 = PHP.objects.get(phpVers="php55")

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-bcmath",
                                             description="A module for PHP applications for using the bcmath library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-common",
                                             description="Common files for PHP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-dba",
                                             description="A database abstraction layer module for PHP applications",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-enchant",
                                             description="Human Language and Character Encoding Support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-gd",
                                             description="A module for PHP applications for using the gd graphics library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-imap",
                                             description="A module for PHP applications that use IMAP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-intl",
                                             description="Internationalization extension for PHP application",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-ioncube-loader",
                                             description="Ioncube Loader",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-ldap",
                                             description="A module for PHP applications that use LDAP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-mbstring",
                                             description="A module for PHP applications which need multi-byte string handling",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-mcrypt",
                                             description="Standard PHP module provides mcrypt library support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-mysql",
                                             description="A module for PHP applications that use MySQL databases",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-odbc",
                                             description="A module for PHP applications that use ODBC databases",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-pdo",
                                             description="A database access abstraction module for PHP applications",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-pear",
                                             description="PHP Extension and Application Repository framework",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-pgsql",
                                             description="A PostgreSQL database module for PHP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-process",
                                             description="Modules for PHP script using system process interfaces",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-pspell",
                                             description="A module for PHP applications for using pspell interfaces",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-recode",
                                             description="A module for PHP applications for using the recode library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-snmp",
                                             description="A module for PHP applications that query SNMP-managed devices",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-soap",
                                             description="A module for PHP applications that use the SOAP protocol",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-tidy",
                                             description="Standard PHP module provides tidy library support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-xml",
                                             description="A module for PHP applications which use XML",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-xmlrpc",
                                             description="A module for PHP applications which use the XML-RPC protocol",
                                             status=1)

            phpExtension.save()

            ## non-active packages


            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-debuginfo",
                                             description="Debug information for package lsphp55",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-mysql56-debuginfo",
                                             description="Debug information for package lsphp55-mysql56",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-lsphp53-devel",
                                             description="Files needed for building PHP extensions",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php54,
                                             extensionName="lsphp55-mysql56",
                                             description="PHP scripting language for creating dynamic web sites",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-mysqlnd",
                                             description="A module for PHP applications that use MySQL databases",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-opcache",
                                             description="The Zend OPcache",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-sqlite",
                                             description="Extension for the SQLite V2 Embeddable SQL Database Engine",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-xcache",
                                             description="PHP accelerator, optimizer, encoder and dynamic content cacher",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp55-xcache-admin",
                                             description="XCache Administration",
                                             status=0)

            phpExtension.save()

            ### ################ #################

            ##### Gather php 56 information

            ### ################ #################

            php56 = PHP.objects.get(phpVers="php56")

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-bcmath",
                                             description="A module for PHP applications for using the bcmath library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-common",
                                             description="Common files for PHP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-dba",
                                             description="A database abstraction layer module for PHP applications",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-enchant",
                                             description="Human Language and Character Encoding Support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-gd",
                                             description="A module for PHP applications for using the gd graphics library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-gmp",
                                             description="A module for PHP applications for using the GNU MP library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-imap",
                                             description="A module for PHP applications that use IMAP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-intl",
                                             description="Internationalization extension for PHP application",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-ioncube-loader",
                                             description="Ioncube Loader",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-ldap",
                                             description="A module for PHP applications that use LDAP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-mbstring",
                                             description="A module for PHP applications which need multi-byte string handling",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-mcrypt",
                                             description="Standard PHP module provides mcrypt library support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-mysql",
                                             description="A module for PHP applications that use MySQL databases",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-odbc",
                                             description="A module for PHP applications that use ODBC databases",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-pdo",
                                             description="A database access abstraction module for PHP applications",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php55,
                                             extensionName="lsphp56-pear",
                                             description="PHP Extension and Application Repository framework",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-pgsql",
                                             description="A PostgreSQL database module for PHP",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-process",
                                             description="Modules for PHP script using system process interfaces",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-pspell",
                                             description="A module for PHP applications for using pspell interfaces",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-recode",
                                             description="A module for PHP applications for using the recode library",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-snmp",
                                             description="A module for PHP applications that query SNMP-managed devices",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-soap",
                                             description="A module for PHP applications that use the SOAP protocol",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-tidy",
                                             description="Standard PHP module provides tidy library support",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-xml",
                                             description="A module for PHP applications which use XML",
                                             status=1)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-xmlrpc",
                                             description="A module for PHP applications which use the XML-RPC protocol",
                                             status=1)

            phpExtension.save()


            ## non-active packages


            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-debuginfo",
                                             description="Debug information for package lsphp56",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-mysql56-debuginfo",
                                             description="Debug information for package lsphp56-mysql56",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-devel",
                                             description="Files needed for building PHP extensions",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-mysql56",
                                             description="PHP scripting language for creating dynamic web sites",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-mysqlnd",
                                             description="A module for PHP applications that use MySQL databases",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-opcache",
                                             description="The Zend OPcache",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-sqlite",
                                             description="Extension for the SQLite V2 Embeddable SQL Database Engine",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-xcache",
                                             description="PHP accelerator, optimizer, encoder and dynamic content cacher",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-xcache-admin",
                                             description="XCache Administration",
                                             status=0)

            phpExtension.save()

            phpExtension = installedPackages(phpVers=php56,
                                             extensionName="lsphp56-pecl-imagick",
                                             description="Extension to create and modify images using ImageMagick",
                                             status=0)

            phpExtension.save()

            ### ################ #################

            ##### Gather php 70 information

            ### ################ #################

            phpVersion = PHP.objects.get(phpVers="php70")

            phpPath = ''

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                phpPath = os.path.join('/usr', 'local', 'CyberCP', 'managePHP', 'php70.xml')
            else:
                phpPath = os.path.join('/usr', 'local', 'CyberCP', 'managePHP', 'ubuntuphp70.xml')

            php = ElementTree.parse(phpPath)

            phpExtensions = php.findall('extension')

            for extension in phpExtensions:
                extensionName = extension.find('extensionName').text
                extensionDescription = extension.find('extensionDescription').text
                status = int(extension.find('status').text)

                phpExtension = installedPackages(phpVers=phpVersion,
                                                 extensionName=extensionName,
                                                 description=extensionDescription,
                                                 status=status)

                phpExtension.save()

            ### ################ #################

            ##### Gather php 71 information

            ### ################ #################

            phpVersion = PHP.objects.get(phpVers="php71")

            phpPath = ''

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                phpPath = os.path.join('/usr', 'local', 'CyberCP', 'managePHP', 'php71.xml')
            else:
                phpPath = os.path.join('/usr', 'local', 'CyberCP', 'managePHP', 'ubuntuphp71.xml')

            php = ElementTree.parse(phpPath)

            phpExtensions = php.findall('extension')

            for extension in phpExtensions:
                extensionName = extension.find('extensionName').text
                extensionDescription = extension.find('extensionDescription').text
                status = int(extension.find('status').text)

                phpExtension = installedPackages(phpVers=phpVersion,
                                                 extensionName=extensionName,
                                                 description=extensionDescription,
                                                 status=status)

                phpExtension.save()

        if PHP.objects.count() == 6:

            newPHP72 = PHP(phpVers="php72")
            newPHP72.save()

            php72Path = ''

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                php72Path = os.path.join('/usr', 'local', 'CyberCP', 'managePHP', 'php72.xml')
            else:
                php72Path = os.path.join('/usr', 'local', 'CyberCP', 'managePHP', 'ubuntuphp72.xml')

            php72 = ElementTree.parse(php72Path)

            php72Extensions = php72.findall('extension')

            for extension in php72Extensions:
                extensionName = extension.find('extensionName').text
                extensionDescription = extension.find('extensionDescription').text
                status = int(extension.find('status').text)

                phpExtension = installedPackages(phpVers=newPHP72,
                                                 extensionName=extensionName,
                                                 description=extensionDescription,
                                                 status=status)

                phpExtension.save()

        if PHP.objects.count() == 7:

            newPHP73 = PHP(phpVers="php73")
            newPHP73.save()

            php73Path = ''

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                php73Path = os.path.join('/usr', 'local', 'CyberCP', 'managePHP', 'php73.xml')
            else:
                php73Path = os.path.join('/usr', 'local', 'CyberCP', 'managePHP', 'ubuntuphp73.xml')

            php73 = ElementTree.parse(php73Path)

            php73Extensions = php73.findall('extension')

            for extension in php73Extensions:
                extensionName = extension.find('extensionName').text
                extensionDescription = extension.find('extensionDescription').text
                status = int(extension.find('status').text)

                phpExtension = installedPackages(phpVers=newPHP73,
                                                 extensionName=extensionName,
                                                 description=extensionDescription,
                                                 status=status)

                phpExtension.save()

        if PHP.objects.count() == 8:

            newPHP74 = PHP(phpVers="php74")
            newPHP74.save()

            php74Path = ''

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                php74Path = os.path.join('/usr', 'local', 'CyberCP', 'managePHP', 'php74.xml')
            else:
                php74Path = os.path.join('/usr', 'local', 'CyberCP', 'managePHP', 'ubuntuphp74.xml')

            php74 = ElementTree.parse(php74Path)

            php74Extensions = php74.findall('extension')

            for extension in php74Extensions:
                extensionName = extension.find('extensionName').text
                extensionDescription = extension.find('extensionDescription').text
                status = int(extension.find('status').text)

                phpExtension = installedPackages(phpVers=newPHP74,
                                                 extensionName=extensionName,
                                                 description=extensionDescription,
                                                 status=status)

                phpExtension.save()

        return render(request, 'managePHP/installExtensions.html', {'phps': PHPManager.findPHPVersions()})
    except KeyError:
        return redirect(loadLoginPage)


def getExtensionsInformation(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)

        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                phpVers = data['phpSelection']

                phpVers = "php" + PHPManager.getPHPString(phpVers)

                php = PHP.objects.get(phpVers=phpVers)

                records = php.installedpackages_set.all()

                json_data = "["
                checker = 0

                for items in records:

                    if items.status == 0:
                        status = "Not-Installed"
                    else:
                        status = "Installed"

                    dic = {'id': items.id,
                           'phpVers': items.phpVers.phpVers,
                           'extensionName': items.extensionName,
                           'description': items.description,
                           'status': status
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'fetchStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def submitExtensionRequest(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('extensionRequestStatus', 0)
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                extensionName = data['extensionName']
                type = data['type']

                if type == "install":
                    execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/phpUtilities.py"
                    execPath = execPath + " installPHPExtension --extension " + extensionName
                else:
                    execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/phpUtilities.py"
                    execPath = execPath + " unInstallPHPExtension --extension " + extensionName

                ProcessUtilities.popenExecutioner(execPath)

                final_json = json.dumps({'extensionRequestStatus': 1, 'error_message': "None"})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'extensionRequestStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'extensionRequestStatus': 0,
                     'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def getRequestStatus(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('extensionRequestStatus', 0)

        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                size = data['size']
                extensionName = data['extensionName']

                checkCommand = ''

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                    checkCommand = 'yum list installed'
                    checkCommand = shlex.split(checkCommand)
                else:
                    checkCommand = 'dpkg --list'
                    checkCommand = shlex.split(checkCommand)

                command = "sudo cat " + phpUtilities.installLogPath
                requestStatus = ProcessUtilities.outputExecutioner(command)

                if requestStatus.find('No such') > -1:
                    requestStatus = ""

                requestStatusSize = len(requestStatus)

                if requestStatus.find("PHP Extension Installed") > -1:

                    command = "sudo rm -f " + phpUtilities.installLogPath
                    ProcessUtilities.executioner(command)

                    if ProcessUtilities.outputExecutioner(checkCommand).find(extensionName) > -1:
                        ext = installedPackages.objects.get(extensionName=extensionName)
                        ext.status = 1
                        ext.save()
                    else:
                        ext = installedPackages.objects.get(extensionName=extensionName)
                        ext.status = 0
                        ext.save()

                    final_json = json.dumps({'finished': 1, 'extensionRequestStatus': 1,
                                             'error_message': "None",
                                             'requestStatus': requestStatus,
                                             'size': requestStatusSize})
                    return HttpResponse(final_json)
                elif requestStatus.find("Can not be installed") > -1:

                    command = "sudo rm -f " + phpUtilities.installLogPath
                    ProcessUtilities.executioner(command)

                    if ProcessUtilities.outputExecutioner(checkCommand).find(extensionName) > -1:
                        ext = installedPackages.objects.get(extensionName=extensionName)
                        ext.status = 1
                        ext.save()

                    else:
                        ext = installedPackages.objects.get(extensionName=extensionName)
                        ext.status = 0
                        ext.save()

                    final_json = json.dumps({'finished': 1, 'extensionRequestStatus': 1,
                                             'error_message': "None",
                                             'requestStatus': requestStatus,
                                             'size': requestStatusSize})
                    return HttpResponse(final_json)
                elif requestStatus.find("Can not un-install Extension") > -1:

                    command = "sudo rm -f " + phpUtilities.installLogPath
                    ProcessUtilities.executioner(command)

                    if ProcessUtilities.outputExecutioner(checkCommand).find(extensionName) > -1:
                        ext = installedPackages.objects.get(extensionName=extensionName)
                        ext.status = 1
                        ext.save()

                    else:
                        ext = installedPackages.objects.get(extensionName=extensionName)
                        ext.status = 0
                        ext.save()

                    final_json = json.dumps({'finished': 1, 'extensionRequestStatus': 1,
                                             'error_message': "None",
                                             'requestStatus': requestStatus,
                                             'size': requestStatusSize})
                    return HttpResponse(final_json)
                elif requestStatus.find("PHP Extension Removed") > -1:

                    command = "sudo rm -f " + phpUtilities.installLogPath
                    ProcessUtilities.executioner(command)

                    ext = installedPackages.objects.get(extensionName=extensionName)
                    ext.status = 0
                    ext.save()

                    final_json = json.dumps({'finished': 1, 'extensionRequestStatus': 1,
                                             'error_message': "None",
                                             'requestStatus': requestStatus,
                                             'size': requestStatusSize})
                    return HttpResponse(final_json)
                else:
                    final_json = json.dumps({'finished': 0, 'extensionRequestStatus': 1,
                                             'error_message': "None",
                                             'requestStatus': requestStatus,
                                             'size': requestStatusSize})
                    return HttpResponse(final_json)



        except BaseException as msg:
            final_dic = {'extensionRequestStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'extensionRequestStatus': 0,
                     'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def getRequestStatusApache(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('extensionRequestStatus', 0)

        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                size = data['size']
                extensionName = data['extensionName']

                checkCommand = ''

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                    checkCommand = 'yum list installed'
                    checkCommand = shlex.split(checkCommand)
                else:
                    checkCommand = 'dpkg --list'
                    checkCommand = shlex.split(checkCommand)

                command = "sudo cat " + phpUtilities.installLogPath
                requestStatus = ProcessUtilities.outputExecutioner(command)

                requestStatusSize = len(requestStatus)

                if requestStatus.find("PHP Extension Installed") > -1:

                    command = "sudo rm -f " + phpUtilities.installLogPath
                    ProcessUtilities.executioner(command)

                    if ProcessUtilities.outputExecutioner(checkCommand).find(extensionName) > -1:
                        ext = installedPackagesApache.objects.get(extensionName=extensionName)
                        ext.status = 1
                        ext.save()
                    else:
                        ext = installedPackagesApache.objects.get(extensionName=extensionName)
                        ext.status = 0
                        ext.save()

                    final_json = json.dumps({'status': 1, 'finished': 1, 'extensionRequestStatus': 1,
                                             'error_message': "None",
                                             'requestStatus': requestStatus,
                                             'size': requestStatusSize})
                    return HttpResponse(final_json)
                elif requestStatus.find("Can not be installed") > -1:

                    command = "sudo rm -f " + phpUtilities.installLogPath
                    ProcessUtilities.executioner(command)

                    if ProcessUtilities.outputExecutioner(checkCommand).find(extensionName) > -1:
                        ext = installedPackagesApache.objects.get(extensionName=extensionName)
                        ext.status = 1
                        ext.save()

                    else:
                        ext = installedPackagesApache.objects.get(extensionName=extensionName)
                        ext.status = 0
                        ext.save()

                    final_json = json.dumps({'status': 1, 'finished': 1, 'extensionRequestStatus': 1,
                                             'error_message': "None",
                                             'requestStatus': requestStatus,
                                             'size': requestStatusSize})
                    return HttpResponse(final_json)
                elif requestStatus.find("Can not un-install Extension") > -1:

                    command = "sudo rm -f " + phpUtilities.installLogPath
                    ProcessUtilities.executioner(command)

                    if ProcessUtilities.outputExecutioner(checkCommand).find(extensionName) > -1:
                        ext = installedPackagesApache.objects.get(extensionName=extensionName)
                        ext.status = 1
                        ext.save()

                    else:
                        ext = installedPackages.objects.get(extensionName=extensionName)
                        ext.status = 0
                        ext.save()

                    final_json = json.dumps({'status': 1, 'finished': 1, 'extensionRequestStatus': 1,
                                             'error_message': "None",
                                             'requestStatus': requestStatus,
                                             'size': requestStatusSize})
                    return HttpResponse(final_json)
                elif requestStatus.find("PHP Extension Removed") > -1:

                    command = "sudo rm -f " + phpUtilities.installLogPath
                    ProcessUtilities.executioner(command)

                    ext = installedPackagesApache.objects.get(extensionName=extensionName)
                    ext.status = 0
                    ext.save()

                    final_json = json.dumps({'status': 1, 'finished': 1, 'extensionRequestStatus': 1,
                                             'error_message': "None",
                                             'requestStatus': requestStatus,
                                             'size': requestStatusSize})
                    return HttpResponse(final_json)
                else:
                    final_json = json.dumps({'status': 1, 'finished': 0, 'extensionRequestStatus': 1,
                                             'error_message': "None",
                                             'requestStatus': requestStatus,
                                             'size': requestStatusSize})
                    return HttpResponse(final_json)



        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [getRequestStatusApache]')
            final_dic = {'status': 0, 'extensionRequestStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError as msg:
        logging.writeToFile(str(msg) + ' [getRequestStatusApache]')
        final_dic = {'status': 0, 'extensionRequestStatus': 0,
                     'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def editPHPConfigs(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        return render(request, 'managePHP/editPHPConfig.html', {'phps': PHPManager.findPHPVersions()})
    except KeyError:
        return redirect(loadLoginPage)


def getCurrentPHPConfig(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                phpVers = data['phpSelection']

                phpVers = "php" + PHPManager.getPHPString(phpVers)

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                    path = "/usr/local/lsws/ls" + phpVers + "/etc/php.ini"
                else:
                    initial = phpVers[3]
                    final = phpVers[4]

                    completeName = str(initial) + '.' + str(final)
                    path = "/usr/local/lsws/ls" + phpVers + "/etc/php/" + completeName + "/litespeed/php.ini"

                allow_url_fopen = "0"
                display_errors = "0"
                file_uploads = "0"
                allow_url_include = "0"
                memory_limit = ""
                max_execution_time = ""
                upload_max_filesize = ""
                max_input_time = ""

                command = "sudo cat " + path
                data = ProcessUtilities.outputExecutioner(command).split('\n')

                for items in data:
                    if items.find("allow_url_fopen") > -1 and items.find("=") > -1:
                        if items.find("On") > -1:
                            allow_url_fopen = "1"
                    if items.find("display_errors") > -1 and items.find("=") > -1:
                        if items.find("On") > -1:
                            display_errors = "1"
                    if items.find("file_uploads") > -1 and items.find("=") > -1:
                        if items.find("On") > -1:
                            file_uploads = "1"
                    if items.find("allow_url_include") > -1 and items.find("=") > -1:
                        if items.find("On") > -1:
                            allow_url_include = "1"
                    if items.find("memory_limit") > -1 and items.find("=") > -1:
                        memory_limit = re.findall(r"[A-Za-z0-9_]+", items)[1]
                    if items.find("max_execution_time") > -1 and items.find("=") > -1:
                        max_execution_time = re.findall(r"[A-Za-z0-9_]+", items)[1]
                    if items.find("upload_max_filesize") > -1 and items.find("=") > -1:
                        upload_max_filesize = re.findall(r"[A-Za-z0-9_]+", items)[1]
                    if items.find("max_input_time") > -1 and items.find("=") > -1:
                        max_input_time = re.findall(r"[A-Za-z0-9_]+", items)[1]
                    if items.find("post_max_size") > -1 and items.find("=") > -1:
                        post_max_size = re.findall(r"[A-Za-z0-9_]+", items)[1]

                final_dic = {'fetchStatus': 1,
                             'allow_url_fopen': allow_url_fopen,
                             'display_errors': display_errors,
                             'file_uploads': file_uploads,
                             'allow_url_include': allow_url_include,
                             'memory_limit': memory_limit,
                             'max_execution_time': max_execution_time,
                             'upload_max_filesize': upload_max_filesize,
                             'max_input_time': max_input_time,
                             'post_max_size': post_max_size}

                final_json = json.dumps(final_dic)

                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)

        return render(request, 'managePHP/editPHPConfig.html')
    except KeyError:
        return redirect(loadLoginPage)


def savePHPConfigBasic(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('saveStatus', 0)
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                phpVers = data['phpSelection']
                allow_url_fopen = data['allow_url_fopen']
                display_errors = data['display_errors']
                file_uploads = data['file_uploads']
                allow_url_include = data['allow_url_include']
                memory_limit = data['memory_limit']
                max_execution_time = data['max_execution_time']
                upload_max_filesize = data['upload_max_filesize']
                max_input_time = data['max_input_time']
                post_max_size = data['post_max_size']

                if allow_url_fopen == True:
                    allow_url_fopen = "allow_url_fopen = On"
                else:
                    allow_url_fopen = "allow_url_fopen = Off"

                if display_errors == True:
                    display_errors = "display_errors = On"
                else:
                    display_errors = "display_errors = Off"

                if file_uploads == True:
                    file_uploads = "file_uploads = On"
                else:
                    file_uploads = "file_uploads = Off"

                if allow_url_include == True:
                    allow_url_include = "allow_url_include = On"
                else:
                    allow_url_include = "allow_url_include = Off"

                phpVers = "php" + PHPManager.getPHPString(phpVers)

                ##

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/phpUtilities.py"
                execPath = execPath + " savePHPConfigBasic --phpVers " + phpVers + " --allow_url_fopen '" + allow_url_fopen + "' --display_errors '" + display_errors + "' --file_uploads '" + file_uploads + "' --allow_url_include '" + allow_url_include + "' --memory_limit " + memory_limit + " --max_execution_time " + max_execution_time + " --upload_max_filesize " + upload_max_filesize + " --max_input_time " + max_input_time + " --post_max_size " + post_max_size

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'saveStatus': 1}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)
                else:
                    final_dic = {'saveStatus': 0, 'error_message': output}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'saveStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        return redirect(loadLoginPage)


#### Get Advance PHP Configs

def getCurrentAdvancedPHPConfig(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                phpVers = data['phpSelection']

                phpVers = "php" + PHPManager.getPHPString(phpVers)

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                    path = "/usr/local/lsws/ls" + phpVers + "/etc/php.ini"
                else:
                    initial = phpVers[3]
                    final = phpVers[4]

                    completeName = str(initial) + '.' + str(final)
                    path = "/usr/local/lsws/ls" + phpVers + "/etc/php/" + completeName + "/litespeed/php.ini"

                command = "sudo cat " + path
                configData = ProcessUtilities.outputExecutioner(command)

                status = {"fetchStatus": 1, "configData": configData}
                final_json = json.dumps(status)
                return HttpResponse(final_json)


        except BaseException as msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        return redirect(loadLoginPage)


def savePHPConfigAdvance(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('saveStatus', 0)

        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                phpVers = data['phpSelection']

                phpVers = "php" + PHPManager.getPHPString(phpVers)

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                    path = "/usr/local/lsws/ls" + phpVers + "/etc/php.ini"
                else:
                    initial = phpVers[3]
                    final = phpVers[4]

                    completeName = str(initial) + '.' + str(final)
                    path = "/usr/local/lsws/ls" + phpVers + "/etc/php/" + completeName + "/litespeed/php.ini"

                tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

                vhost = open(tempPath, "w")
                vhost.write(data['configData'])
                vhost.close()

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/phpUtilities.py"
                execPath = execPath + " savePHPConfigAdvance --phpVers " + path + " --tempPath " + tempPath

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    status = {"saveStatus": 1, "configData": data['configData']}
                    final_json = json.dumps(status)
                    return HttpResponse(final_json)
                else:
                    data_ret = {'saveStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

            except BaseException as msg:
                data_ret = {'saveStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except KeyError as msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[saveConfigsToFile]")
        return HttpResponse("Not Logged in as admin")
