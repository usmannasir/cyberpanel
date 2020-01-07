#!/usr/local/CyberCP/bin/python
import getpass

def main():
    if getpass.getuser() == 'root':
        userType = "admin"
    else:
        userType = "user"

    data = """{
    "userName": "%s",
    "userType": "%s",
    "lang": "en",
    "assetsUri": "/usr/local/lvemanager",
    "baseUri": "/usr/local/lvemanager",
    "defaultDomain": "cyberpanel.net"
}""" % (getpass.getuser(), userType)

    print(data)

if __name__ == '__main__':
    main()