import requests
import json
import pexpect
from CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import time
from backupUtilities import backupUtilities
import signal

def verifyHostKey(IPAddress):
        try:
            backupUtilities.host_key_verification(IPAddress)

            password = "hello"

            expectation = []

            expectation.append("continue connecting (yes/no)?")
            expectation.append("password:")

            setupSSHKeys = pexpect.spawn("ssh root@" + IPAddress)

            index = setupSSHKeys.expect(expectation)

            if index == 0:
                setupSSHKeys.sendline("yes")

                setupSSHKeys.expect("password:")
                setupSSHKeys.sendline(password)

                expectation = []

                expectation.append("password:")
                expectation.append(pexpect.EOF)


                innerIndex = setupSSHKeys.expect(expectation)

                if innerIndex == 0:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]
                elif innerIndex == 1:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]

            elif index == 1:

                setupSSHKeys.expect("password:")
                setupSSHKeys.sendline(password)

                expectation = []

                expectation.append("password:")
                expectation.append(pexpect.EOF)

                innerIndex = setupSSHKeys.expect(expectation)

                if innerIndex == 0:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]
                elif innerIndex == 1:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]


        except pexpect.TIMEOUT, msg:
            logging.writeToFile("Timeout [verifyHostKey]")
            return [0,"Timeout [verifyHostKey]"]
        except pexpect.EOF, msg:
            logging.writeToFile("EOF [verifyHostKey]")
            return [0,"EOF [verifyHostKey]"]
        except BaseException, msg:
            logging.writeToFile(str(msg) + " [verifyHostKey]")
            return [0,str(msg)+" [verifyHostKey]"]



print verifyHostKey("23.95.216.56")