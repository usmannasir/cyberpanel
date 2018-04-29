import CyberCPLogFileWriter as logging
import os
import subprocess
import shutil
import platform

system=platform.dist()[0]
version=float(platform.dist()[1])

class DNS:

    nsd_base = "/etc/nsd/nsd.conf"
    zones_base_dir = "/usr/local/lsws/conf/zones/"
    create_zone_dir = "/usr/local/lsws/conf/zones"

    @staticmethod
    def createNameServer(virtualHostName, firstNS, firstNSIP, secondNS, secondNSIP):
        try:

            if not os.path.exists(DNS.zones_base_dir):
                os.mkdir(DNS.create_zone_dir)

            zonePath = DNS.zones_base_dir + virtualHostName
            zoneFilePath = zonePath + "/zone.conf"



            data = open(DNS.nsd_base, "r").readlines()

            if DNS.checkIfZoneExists(virtualHostName, data) == 1:

                os.mkdir(zonePath)
                zoneFileToWrite = open(zoneFilePath, "w")

                if DNS.addEntryInMainZone(virtualHostName, data) == 1:
                    if DNS.perVirtualHostZoneFile(virtualHostName, zoneFileToWrite) == 1:
                        if DNS.addNSRecord(firstNS, firstNSIP, secondNS, secondNSIP, zoneFileToWrite) == 1:
                            DNS.restartNSD()
                            zoneFileToWrite.close()
                            return 1
                        else:
                            zoneFileToWrite.close()
                            return 0
                    else:
                        zoneFileToWrite.close()
                        return 0
                else:
                    zoneFileToWrite.close()
                    return 0


            else:
                if not os.path.exists(zonePath):
                    os.mkdir(zonePath)
                    zoneFileToWrite = open(zoneFilePath, "w")


                    if DNS.perVirtualHostZoneFile(virtualHostName, zoneFileToWrite) == 1:
                        if DNS.addNSRecord(firstNS, firstNSIP, secondNS, secondNSIP, zoneFileToWrite) == 1:
                            DNS.restartNSD()
                            zoneFileToWrite.close()
                            return 1
                        else:
                            zoneFileToWrite.close()
                            return 0
                    else:
                        zoneFileToWrite.close()
                        return 0

                else:

                    zoneFileToWrite = open(zoneFilePath, "a")
                    if DNS.addNSRecord(firstNS, firstNSIP, secondNS, secondNSIP, zoneFileToWrite) == 1:
                        DNS.restartNSD()
                        zoneFileToWrite.close()
                        return 1
                    else:
                        zoneFileToWrite.close()
                        return 0

                zoneFileToWrite.close()
                logging.CyberCPLogFileWriter.writeToFile(
                    "Zone file for virtualhost already exists. " + "[createNameServer]")
                return 1

        except IOError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addEntryInMainZone]")
            return 0

    @staticmethod
    def checkIfZoneExists(virtualHostName,data):
        for items in data:
            if items.find(virtualHostName) > -1:
                return 0
        return 1


    @staticmethod
    def addEntryInMainZone(virtualHostName,data):

        # Defining zone to be added
        zone = "zone:" + "\n"
        zoneName = "    name: " + virtualHostName + "\n"
        zoneFile = "    zonefile: "+virtualHostName+"/zone.conf" + "\n"


        try:
            mainZoneFile = open(DNS.nsd_base,"w")
            zoneCheck = 1
            noZones = 1

            for items in data:
                if items.find("zone:")>-1 and zoneCheck==1:
                    mainZoneFile.writelines(zone)
                    mainZoneFile.writelines(zoneName)
                    mainZoneFile.writelines(zoneFile)
                    mainZoneFile.writelines("\n")
                    mainZoneFile.writelines(items)
                    noZones = 0
                    zoneCheck = 0
                else:
                    mainZoneFile.writelines(items)

            if noZones ==1:
                mainZoneFile.writelines(zone)
                mainZoneFile.writelines(zoneName)
                mainZoneFile.writelines(zoneFile)
                mainZoneFile.writelines("\n")

            mainZoneFile.close()
            return 1
        except IOError,msg:
            mainZoneFile.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addEntryInMainZone]")
            return 0

    @staticmethod
    def perVirtualHostZoneFile(virtualHostName, zoneFileToWrite):

        # Make zone directory

        origin = "$ORIGIN " + virtualHostName + "." + "\n"
        ttl = "$TTL 86400" + "\n"

        try:
            zoneFileToWrite.writelines(origin)
            zoneFileToWrite.writelines(ttl)
            zoneFileToWrite.writelines("\n")

            # Create SOA Record

            DNS.createSOARecord(virtualHostName, zoneFileToWrite)

            return 1


        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [perVirtualHostZoneFile]")
            return 0

    @staticmethod
    def createSOARecord(virtualHostName,fileHandle):

        # Define SOA Record

        soa = "@ IN SOA ns1 admin@"+virtualHostName+" (" + "\n"
        serialNumber = "	2012082703" + "\n"
        refreshRate = "	28800" + "\n"
        retryRate = "	1400" + "\n"
        expiry = "	864000" + "\n"
        minTTL = "	86400" + "\n"
        endSOA = "	)" + "\n"


        try:
            fileHandle.writelines("\n")

            fileHandle.writelines(soa)
            fileHandle.writelines(serialNumber)
            fileHandle.writelines(refreshRate)
            fileHandle.writelines(retryRate)
            fileHandle.writelines(expiry)
            fileHandle.writelines(minTTL)
            fileHandle.writelines(endSOA)


            fileHandle.writelines("\n")


            return 1
        except IOError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createSOARecord]")
            return 0



    @staticmethod
    def addNSRecord(nsRecordOne,firstNSIP, nsRecordTwo, secondNSIP, fileHandle):
        # Defining NS Record

        NSARecordOne = nsRecordOne.split(".")[0]
        NSARecordTwo = nsRecordTwo.split(".")[0]

        NS1 = "\t\t" + "NS" + "\t" + nsRecordOne + "." "\n"
        NS2 = "\t\t" + "NS" + "\t" + nsRecordTwo + "."

        try:
            fileHandle.writelines("\n")
            fileHandle.writelines("\n")

            fileHandle.writelines(NS1)
            fileHandle.writelines(NS2)

            DNS.addRecord(NSARecordOne, "A", firstNSIP, fileHandle)
            DNS.addRecord(NSARecordTwo, "A", secondNSIP, fileHandle)

            fileHandle.writelines("\n")
            return 1
        except IOError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addRecord]")
            return 0


    @staticmethod
    def addRecord(recordValue, recordType, recordIP, fileHandle):

        # Define Record

        recordString = recordValue +"\t" + "IN" + "\t" + recordType + "\t" + recordIP

        try:
            fileHandle.writelines("\n")
            fileHandle.writelines(recordString)
            fileHandle.writelines("\n")
            return 1
        except IOError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addRecord]")
            return 0


    @staticmethod
    def restartNSD():

        try:

            ############## Restart NSD ######################
            if version >= 7:
                cmd.append("systemctl")
                cmd.append("restart")
                cmd.append("nsd")
            elif version >= 6:
                cmd.append("service")
                cmd.append("nsd")
                cmd.append("restart")
            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("           Could restart NSD                   ")
                print("###############################################")
                logging.CyberCPLogFileWriter.writeToFile("[Failed to restart NSD]")
                return 0
            else:
                print("###############################################")
                print("              NSD Restarted                    ")
                print("###############################################")
                return 1


        except OSError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [restartNSD]")
            return 0

    @staticmethod
    def deleteZone(virtualHostname):
        try:
            if os.path.exists(DNS.zones_base_dir+virtualHostname):
                shutil.rmtree(DNS.zones_base_dir+virtualHostname)

            data = open(DNS.nsd_base, "r").readlines()

            writeDataToFile = open(DNS.nsd_base,"w")

            index = 0

            for items in data:
                if items.find(virtualHostname) >-1:
                    try:
                        del data[index-1]
                        del data[index-1]
                        del data[index-1]
                    except:
                        break
                    break
                index = index+1

            for items in data:
                writeDataToFile.writelines(items)

            writeDataToFile.close()



        except OSError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [deleteZone]")

    @staticmethod
    def addARecord(virtualHostName,recordValue,recordIP):
        try:

            if not os.path.exists(DNS.zones_base_dir):
                os.mkdir(DNS.create_zone_dir)

            data = open(DNS.nsd_base, "r").readlines()

            zonePath = DNS.zones_base_dir + virtualHostName
            zoneFilePath = zonePath + "/zone.conf"

            if DNS.checkIfZoneExists(virtualHostName,data) == 1:

                DNS.addEntryInMainZone(virtualHostName,data)

                os.mkdir(zonePath)
                zoneFileToWrite = open(zoneFilePath, "w")

                DNS.perVirtualHostZoneFile(virtualHostName, zoneFileToWrite)
                DNS.addRecord(recordValue,"A",recordIP,zoneFileToWrite)


            else:

                if not os.path.exists(zonePath):
                    os.mkdir(zonePath)
                    zoneFileToWrite = open(zoneFilePath, "w")


                    if DNS.perVirtualHostZoneFile(virtualHostName, zoneFileToWrite) == 1:
                        if DNS.addRecord(recordValue,"A",recordIP,zoneFileToWrite) == 1:
                            DNS.restartNSD()
                            zoneFileToWrite.close()
                            return 1
                        else:
                            zoneFileToWrite.close()
                            return 0
                    else:
                        zoneFileToWrite.close()
                        return 0

                else:

                    zoneFileToWrite = open(zoneFilePath, "a")
                    if DNS.addRecord(recordValue,"A",recordIP,zoneFileToWrite) == 1:
                        DNS.restartNSD()
                        zoneFileToWrite.close()
                        return 1
                    else:
                        zoneFileToWrite.close()
                        return 0

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [addARecord]')


    @staticmethod
    def deleteRecord(recordValue, recordType, recordIP, virtualHostName):

        try:
            zonePath = DNS.zones_base_dir + virtualHostName
            zoneFilePath = zonePath + "/zone.conf"

            data = open(zoneFilePath, "r").readlines()

            writeDataToFile = open(zoneFilePath, "w")

            for items in data:
                if items.find(recordIP) > -1 and items.find(recordValue) > -1 and items.find(recordType)>-1:
                    continue
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            return 1
        except IOError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addRecord]")
            return 0