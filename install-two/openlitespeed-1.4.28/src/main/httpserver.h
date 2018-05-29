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
#ifndef HTTPSERVER_H
#define HTTPSERVER_H


#include <config.h>
#include <http/httplogsource.h>
#include <util/tsingleton.h>

#include <inttypes.h>

#define DEFAULT_SWAP_DIR    DEFAULT_TMP_DIR "/swap/"

#define ADMIN_USERDB                "_AdminUserDB"

extern const char *sStatDir;


class HttpVHost;
class HttpServerImpl;
class HttpListener;
class GSockAddr;
class AutoStr2;
class HttpContext;
class HttpSession;
class LogFile;
class AccessControl;
class FcgiApp;
class ExtWorker;
class StringList;
class ScriptHandlerMap;
class SslContext;
class HttpConfigLoader;
class VHostMap;
class XmlNode;
class ConfigCtx;

class HttpServer : public TSingleton<HttpServer>, public HttpLogSource
{
    friend class TSingleton<HttpServer>;

    HttpServerImpl     *m_impl;

    HttpServer(const HttpServer &rhs);
    void operator=(const HttpServer &rhs);
    HttpServer();
public:

    ~HttpServer();

    int start();
    int shutdown();
    HttpListener *addListener(const char *pName, const char *pAddr);
    int removeListener(const char *pName);
    HttpListener *getListener(const char *pName) const ;

    int addVHost(HttpVHost *pVHost);
    int updateVHost(const char *pName, HttpVHost *pVHost);
    int removeVHost(const char *pName);
    HttpVHost *getVHost(const char *pName) const;
    void checkSuspendedVHostList(HttpVHost *pVHost);


//     int mapListenerToVHost( HttpListener * pListener,
//                             const char * pKey,
//                             const char * pVHostName );
    int mapListenerToVHost(const char *pListenerName,
                           const char *pKey,
                           const char *pVHostName);
    int mapListenerToVHost(HttpListener *pListener,
                           HttpVHost    *pVHost,
                           const char *pDomains);
    int removeVHostFromListener(const char *pListenerName,
                                const char *pVHostName);
    int allocatePidTracker();

    AccessControl *getAccessCtrl() const;
    int  getVHostCounts() const;
    HttpVHost *getVHost(int index) const;


    void beginConfig();
    void endConfig(int error);
    void onTimer();
    void onVHostTimer();
    int  enableVHost(const char *pVHostName, int enable);
    int  isServerOk();
    void offsetChroot();
    void setProcNo(int proc);
    void setBlackBoard(char *pBuf);
    void passListeners();
    void recoverListeners();

    int  initMultiplexer(const char *pType);
    int  reinitMultiplexer();
    int  initAdns();
    int  initAioSendFile();
    int  initLscpd();

    void setSwapDir(const char *pDir);
    const char *getSwapDir();
    int setupSwap();


    const AutoStr2 *getErrDocUrl(int statusCode) const;
    void releaseAll();
    virtual void setLogLevel(const char *pLevel);
    virtual int setAccessLogFile(const char *pFileName, int pipe);
    virtual int setErrorLogFile(const char *pFileName);
    virtual void setErrorLogRollingSize(off_t size, int keep_days);
    virtual AccessLog *getAccessLog() const;
    void enableAioLogging();
    const StringList *getIndexFileList() const;
    int  test_main(const char *pArgv0);
    void generateStatusReport();
    int  authAdminReq(char *pAuth);
    HttpContext &getServerContext();
    static void cleanPid();
    int configServerBasics(int reconfig, const XmlNode *pRoot);
    int configServer(int reconfig, XmlNode *pRoot);
    int changeUserChroot();
//    void reconfigVHost( char *pVHostName, XmlNode* pRoot );
    void setServerRoot(const char *pRoot);
    int initServer(XmlNode *pRoot, int &iReleaseXmlTree, int reconfig = 0);


};

extern int removeMatchFile(const char *pDir, const char *prefix);

#endif
