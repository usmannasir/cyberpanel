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
#ifndef HTTPIOLINK_H
#define HTTPIOLINK_H



#include <edio/eventreactor.h>
#include <http/clientinfo.h>
#include <http/hiostream.h>

#include <sslpp/sslconnection.h>
#include <util/dlinkqueue.h>
#include <log4cxx/logsession.h>
#include <util/iovec.h>

#include <sys/types.h>
#include <lsiapi/internal.h>
#include <lsiapi/lsimoduledata.h>
#include <lsiapi/lsiapihooks.h>

class Aiosfcb;
class HttpListener;
class VHostMap;
class SslContext;
struct sockaddr;

typedef int (*writev_fp)(LsiSession *pThis, const struct iovec *vector,
                         int count);
typedef int (*read_fp)(LsiSession *pThis, char *pBuf, int size);


class NtwkIOLink : public LsiSession, public EventReactor, public HioStream
{
private:
    typedef int (*onRW_fp)(NtwkIOLink *pThis);
    typedef void (*onTimer_fp)(NtwkIOLink *pThis);
    typedef int (*close_fp)(NtwkIOLink *pThis);
    class fp_list
    {
    public:
        read_fp         m_read_fp;
        writev_fp       m_writev_fp;
        onRW_fp         m_onWrite_fp;
        onRW_fp         m_onRead_fp;
        close_fp        m_close_fp;
        onTimer_fp      m_onTimer_fp;

        fp_list(read_fp rfn, writev_fp wvfn, onRW_fp onwfn, onRW_fp onrfn,
                close_fp cfn, onTimer_fp otfn)
            : m_read_fp(rfn)
            , m_writev_fp(wvfn)
            , m_onWrite_fp(onwfn)
            , m_onRead_fp(onrfn)
            , m_close_fp(cfn)
            , m_onTimer_fp(otfn)
        {}
    };

    class fp_list_list
    {
    public:
        fp_list        *m_pNoSSL;
        fp_list        *m_pSSL;

        fp_list_list(fp_list *lplain, fp_list *lssl)
            : m_pNoSSL(lplain)
            , m_pSSL(lssl)
        {}
    };

    static class fp_list        s_normal;
    static class fp_list        s_normalSSL;
    static class fp_list        s_throttle;
    static class fp_list        s_throttleSSL;

    static class fp_list_list   s_fp_list_list_normal;
    static class fp_list_list   s_fp_list_list_throttle;

    static class fp_list_list  *s_pCur_fp_list_list;

    static int                  s_iPrevTmToken;
    static int                  s_iTmToken;



    LsiModuleData       m_moduleData;

    ClientInfo         *m_pClientInfo;
    const VHostMap     *m_pVHostMap;
    unsigned short      m_iRemotePort;

    char                m_iInProcess;
    char                m_iPeerShutdown;
    int                 m_tmToken;
    int                 m_iSslLastWrite;
    int                 m_iHeaderToSend;
    SslConnection       m_ssl;

    class fp_list      *m_pFpList;
    IolinkSessionHooks  m_sessionHooks;

    short               m_hasBufferedData;
    IOVec               m_iov;
    DLinkQueue          m_aioSFQ;



public:
    short               hasBufferedData()   {   return m_hasBufferedData; }

private:
    NtwkIOLink(const NtwkIOLink &rhs);
    void operator=(const NtwkIOLink &rhs);

    int doRead()
    {
        if (isWantRead())
            return getHandler()->onReadEx();
        else
            suspendRead();
        return 0;
    }

    int doReadT()
    {
        if (isWantRead())
        {
            if (allowRead())
                return getHandler()->onReadEx();
            else
            {
                suspendRead();
                setFlag(HIO_FLAG_WANT_READ, 1);
            }
        }
        else
            suspendRead();
        return 0;
    }

    int doWrite()
    {
        if (isWantWrite())
            if (getHandler())
                return getHandler()->onWriteEx();
            else
                return 0;
        else
        {
            suspendWrite();
            if (isSSL() || m_hasBufferedData)
                flush();
        }
        return 0;
    }

    int checkWriteRet(int len);
    int checkReadRet(int ret, int size);
    void setSSLAgain();

    static int writevEx(LsiSession *pThis, const iovec *vector, int count);
    static int writevExT(LsiSession *pThis, const iovec *vector, int count);
    static int writevExSSL(LsiSession *pThis, const iovec *vector, int count);
    static int writevExSSL_T(LsiSession *pThis, const iovec *vector,
                             int count);

    static int readEx(LsiSession *pThis, char *pBuf, int size);
    static int readExT(LsiSession *pThis, char *pBuf, int size);
    static int readExSSL(LsiSession *pThis, char *pBuf, int size);
    static int readExSSL_T(LsiSession *pThis, char *pBuf, int size);

    static int onReadSSL(NtwkIOLink *pThis);
    static int onReadSSL_T(NtwkIOLink *pThis);
    static int onReadT(NtwkIOLink *pThis);
    static int onRead(NtwkIOLink *pThis);

    static int onWriteSSL(NtwkIOLink *pThis);
    static int onWriteSSL_T(NtwkIOLink *pThis);
    static int onWriteT(NtwkIOLink *pThis);
    static int onWrite(NtwkIOLink *pThis);

    static int close_(NtwkIOLink *pThis);
    static int closeSSL(NtwkIOLink *pThis);
    static void onTimer_T(NtwkIOLink *pThis);
    static void onTimer_(NtwkIOLink *pThis);
    static void onTimerSSL_T(NtwkIOLink *pThis);

    void drainReadBuf();

    bool allowWrite() const
    {   return m_pClientInfo->allowWrite();  }


    void updateSSLEvent();
    void checkSSLReadRet(int ret);
    void flushSslWpending();

    int setupHandler(HiosProtocol verSpdy);
    int sslSetupHandler();

    void dumpState(const char *pFuncName, const char *action);

    off_t sendfileSetUp(off_t size);
    int sendfileFinish(int written);

public:

    static void setPrevToken(int val)
    {
        s_iPrevTmToken = val;
    }
    static int getPrevToken()
    {   return s_iPrevTmToken;    }

    static void setToken(int val)
    {
        s_iTmToken = val;
    }
    static int getToken()
    {   return s_iTmToken;        }

    void setRemotePort(unsigned short port)
    {
        m_iRemotePort = port;
        clearLogId();
    };

    unsigned short getRemotePort() const  {   return m_iRemotePort;       };

    int sendRespHeaders(HttpRespHeaders *pHeaders, int isNoBody);

    const char *buildLogId();
    LogSession *getLogSession()        {   return this;        }

    class fp_list      *getFnList() { return m_pFpList; }

public:
    void closeSocket();
    bool allowRead() const
    {   return m_pClientInfo->allowRead();   }
    int close();
    int  shutdown();
    int  detectClose();
    int  detectCloseNow();

public:


    NtwkIOLink();
    ~NtwkIOLink();

    char inProcess() const    {   return m_iInProcess;    }

    int read(char *pBuf, int size);

    // Output stream interfaces
    bool canHold(int size)    {   return allowWrite();        }

    int write(const char *pBuf, int size);
    int writev_internal(const struct iovec *vector, int len, int flush_flag);
    int writev(const struct iovec *vector, int len);

    int sendfile(int fdSrc, off_t off, off_t size);

    int addAioSFJob(Aiosfcb *cb);
    int aiosendfiledone(Aiosfcb *cb);
    virtual int aiosendfile(Aiosfcb *cb);

    int flush();

    void setNoSSL()
    {
        m_pFpList = s_pCur_fp_list_list->m_pNoSSL;
    }

    // SSL interface
    void setSSL(SSL *pSSL)
    {
        m_pFpList = s_pCur_fp_list_list->m_pSSL;
        m_ssl.setSSL(pSSL);
        m_ssl.setfd(getfd());
    }

    SslConnection *getSSL()     {   return &m_ssl;  }
    bool isSSL() const          {   return m_ssl.getSSL() != NULL;  }

    int shutdownSsl();

    int SSLAgain();
    int acceptSSL();
    void handle_acceptSSL_EIO_Err();

    int get_url_from_reqheader(char *buf, int length, char **puri,
                               int *uri_len, char **phost, int *host_len);

    int switchToHttp2Handler(HioHandler *pSession);

    int setLink(HttpListener *pListener, int fd, ClientInfo *pInfo,
                SslContext  *pSslContext);

    const char *getPeerAddrString() const
    {   return m_pClientInfo->getAddrString();   }
    int getPeerAddrStrLen() const
    {   return m_pClientInfo->getAddrStrLen();   }

    const struct sockaddr *getPeerAddr() const
    {   return m_pClientInfo->getAddr();   }

    void changeClientInfo(ClientInfo *pInfo);


    //Event driven IO interface
    int handleEvents(short event);

    void setNotWantRead()   {   setFlag(HIO_FLAG_WANT_READ, 0);  }
    void suspendRead();
    void continueRead();
    void suspendWrite();
    void continueWrite();
    void switchWriteToRead();
    uint16_t getEvents() const
    {   return EventReactor::getEvents();  }

    void checkThrottle();
    //void setThrottleLimit( int limit )
    //{   m_baseIO.getThrottleCtrl().setLimit( limit );    }

    void onTimer();
    int isFromLocalAddr() const;

    //void stopThrottleTimer();
    //void startThrottleTimer();

    ClientInfo *getClientInfo() const
    {   return m_pClientInfo;               }
    ThrottleControl *getThrottleCtrl() const
    {   return  &(m_pClientInfo->getThrottleCtrl());  }
    static void enableThrottle(int enable);
    int isThrottle() const
    {   return m_pFpList->m_onTimer_fp != onTimer_; }

    void suspendEventNotify();
    void resumeEventNotify();

    void tryRead();

    void setVHostMap(const VHostMap *pMap) {   m_pVHostMap = pMap;     }
    const VHostMap *getVHostMap() const    {   return m_pVHostMap;     }

    LsiModuleData *getModuleData()      {   return &m_moduleData;   }

    IolinkSessionHooks  *getSessionHooks() {  return &m_sessionHooks;    }

    virtual NtwkIOLink *getNtwkIoLink()    {   return this;    }
};


#endif
