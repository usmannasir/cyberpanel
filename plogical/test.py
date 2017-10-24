import requests
import json
def editWPFile():

    finalData = json.dumps({'adminUser': "admin",
                            'adminPass': "1234567",
                            'domainName': "usmannasir.me",
                            'ownerEmail': "admin",
                            'packageName': "Default",
                            'websiteOwner': "usman",
                            'ownerPassword': "9xvps",
                            })
    r = requests.post("http://147.135.165.44:8090/api/createWebsite", data=finalData)
    print r.text

def delwebsite():

    finalData = json.dumps({'adminUser': "admin",
                            'adminPass': "9njZ9Hw6QuJvw4AS6w",
                            })
    r = requests.post("https://cyberpanel.extravm.com:8090/api/verifyConn", data=finalData)
    print r.text


def getKey(ipAddress, password):
    return requests.get('https://api.ipify.org').text


print getKey("147.135.165.44","1234567")