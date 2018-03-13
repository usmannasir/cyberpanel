/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2015  LiteSpeed Technologies, Inc.                 *
*                                                                            *
*    This program is free software: you can redistribute it and/or modify    *
*    it under the terms of the GNU General Public License as published by    *
*    the Free Software Foundation, either version 3 of the License, or       *
*    (at your option) any later version.                                     *
*                                                                            *
*    This program is distributed in the hope that it will be useful,         *
*    but WITHOUT ANY WARRANTY; without even the implied warranty of          *
*    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the            *
*    GNU General Public License for more details.                            *
*                                                                            *
*    You should have received a copy of the GNU General Public License       *
*    along with this program. If not, see http://www.gnu.org/licenses/.      *
*****************************************************************************/
#include "httplogsource.h"
#include <http/accesslog.h>
#include <http/httplog.h>
#include <http/stderrlogger.h>
#include <log4cxx/appender.h>
#include <log4cxx/logger.h>
//#include <log4cxx/appendermanager.h>
//#include <log4cxx/level.h>
#include <main/configctx.h>
#include <util/autostr.h>
#include <util/xmlnode.h>
#include <util/gpath.h>
//#include <unistd.h>
#include <limits.h>
#include <stdlib.h>


AutoStr  HttpLogSource::s_sDefaultAccessLogFormat;
short HttpLogSource::s_iAioServerAccessLog = -1;
short HttpLogSource::s_iAioServerErrorLog = -1;
int HttpLogSource::initAccessLog(const XmlNode *pRoot,
                                 int setDebugLevel)
{
    ConfigCtx currentCtx("accesslog");
    //const XmlNode *p0 = pRoot->getChild( "logging", 1 );
    const XmlNode *pNode1 = pRoot->getChild("accessLog");

    if (pNode1 == NULL)
    {
        if (setDebugLevel)
        {
            currentCtx.logErrorMissingTag("accessLog");
            return LS_FAIL;
        }
    }
    else
    {
        off_t rollingSize = 1024 * 1024 * 1024;
        int useServer = ConfigCtx::getCurConfigCtx()->getLongValue(pNode1,
                        "useServer", 0, 2, 2);
        enableAccessLog(useServer != 2);

        if (setDebugLevel)
        {
            const char *pFmt = pNode1->getChildValue("logFormat");

            if (pFmt)
                s_sDefaultAccessLogFormat.setStr(pFmt);
        }

        if (setDebugLevel || useServer == 0)
        {
            if (initAccessLog(pNode1, &rollingSize) != 0)
            {
                LS_ERROR(&currentCtx, "failed to set up access log!");
                return LS_FAIL;
            }
        }

        const char *pByteLog = pNode1->getChildValue("bytesLog");

        if (pByteLog)
        {
            char buf[MAX_PATH_LEN];

            if (ConfigCtx::getCurConfigCtx()->getAbsoluteFile(buf, pByteLog) != 0)
            {
                currentCtx.logErrorPath("log file",  pByteLog);
                return LS_FAIL;
            }

            if (GPath::isWritable(buf) == false)
            {
                LS_ERROR(&currentCtx, "log file is not writable - %s", buf);
                return LS_FAIL;
            }

            setBytesLogFilePath(buf, rollingSize);
        }
    }

    return 0;
}


int HttpLogSource::initAccessLog(const XmlNode *pNode,
                                 off_t *pRollingSize)
{
    char buf[MAX_PATH_LEN];
    int ret = -1;
    const char *pPipeLogger = pNode->getChildValue("pipedLogger");

    if (pPipeLogger)
        ret = setAccessLogFile(pPipeLogger, 1);

    if (ret == -1)
    {
        ret = ConfigCtx::getCurConfigCtx()->getLogFilePath(buf, pNode);

        if (ret)
            return ret;

        ret = setAccessLogFile(buf, 0);
    }

    if (ret == 0)
    {
        AccessLog *pLog = getAccessLog();
        const char *pValue = pNode->getChildValue("keepDays");

        if (pValue)
            pLog->getAppender()->setKeepDays(atoi(pValue));

        pLog->setLogHeaders(ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                            "logHeaders", 0, 7, 3));

        const char *pFmt = pNode->getChildValue("logFormat");

        if (!pFmt)
            pFmt = s_sDefaultAccessLogFormat.c_str();

        if (pFmt)
            if (pLog->setCustomLog(pFmt) == -1)
                LS_ERROR(ConfigCtx::getCurConfigCtx(),
                         "failed to setup custom log format [%s]",
                         pFmt);

        pValue = pNode->getChildValue("logReferer");

        if (pValue)
            pLog->accessLogReferer(atoi(pValue));

        pValue = pNode->getChildValue("logUserAgent");

        if (pValue)
            pLog->accessLogAgent(atoi(pValue));

        pValue = pNode->getChildValue("rollingSize");

        if (pValue)
        {
            off_t size = getLongValue(pValue);

            if ((size > 0) && (size < 1024 * 1024))
                size = 1024 * 1024;

            if (pRollingSize)
                *pRollingSize = size;

            pLog->getAppender()->setRollingSize(size);
        }

        m_iAioAccessLog = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                          "enableaiolog", 0, 1, -1);

        pLog->getAppender()->setCompress(
            ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "compressArchive", 0, 1,
                    0));
    }

    return ret;
}

int HttpLogSource::initAllLog(const char *pRoot)
{
    char achBuf[256], achBuf1[256];
    char *p = achBuf;
    strcpy(p, pRoot);
    char *pEnd = p + strlen(p);
    strcpy(achBuf1, achBuf);
    
    strcpy(pEnd, "/logs/error.log");
    setErrorLogFile(achBuf);
    setLogLevel("DEBUG");
    off_t rollSize = 1024 * 10240;
    setErrorLogRollingSize(rollSize, 30);
    HttpLog::setDebugLevel(0);
    
    strcpy(pEnd, "/logs/stderr.log");
    StdErrLogger::getInstance().setLogFileName(achBuf);
    StdErrLogger::getInstance().getAppender()->setRollingSize(rollSize);
    
    strcpy(pEnd, "/logs/access.log");
    HttpLog::setAccessLogFile(achBuf, 0);
    enableAccessLog(1);
    
    AccessLog *pLog = getAccessLog();
    pLog->getAppender()->setKeepDays(30);
    pLog->setLogHeaders(3);
    pLog->setCustomLog(s_sDefaultAccessLogFormat.c_str());
    pLog->accessLogReferer(0);
    pLog->accessLogAgent(0);
    pLog->getAppender()->setRollingSize(rollSize);
    pLog->getAppender()->setCompress(0);
    
    return 0;
}


int HttpLogSource::initErrorLog2(const XmlNode *pNode,
                                 int setDebugLevel)
{
    char buf[MAX_PATH_LEN];
    int ret = ConfigCtx::getCurConfigCtx()->getLogFilePath(buf, pNode);

    if (ret)
        return ret;

    setErrorLogFile(buf);

    const char *pValue = ConfigCtx::getCurConfigCtx()->getTag(pNode,
                         "logLevel");

    if (pValue != NULL)
        setLogLevel(pValue);

    off_t rollSize =
        ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "rollingSize", 0,
                INT_MAX, 1024 * 10240);
    int days = ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "keepDays", 0,
               LLONG_MAX, 30);
    setErrorLogRollingSize(rollSize, days);

    m_iAioErrorLog = ConfigCtx::getCurConfigCtx()->getLongValue(pNode,
                     "enableaiolog", 0, 1, -1);

    if (setDebugLevel)
    {
        pValue = pNode->getChildValue("debugLevel");

        if (pValue != NULL)
            HttpLog::setDebugLevel(atoi(pValue));

        if (ConfigCtx::getCurConfigCtx()->getLongValue(pNode, "enableStderrLog", 0,
                1, 1))
        {
            char *p = strrchr(buf, '/');

            if (p)
            {
                strcpy(p + 1, "stderr.log");
                StdErrLogger::getInstance().setLogFileName(buf);
                StdErrLogger::getInstance().getAppender()->
                setRollingSize(rollSize);
            }
        }
        else
            StdErrLogger::getInstance().setLogFileName(NULL);
    }

    return 0;
}


int HttpLogSource::initErrorLog(const XmlNode *pRoot,
                                int setDebugLevel)
{
    ConfigCtx currentCtx("errorLog");
    const XmlNode *pNode1 = NULL;
    pNode1 = pRoot->getChild("errorLog");

    if (pNode1 == NULL)
    {
        if (setDebugLevel)
        {
            currentCtx.logErrorMissingTag("errorLog");
            return LS_FAIL;
        }
    }
    else
    {
        int useServer = ConfigCtx::getCurConfigCtx()->getLongValue(pNode1,
                        "useServer", 0, 1, 1);

        if (setDebugLevel || useServer == 0)
        {
            if (initErrorLog2(pNode1, setDebugLevel) != 0)
            {
                LS_ERROR(&currentCtx, "failed to set up error log!");
                return LS_FAIL;
            }
        }
    }

    return 0;
}

