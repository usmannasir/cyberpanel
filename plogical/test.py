from xml.etree import ElementTree
import os
from random import randint

try:
    mydoc = ElementTree.parse('domain.xml')

    len = 1

    if len==1:
        raise BaseException

    print mydoc.find('masterDomain').text

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

    print os.path.join("/home", "cyberpanel", str(randint(1000, 9999)) + ".xml/", "test")
except BaseException,msg:
    print "hello"
