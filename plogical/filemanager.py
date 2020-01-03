from plogical import CyberCPLogFileWriter as logging
import argparse
from random import randint

class filemanager:

    @staticmethod
    def createTemporaryFile(domainName):
        try:

            path = "/home/" + domainName + "/..filemanagerkey"

            fileKey = str(randint(1000, 9999))

            filemanager = open(path,'w')
            filemanager.write(fileKey)
            filemanager.close()

            print(fileKey)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [createTemporaryFile]")
            print("0," + str(msg))


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Filemanager')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--domainName', help='Domain name!')


    args = parser.parse_args()

    if args.function == "createTemporaryFile":
        filemanager.createTemporaryFile(args.domainName)

if __name__ == "__main__":
    main()