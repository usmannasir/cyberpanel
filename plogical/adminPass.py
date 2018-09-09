import argparse
import requests
import json
from random import randint

def main():

    parser = argparse.ArgumentParser(description='Reset admin user password!')
    parser.add_argument('--password', help='New Password')

    pathToFile = "/home/cyberpanel/"+str(randint(1000, 9999))
    file = open(pathToFile,"w")
    file.close()

    args = parser.parse_args()

    finalData = json.dumps({'password': args.password,'randomFile': pathToFile})
    r = requests.post("http://localhost:5003/api/changeAdminPassword", data=finalData,
                      verify=False)

    data = json.loads(r.text)

    if data['changed'] == 1:
        print("Admin password successfully changed!")
    else:
        print(data['error_message'])

if __name__ == "__main__":
    main()