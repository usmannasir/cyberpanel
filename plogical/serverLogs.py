from plogical import CyberCPLogFileWriter as logging
import argparse

class serverLogs:

    @staticmethod
    def cleanLogFile(fileName):
        try:
            logFile = open(fileName,'w')
            logFile.close()
            print("1,None")
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[cleanLogFile]")

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')

    parser.add_argument('--fileName', help='File to clean.')

    args = parser.parse_args()

    if args.function == "cleanLogFile":
        serverLogs.cleanLogFile(args.fileName)

if __name__ == "__main__":
    main()