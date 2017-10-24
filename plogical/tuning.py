import CyberCPLogFileWriter as logging
from installUtilities import installUtilities

class tuning:


    @staticmethod
    def fetchTuningDetails():

        try:
            datas = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
            dataToReturn = {}



            for items in datas:
                if items.find("maxConnections")>-1:
                    data = items.split()
                    dataToReturn['maxConnections'] = data[1]

                if items.find("maxSSLConnections") > -1:
                    data = items.split()
                    dataToReturn['maxSSLConnections'] = data[1]

                if items.find("connTimeout") > -1:
                    data = items.split()
                    dataToReturn['connTimeout'] = data[1]


                if items.find("maxConnections")>-1:
                    data = items.split()
                    dataToReturn['maxConnections'] = data[1]

                if items.find("keepAliveTimeout") > -1:
                    data = items.split()
                    dataToReturn['keepAliveTimeout'] = data[1]


                if items.find("totalInMemCacheSize") > -1:
                    data = items.split()
                    dataToReturn['totalInMemCacheSize'] = data[1]

                if items.find("enableGzipCompress") > -1:
                    data = items.split()
                    dataToReturn['enableGzipCompress'] = data[1]

            return dataToReturn

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [fetchTuningDetails]")
            return 0


    @staticmethod
    def saveTuningDetails(maxConnections,maxSSLConnections,connectionTimeOut,keepAliveTimeOut,cacheSizeInMemory,gzipCompression):

        try:
            datas = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
            writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf","w")


            for items in datas:
                if items.find("maxConnections") > -1:
                    data = "  maxConnections          "+str(maxConnections)+"\n"
                    writeDataToFile.writelines(data)
                    continue

                elif items.find("maxSSLConnections") > -1:
                    data = "  maxSSLConnections       "+str(maxSSLConnections) + "\n"
                    writeDataToFile.writelines(data)
                    continue

                elif items.find("connTimeout") > -1:
                    data ="  connTimeout             "+str(connectionTimeOut)+"\n"
                    writeDataToFile.writelines(data)
                    continue

                elif items.find("keepAliveTimeout") > -1:
                    data = "  keepAliveTimeout        " + str(keepAliveTimeOut) + "\n"
                    writeDataToFile.writelines(data)
                    continue

                elif items.find("totalInMemCacheSize") > -1:
                    data = "  totalInMemCacheSize     " + str(cacheSizeInMemory) + "\n"
                    writeDataToFile.writelines(data)
                    continue

                elif items.find("enableGzipCompress") > -1:
                    data = "  enableGzipCompress      " + str(gzipCompression) + "\n"
                    writeDataToFile.writelines(data)
                    continue
                else:
                    writeDataToFile.writelines(items)
            writeDataToFile.close()

            return 1

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [saveTuningDetails]")
            return 0




    @staticmethod
    def fetchPHPDetails(phpVersion):
        try:
            path = installUtilities.Server_root_path + "/conf/phpconfigs/php"+str(phpVersion)+".conf"
            datas = open(path).readlines()
            dataToReturn = {}

            for items in datas:
                if items.find("maxConns")>-1:
                    data = items.split()
                    dataToReturn['maxConns'] = data[1]

                if items.find("initTimeout") > -1:
                    data = items.split()
                    dataToReturn['initTimeout'] = data[1]

                if items.find("persistConn") > -1:
                    data = items.split()
                    dataToReturn['persistConn'] = data[1]


                if items.find("memSoftLimit")>-1:
                    data = items.split()
                    dataToReturn['memSoftLimit'] = data[1]

                if items.find("memHardLimit") > -1:
                    data = items.split()
                    dataToReturn['memHardLimit'] = data[1]


                if items.find("procSoftLimit") > -1:
                    data = items.split()
                    dataToReturn['procSoftLimit'] = data[1]

                if items.find("procHardLimit") > -1:
                    data = items.split()
                    dataToReturn['procHardLimit'] = data[1]

            return dataToReturn

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [fetchPHPDetails]")
            return 0

    @staticmethod
    def tunePHP(phpVersion,maxConns,initTimeout,persistConn,memSoftLimit,memHardLimit,procSoftLimit,procHardLimit):


        try:
            path = installUtilities.Server_root_path + "/conf/phpconfigs/php" + str(phpVersion) + ".conf"
            datas = open(path).readlines()

            writeDataToFile = open(path,"w")


            for items in datas:
                if items.find("maxConns") > -1:
                    data = "  maxConns                "+str(maxConns)+"\n"
                    writeDataToFile.writelines(data)
                    continue

                elif items.find("initTimeout") > -1:
                    data = "  initTimeout             "+str(initTimeout) + "\n"
                    writeDataToFile.writelines(data)
                    continue

                elif items.find("memSoftLimit") > -1:
                    data ="  memSoftLimit            "+str(memSoftLimit)+"\n"
                    writeDataToFile.writelines(data)
                    continue

                elif items.find("memHardLimit") > -1:
                    data = "  memHardLimit            " + str(memHardLimit) + "\n"
                    writeDataToFile.writelines(data)
                    continue

                elif items.find("procSoftLimit") > -1:
                    data = "  procSoftLimit           " + str(procSoftLimit) + "\n"
                    writeDataToFile.writelines(data)
                    continue

                elif items.find("procHardLimit") > -1:
                    data = "  procHardLimit           " + str(procHardLimit) + "\n"
                    writeDataToFile.writelines(data)
                    continue
                elif items.find("persistConn") > -1:
                    if persistConn == "Enable":
                        persist = 1
                    else:
                        persist = 0


                    data = "  persistConn             " + str(persist) + "\n"
                    writeDataToFile.writelines(data)
                    continue
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            return 1

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [saveTuningDetails]")
            return 0

