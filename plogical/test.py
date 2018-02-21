from xml.etree import ElementTree
import os
from random import randint

try:
    mydoc = ElementTree.parse('domain.xml')


    len = 0

    if len == 0:
        raise BaseException("Error occurred!")

    domains = mydoc.findall('ChildDomains/domain')

    for d in domains:
        print d.find('domain').text
        print d.find('phpSelection').text
        print d.find('path').text

    databases = mydoc.findall('Databases/database')

    for d in databases:
        print d.find('dbName').text
        print d.find('dbUser').text
        print d.find('password').text

    dnsrecords = mydoc.findall('dnsrecords/dnsrecord')

    for dnsrecord in dnsrecords:
        print dnsrecord.find('type').text
        print dnsrecord.find('name').text
        print dnsrecord.find('content').text
        print dnsrecord.find('priority').text

    print os.path.join("/home", "cyberpanel", str(randint(1000, 9999)) + ".xml/", "test")
except BaseException,msg:
    print str(msg)
