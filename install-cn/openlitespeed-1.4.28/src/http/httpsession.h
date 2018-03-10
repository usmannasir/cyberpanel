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
#ifndef HTTPCONNECTION_H
#define HTTPCONNECTION_H

#include <ls.h>
#include <edio/aioeventhandler.h>
#include <edio/aiooutputstream.h>
#include <http/httpreq.h>
#include <http/httpresp.h>
#include <http/ntwkiolink.h>
#include <http/sendfileinfo.h>
#include <lsiapi/internal.h>
#include <lsiapi/lsimoduledata.h>

class ReqHandler;
class VHostMap;
class ChunkInputStream;
class ChunkOutputStream;
class ExtWorker;
class VMemBuf;
class GzipBuf;
class SSIScript;
class LsiApiHooks;
class Aiosfcb;
class ReqParser;
class CallbackLinkedObj;

enum  HttpSessionState
{
    HSS_FREE,
    HSS_WAITING,
    HSS_READING,
    HSS_READING_BODY,
    HSS_EXT_AUTH,
    HSS_THROTTLING,
    HSS_PROCESSING,
    HSS_REDIRECT,
    HSS_EXT_REDIRECT,
    HSS_HTTP_ERROR,
    HSS_WRITING,
    HSS_AIO_PENDING,
    HSS_AIO_COMPLETE,
    HSS_COMPLETE,
    HSS_RECYCLING,
};

enum HSPState
{
    HSPS_READ_REQ_HEADER,
    HSPS_NEW_REQ,
    HSPS_MATCH_VHOST,
    HSPS_HKPT_HTTP_BEGIN,
    HSPS_HKPT_RCVD_REQ_HEADER,
    HSPS_PROCESS_NEW_REQ_BODY,
    HSPS_READ_REQ_BODY,
    HSPS_HKPT_RCVD_REQ_BODY,
    HSPS_PROCESS_NEW_URI,
    HSPS_VHOST_REWRITE,
    HSPS_CONTEXT_MAP,
    HSPS_CONTEXT_REWRITE,
    HSPS_HKPT_URI_MAP,
    HSPS_FILE_MAP,
    HSPS_CONTEXT_AUTH,
    HSPS_AUTHORIZER,
    HSPS_HKPT_HTTP_AUTH,
    HSPS_AUTH_DONE,
    HSPS_BEGIN_HANDLER_PROCESS,
    HSPS_HKPT_RCVD_REQ_BODY_PROCESSING,
    HSPS_HKPT_RCVD_RESP_HEADER,
    HSPS_RCVD_RESP_HEADER_DONE,
    HSPS_HKPT_RCVD_RESP_BODY,
    HSPS_RCVD_RESP_BODY_DONE,
    HSPS_HKPT_SEND_RESP_HEADER,
    HSPS_SEND_RESP_HEADER_DONE,
    HSPS_HKPT_HANDLER_RESTART,
    HSPS_HANDLER_RESTART_DONE,
    HSPS_HKPT_HTTP_END,
    HSPS_HTTP_END_DONE,
    HSPS_HANDLER_PROCESSING,
    HSPS_WEBSOCKET,
    HSPS_HTTP_ERROR

};

#define HSF_URI_PROCESSED           (1<<0)
#define HSF_HANDLER_DONE            (1<<1)
#define HSF_RESP_HEADER_SENT        (1<<2)
#define HSF_HANDLER_WRITE_SUSPENDED (1<<3)
#define HSF_RESP_FLUSHED            (1<<4)
#define HSF_REQ_BODY_DONE           (1<<5)
#define HSF_REQ_WAIT_FULL_BODY      (1<<6)
#define HSF_RESP_WAIT_FULL_BODY     (1<<7)
#define HSF_RESP_HEADER_DONE        (1<<8)
#define HSF_ACCESS_LOG_OFF          (1<<9)
#define HSF_HOOK_SESSION_STARTED    (1<<10)
#define HSF_RECV_RESP_BUFFERED      (1<<11)
#define HSF_SEND_RESP_BUFFERED      (1<<12)
#define HSF_CHUNK_CLOSED            (1<<13)
#define HSF_RESP_BODY_COMPRESSED    (1<<14)
#define HSF_SUSPENDED               (1<<15)
#define HSF_SC_404                  (1<<16)
#define HSF_AIO_READING             (1<<17)

#define HSF_STX_FILE_CACHE_READY    (1<<19)


class HttpSession : public LsiSession, public InputStream,
    public HioHandler,
    public AioEventHandler
{
    HttpReq               m_request;
    HttpResp              m_response;

    LsiModuleData         m_moduleData; //lsiapi user data of http level
    const lsi_reqhdlr_t  *m_pModHandler;

    HttpSessionHooks      m_sessionHooks;
    HSPState              m_processState;
    int                   m_suspendPasscode;
    int                   m_curHookLevel;

    ChunkInputStream     *m_pChunkIS;
    ChunkOutputStream    *m_pChunkOS;
    ReqHandler           *m_pHandler;

    lsi_hookinfo_t        m_curHookInfo;
    lsi_param_t           m_curHkptParam;
    int                   m_curHookRet;

    off_t                 m_lDynBodySent;

    VMemBuf              *m_pRespBodyBuf;
    GzipBuf              *m_pGzipBuf;
    ClientInfo           *m_pClientInfo;

    NtwkIOLink           *m_pNtwkIOLink;
    uint16_t              m_iRemotePort;

    SendFileInfo          m_sendFileInfo;

    long                  m_lReqTime;
    int32_t               m_iReqTimeUs;

    int32_t               m_iFlag;
    short                 m_iState;
    unsigned short        m_iReqServed;
    //int                   m_accessGranted;

    AioReq                m_aioReq;
    Aiosfcb              *m_pAiosfcb;

    uint32_t              m_sn;
    ReqParser            *m_pReqParser;

    AutoBuf               m_sExtCmdResBuf;
    evtcb_pf              m_cbExtCmd;
    long                  m_lExtCmdParam;
    void                 *m_pExtCmdParam;


    HttpSession(const HttpSession &rhs);
    void operator=(const HttpSession &rhs);

    void processPending(int ret);

    void parseHost(char *pHost);

    int  buildErrorResponse(const char *errMsg);

    void cleanUpHandler();
    void nextRequest();
    int  updateClientInfoFromProxyHeader(const char *pHeaderName,
                                         const char *pProxyHeader,
                                         int headerLen);

    static int readReqBodyTermination(LsiSession *pSession, char *pBuf,
                                      int size);

    static int stx_nextRequest(lsi_session_t *p, long , void *)
    {
        HttpSession *pSession = (HttpSession *)p;
        if (pSession)
            pSession->nextRequest();
        return 0;
    }

public:

    uint32_t getSn()    { return m_sn;}

    void runAllCallbacks();

    void closeConnection();
    void recycle();

    int isHookDisabled(int level) const
    {   return m_sessionHooks.isDisabled(level);  }

    int isRespHeaderSent() const
    {   return m_iFlag & HSF_RESP_HEADER_SENT;   }

    void setFlag(int f)       {   m_iFlag |= f;               }
    void setFlag(int f, int v)
    {   m_iFlag = (m_iFlag & ~f) | (v ? f : 0);               }
    void clearFlag(int f)     {   m_iFlag &= ~f;               }
    int32_t getFlag() const       {   return m_iFlag;             }
    int32_t getFlag(int mask)    {   return m_iFlag & mask;      }

    ReqParser  *getReqParser()  {   return m_pReqParser;    }


    AutoBuf &getExtCmdBuf()   { return m_sExtCmdResBuf;    }

    void setExtCmdNotifier(evtcb_pf cb, const long lParam,
                           void *pParam)
    {
        m_cbExtCmd = cb;
        m_lExtCmdParam = lParam;
        m_pExtCmdParam = pParam;
    }

    void extCmdDone();

    int pushToClient(const char *pUri, int uriLen);
    void processLinkHeader(const char* pValue, int valLen);
    
    static int hookResumeCallback(lsi_session_t *session, long lParam, void *);


private:
    int checkAuthorizer(const HttpHandler *pHandler);
    int assignHandler(const HttpHandler *pHandler);
    int readReqBody();
    int reqBodyDone();
    int processURI(const char *pURI);
    int readToHeaderBuf();
    void sendHttpError(const char *pAdditional);
    int sendDefaultErrorPage(const char *pAdditional);
    int detectTimeout();

    //int cacheWrite( const char * pBuf, int size );
    //int writeRespBuf();

    void releaseChunkOS();
    void releaseRequestResource();

    void setupChunkIS();
    void releaseChunkIS();
    int  doWrite();
    int  doRead();
    int processURI(int resume);
    int checkAuthentication(const HTAuth *pHTAuth,
                            const AuthRequired *pRequired, int resume);

    void logAccess(int cancelled);
    int  detectKeepAliveTimeout(int delta);
    int  detectConnectionTimeout(int delta);
    void resumeSSI();
    int sendStaticFile(SendFileInfo *pData);
    int sendStaticFileEx(SendFileInfo *pData);
#ifdef LS_AIO_USE_AIO
    int aioRead(SendFileInfo *pData, void *pBuf = NULL);
    int sendStaticFileAio(SendFileInfo *pData);
#endif
    int writeRespBodyBlockInternal(SendFileInfo *pData, const char *pBuf,
                                   int written);
    int writeRespBodyBlockFilterInternal(SendFileInfo *pData, const char *pBuf,
                                         int written, lsi_param_t *param = NULL);
    int chunkSendfile(int fdSrc, off_t off, off_t size);
    int processWebSocketUpgrade(const HttpVHost *pVHost);
    int processHttp2Upgrade(const HttpVHost *pVHost);

    //int resumeHandlerProcess();
    int flushBody();
    int endResponseInternal(int success);

    int getModuleDenyCode(int iHookLevel);
    int processHkptResult(int iHookLevel, int ret);

    int processOneLink(const char* p, const char* pEnd);
    
    int restartHandlerProcess();
    int runFilter(int hookLevel, filter_term_fn pfTerm,
                  const char *pBuf,
                  int len, int flagIn);
    int contentEncodingFixup();
    int processVHostRewrite();
    int runEventHkpt(int hookLevel, HSPState nextState);
    int processNewReqInit();
    int processNewReqBody();
    int smProcessReq();
    int processContextMap();
    int processContextRewrite();
    int processContextAuth();
    int processAuthorizer();
    int processFileMap();
    int processNewUri();

    void resetEvtcb();
    void processServerPush();
 


public:
    int  flush();


public:
    NtwkIOLink *getNtwkIOLink() const      {   return m_pNtwkIOLink;   }
    //void setNtwkIOLink( NtwkIOLink * p )    {   m_pNtwkIOLink = p;      }
    //below are wrapper functions
    SslConnection *getSSL() const   {   return m_request.getSsl();          }
    int16_t isSSL() const           {   return m_request.isHttps(); }

    const char *getPeerAddrString() const;
    int getPeerAddrStrLen() const;
    const struct sockaddr *getPeerAddr() const;

    void suspendRead()          {    getStream()->suspendRead();        };
    void continueRead()         {    getStream()->continueRead();       };
    void suspendWrite()         {    getStream()->suspendWrite();       };
    void continueWrite()        {    getStream()->continueWrite();      };
    void switchWriteToRead()    {    getStream()->switchWriteToRead();  };

    void suspendEventNotify()   {    getStream()->suspendEventNotify(); };
    void resumeEventNotify()    {    getStream()->resumeEventNotify();  };

    off_t getBytesRecv() const  {   return getStream()->getBytesRecv();    }
    off_t getBytesSent() const  {   return getStream()->getBytesSent();    }

    void setClientInfo(ClientInfo *p)   {   m_pClientInfo = p;      }
    ClientInfo *getClientInfo() const   {   return m_pClientInfo;  }

    HttpSessionState getState() const       {   return (HttpSessionState)m_iState;    }
    void setState(HttpSessionState state) {   m_iState = (short)state;   }
    int getServerAddrStr(char *pBuf, int len);
    int isAlive();
    int setUpdateStaticFileCache(const char *pPath, int pathLen,
                                 int fd, struct stat &st);

    int isEndResponse() const   { return (m_iFlag & HSF_HANDLER_DONE);     }

    int resumeProcess(int resumeState, int retcode);

public:
    void setupChunkOS(int nobuffer);

    HttpSession();
    ~HttpSession();


    unsigned short getRemotePort() const
    {   return m_iRemotePort;   };

    void setVHostMap(const VHostMap *pMap)
    {
        m_iReqServed = 0;
        m_request.setVHostMap(pMap);
    }

    HttpReq *getReq()
    {   return &m_request;  }
//     HttpResp* getResp()
//     {   return &m_response; }

    long getReqTime() const {   return m_lReqTime;  }
    int32_t getReqTimeUs() const    {   return m_iReqTimeUs;    }

    int writeRespBodyDirect(const char *pBuf, int size);
    int writeRespBody(const char *pBuf, int len);

    int isNoRespBody() const
    {   return m_request.noRespBody();  }


    int onReadEx();
    int onWriteEx();
    int onInitConnected();
    int onCloseEx();

    int redirect(const char *pNewURL, int len, int alloc = 0);
    int getHandler(const char *pURI, ReqHandler *&pHandler);
    //int setLocation( const char * pLoc );

    //int startForward( int fd, int type );
    bool endOfReqBody();
    void setWaitFullReqBody()
    {    setFlag(HSF_REQ_WAIT_FULL_BODY);    }

    int parseReqArgs(int doPostBody, int uploadPassByPath,
                     const char *uploadTmpDir, int uploadTmpFilePermission);

    int  onTimerEx();

    //void accessGranted()    {   m_accessGranted = 1;  }
    void changeHandler() {    setState(HSS_REDIRECT); };

    //const char * buildLogId();

    void httpError(int code, const char *pAdditional = NULL);
    int read(char *pBuf, int size);
    int readv(struct iovec *vector, size_t count);
    ReqHandler *getCurHandler() const  {   return m_pHandler;  }


    //void resumeAuthentication();
    void authorized();

    void addEnv(const char *pKey, int keyLen, const char *pValue, long valLen);

    off_t writeRespBodySendFile(int fdFile, off_t offset, off_t size);
    int setupRespCache();
    void releaseRespCache();
    int sendDynBody();
    int setupGzipFilter();
    int setupGzipBuf();
    void releaseGzipBuf();
    int appendDynBody(const char *pBuf, int len);
    int appendDynBodyEx(const char *pBuf, int len);

    int appendRespBodyBuf(const char *pBuf, int len);
    int appendRespBodyBufV(const iovec *vector, int count);

    int shouldSuspendReadingResp();
    void resetRespBodyBuf();
    int checkRespSize(int nobuffer);

    int respHeaderDone();

    void setRespBodyDone()
    {
        m_iFlag |= HSF_HANDLER_DONE;
        if (m_pChunkOS)
        {
            setFlag(HSF_RESP_FLUSHED, 0);
            flush();
        }
    }

    int endResponse(int success);
    int setupDynRespBodyBuf();
    GzipBuf *getGzipBuf() const    {   return m_pGzipBuf;  }
    VMemBuf *getRespCache() const  {   return m_pRespBodyBuf; }
    off_t getDynBodySent() const    {   return m_lDynBodySent; }
    //int flushDynBody( int nobuff );
    int execExtCmd(const char *pCmd, int len, int mode = EXEC_EXT_CMD);
    int handlerProcess(const HttpHandler *pHandler);
    int getParsedScript(SSIScript *&pScript);
    int startServerParsed();
    HttpResp *getResp()
    {   return &m_response; }
    int flushDynBodyChunk();
    //int writeConnStatus( char * pBuf, int bufLen );

    void resetResp()
    {   getResp()->reset(); }

    LogSession *getLogSession()    {   return getStream();     }

    SendFileInfo *getSendFileInfo() {   return &m_sendFileInfo;   }

    int openStaticFile(const char *pPath, int pathLen, int *status);

    int detectContentLenMismatch(int buffered);

    /**
     * @brief initSendFileInfo() should be called before start sending a static file
     *
     * @param pPath[in] an file path to a static file
     * @param pathLen[in] the lenght of the path
     * @return 0 if successful, HTTP status code in SC_xxx predefined macro.
     *
     **/
    int initSendFileInfo(const char *pPath, int pathLen);

    /**
     * @brief setSendFileOffset() set the start point and length of the file to be send
     *
     * @param start[in] file offset from which will start reading data  from
     * @param size[in]  the number of bytes to be sent
     *
     **/

    void setSendFileOffsetSize(off_t start, off_t size);

    void setSendFileOffsetSize(int fd, off_t start, off_t size);


    int finalizeHeader(int ver, int code);
    LsiModuleData *getModuleData()      {   return &m_moduleData;   }

    HttpSessionHooks *getSessionHooks() { return &m_sessionHooks;   }

    void setSendFileBeginEnd(off_t start, off_t end);
    void prepareHeaders();
    int sendRespHeaders();
    void addLocationHeader();

    void setAccessLogOff()      {   m_iFlag |= HSF_ACCESS_LOG_OFF;  }
    int shouldLogAccess() const
    {   return !(m_iFlag & HSF_ACCESS_LOG_OFF);    }

    int updateContentCompressible();
    int handoff(char **pData, int *pDataLen);
    int suspendProcess();

    virtual int onAioEvent();
    int handleAioSFEvent(Aiosfcb *event);

    void setModHandler(const lsi_reqhdlr_t *pHandler)
    {   m_pModHandler = pHandler;   }

    const lsi_reqhdlr_t *getModHandler()
    {   return m_pModHandler;}
    
    void setBackRefPtr(evtcbhead_t ** v);
    void resetBackRefPtr();
    void cancelEvent(evtcbnode_s * v);

};

#endif
