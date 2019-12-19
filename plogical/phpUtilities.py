import sys
sys.path.append('/usr/local/CyberCP')
from plogical import CyberCPLogFileWriter as logging
import subprocess
import shlex
import _thread
from plogical import installUtilities
import argparse
import os
from plogical.mailUtilities import mailUtilities
from plogical.processUtilities import ProcessUtilities

class phpUtilities:

    installLogPath = "/home/cyberpanel/phpExtensionRequestLog"

    @staticmethod
    def installPHPExtension(extension,extensions):
        try:

            mailUtilities.checkHome()

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                command = 'sudo yum install ' + extension + ' -y'
            else:
                command = 'sudo apt-get install ' + extension + ' -y'

            cmd = shlex.split(command)

            try:
                with open(phpUtilities.installLogPath, 'w') as f:
                    subprocess.call(cmd, stdout=f)

                writeToFile = open(phpUtilities.installLogPath, 'a')
                writeToFile.writelines("PHP Extension Installed.\n")
                writeToFile.close()

                installUtilities.installUtilities.reStartLiteSpeed()

                return 1
            except:
                writeToFile = open(phpUtilities.installLogPath, 'a')
                writeToFile.writelines("Can not be installed.\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile("[Could not Install]")
                installUtilities.installUtilities.reStartLiteSpeed()
                return 0
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installPHPExtension]")

    @staticmethod
    def unInstallPHPExtension(extension,extensions):
        try:

            mailUtilities.checkHome()

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                command = 'sudo rpm --nodeps -e  ' + extension + ' -v'
            else:
                command = 'sudo apt-get remove -y  ' + extension

            cmd = shlex.split(command)

            try:

                with open(phpUtilities.installLogPath, 'w') as f:
                    subprocess.call(cmd, stdout=f)

                writeToFile = open(phpUtilities.installLogPath, 'a')
                writeToFile.writelines("PHP Extension Removed.\n")
                writeToFile.close()
                installUtilities.installUtilities.reStartLiteSpeed()
                return 1
            except:
                writeToFile = open(phpUtilities.installLogPath, 'a')
                writeToFile.writelines("Can not un-install Extension.\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile("[Could not Install]")
                installUtilities.installUtilities.reStartLiteSpeed()
                return 0

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[unInstallPHPExtension]")

    @staticmethod
    def initiateInstall(extension):
        try:
            _thread.start_new_thread(phpUtilities.installPHPExtension, (extension, extension))
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateInstall]")

    @staticmethod
    def initiateRemoval(extension):
        try:
            _thread.start_new_thread(phpUtilities.unInstallPHPExtension, (extension, extension))
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateRestore]")

    @staticmethod
    def savePHPConfigBasic(phpVers,allow_url_fopen,display_errors,file_uploads,allow_url_include,memory_limit,max_execution_time,upload_max_filesize,max_input_time,post_max_size):
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                path = "/usr/local/lsws/ls" + phpVers + "/etc/php.ini"
            else:
                initial = phpVers[3]
                final = phpVers[4]

                completeName = str(initial) + '.' + str(final)
                path = "/usr/local/lsws/ls" + phpVers + "/etc/php/" + completeName + "/litespeed/php.ini"

            logging.CyberCPLogFileWriter.writeToFile(path)

            data = open(path, 'r').readlines()

            writeToFile = open(path, 'w')

            for items in data:
                if items.find("allow_url_fopen") > -1 and items.find("=") > -1:
                    writeToFile.writelines(allow_url_fopen + "\n")
                elif items.find("display_errors") > -1 and items.find("=") > -1:
                    writeToFile.writelines(display_errors + "\n")
                elif items.find("file_uploads") > -1 and items.find("=") > -1 and not items.find(
                        "max_file_uploads") > -1:
                    writeToFile.writelines(file_uploads + "\n")
                elif items.find("allow_url_include") > -1 and items.find("=") > -1:
                    writeToFile.writelines(allow_url_include + "\n")

                elif items.find("memory_limit") > -1 and items.find("=") > -1:
                    writeToFile.writelines("memory_limit = " + memory_limit + "\n")

                elif items.find("max_execution_time") > -1 and items.find("=") > -1:
                    writeToFile.writelines("max_execution_time = " + max_execution_time + "\n")

                elif items.find("upload_max_filesize") > -1 and items.find("=") > -1:
                    writeToFile.writelines("upload_max_filesize = " + upload_max_filesize + "\n")

                elif items.find("max_input_time") > -1 and items.find("=") > -1:
                    writeToFile.writelines("max_input_time = " + max_input_time + "\n")
                elif items.find("post_max_size") > -1 and items.find("=") > -1:
                    writeToFile.writelines("post_max_size = " + post_max_size + "\n")
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

            installUtilities.installUtilities.reStartLiteSpeed()

            print("1,None")

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [savePHPConfigBasic]")
            print("0,"+str(msg))

    @staticmethod
    def savePHPConfigAdvance(phpVers,tempPath):
        try:
            phpINI = open(phpVers, 'w')
            phpINI.write(open(tempPath, "r").read())
            phpINI.close()
            installUtilities.installUtilities.reStartLiteSpeed()

            if os.path.exists(tempPath):
                os.remove(tempPath)

            print("1,None")
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [savePHPConfigAdvance]")
            print("0,"+str(msg))



def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--phpVers', help='Domain name!')
    parser.add_argument('--allow_url_fopen', help='Max Connections for PHP!')
    parser.add_argument('--display_errors', help='Initial Request Timeout (secs) for PHP!')
    parser.add_argument("--file_uploads", help="Persistent Connection for PHP!")
    parser.add_argument("--allow_url_include", help="Memory Soft Limit (bytes) for PHP!")
    parser.add_argument("--memory_limit", help="Process Hard Limit for PHP!")
    parser.add_argument("--max_execution_time", help="Memory Hard Limit (bytes) for PHP!")
    parser.add_argument("--upload_max_filesize", help="Process Soft Limit for PHP!")
    parser.add_argument("--max_input_time", help="Process Hard Limit for PHP!")
    parser.add_argument("--post_max_size", help="Process Hard Limit for PHP!")
    parser.add_argument("--extension", help="Process Hard Limit for PHP!")

    ## Litespeed Tuning Arguments

    parser.add_argument("--tempPath", help="Temporary path to file where PHP is storing data!")


    args = parser.parse_args()

    if args.function == "savePHPConfigBasic":
        phpUtilities.savePHPConfigBasic(args.phpVers, args.allow_url_fopen, args.display_errors, args.file_uploads, args.allow_url_include, args.memory_limit,
                                        args.max_execution_time, args.upload_max_filesize, args.max_input_time, args.post_max_size)
    elif args.function == "savePHPConfigAdvance":
        phpUtilities.savePHPConfigAdvance(args.phpVers, args.tempPath)

    elif args.function == "installPHPExtension":
        phpUtilities.installPHPExtension(args.extension, args.extension)

    elif args.function == "unInstallPHPExtension":
        phpUtilities.unInstallPHPExtension(args.extension, args.extension)




if __name__ == "__main__":
    main()