/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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

//  Author: dxu@litespeedtech.com (David Shue)

#include "pagespeed.h"
#include <string.h>
#include <util/loopbuf.h>

#include "ls_caching_headers.h"
#include "ls_message_handler.h"
#include "ls_rewrite_driver_factory.h"
#include "ls_rewrite_options.h"
#include "ls_server_context.h"
#include "ls_uamatcher.h"
#include "ls_base_fetch.h"

#include <sys/uio.h>
#include <apr_poll.h>
#include <util/autostr.h>
#include <util/stringtool.h>
#include <util/autobuf.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "log_message_handler.h"
#include <signal.h>
#include "http/serverprocessconfig.h"

#include "net/instaweb/http/public/async_fetch.h"
#include "net/instaweb/http/public/cache_url_async_fetcher.h"
#include "net/instaweb/http/public/request_context.h"
#include "net/instaweb/public/global_constants.h"
#include "net/instaweb/rewriter/public/experiment_matcher.h"
#include "net/instaweb/rewriter/public/experiment_util.h"
#include "net/instaweb/rewriter/public/process_context.h"
#include "net/instaweb/rewriter/public/resource_fetch.h"
#include "net/instaweb/rewriter/public/rewrite_driver.h"
#include "net/instaweb/rewriter/public/rewrite_options.h"
#include "net/instaweb/rewriter/public/rewrite_query.h"
#include "net/instaweb/rewriter/public/rewrite_stats.h"
#include "net/instaweb/rewriter/public/static_asset_manager.h"
#include "net/instaweb/util/public/fallback_property_page.h"
#include "pagespeed/automatic/proxy_fetch.h"
#include "pagespeed/kernel/base/google_message_handler.h"
#include "pagespeed/kernel/base/null_message_handler.h"
#include "pagespeed/kernel/base/posix_timer.h"
#include "pagespeed/kernel/base/stack_buffer.h"
#include "pagespeed/kernel/base/stdio_file_system.h"
#include "pagespeed/kernel/base/string.h"
#include "pagespeed/kernel/base/string_writer.h"
#include "pagespeed/kernel/base/time_util.h"
#include "pagespeed/kernel/http/content_type.h"
#include "pagespeed/kernel/http/google_url.h"
#include "pagespeed/kernel/http/query_params.h"
#include "pagespeed/kernel/html/html_keywords.h"
#include "pagespeed/kernel/thread/pthread_shared_mem.h"
#include "pagespeed/kernel/util/gzip_inflater.h"
#include "pagespeed/kernel/util/statistics_logger.h"
#include "pagespeed/system/in_place_resource_recorder.h"
#include "pagespeed/system/system_caches.h"
#include "pagespeed/system/system_request_context.h"
#include "pagespeed/system/system_rewrite_options.h"
#include "pagespeed/system/system_server_context.h"
#include "pagespeed/system/system_thread_system.h"



#define MODPAGESPEEDVERSION  "2.1-1.11.33.4"

#define DBG(session, args...) g_api->log(session, LSI_LOG_DEBUG, args)

#define  POST_BUF_READ_SIZE 65536

// Needed for SystemRewriteDriverFactory to use shared memory.
#define PAGESPEED_SUPPORT_POSIX_SHARED_MEM
#define PAGESPEED_RESP_HEADER "X-LS-Pagespeed"


enum {
    PS_STATE_INIT = 0,
    PS_STATE_RECV_REQ,
    PS_STATE_RECV_RESP_HEADER,
    PS_STATE_SEND_RESP_BODY,
    PS_STATE_DONE,
};



using namespace net_instaweb;

/**************************************************************************************************
 *
 * Understand the order of initialising
 * Onece find module in list, load module .so first,
 * then parse config will be called when it has parameter
 * then, _init() will be called for init the module after all modules loaded
 * now, all config read, and server start to serv.
 * then, main_inited HOOK will be called
 * pre_fork HOOK will be launched before children process forking.
 *
 *
 * ************************************************************************************************/

//All of the parameters should have "pagespeed" as the first word.
static lsi_config_key_s paramArray[] =
{
    {"pagespeed", 0, 0},
    {NULL,0,0} //Must have NULL in the last item
};

//process level data, can be accessed anywhere
struct LsPsGlobalCtx
{
    LsRewriteDriverFactory  *driverFactory;
    Statistics              *global_statistics;

public:
    LsPsGlobalCtx()
        : driverFactory(NULL)
        , global_statistics(NULL)
        {}
    ~LsPsGlobalCtx()
    {
        if (driverFactory)
        {
            delete driverFactory;
            driverFactory = NULL;
        }
    }
};

//VHost level data
struct LsPsVhCtx
{
    LsServerContext            *serverContext;
    RewriteOptions             *options;
    ProxyFetchFactory          *proxyFetchFactory;
    MessageHandler             *handler;
public:
    LsPsVhCtx()
    {
        LS_ZERO_FILL(serverContext, handler);
    }
    
    ~LsPsVhCtx()
    {
        if (serverContext)
            delete serverContext;
        if (proxyFetchFactory)
            delete proxyFetchFactory;
        if (handler)
            delete handler;
    }
};

struct LsPsReqCtx
{
    LsiBaseFetch *baseFetch;
    //lsi_session_t *session;

    // for html rewrite
    ProxyFetch *proxyFetch;

    // for in place resource
    RewriteDriver *driver;
    InPlaceResourceRecorder *recorder;

    bool htmlRewrite;
    bool inPlace;
    bool fetchDone;
    
    PreserveCachingHeaders preserveCachingHeaders;

public: 
    LsPsReqCtx()
    {
        LS_ZERO_FILL(baseFetch, fetchDone);
    }
    ~LsPsReqCtx()
    {
    // proxy_fetch deleted itself if we called Done(), but if an error happened
    // before then we need to tell it to delete itself.
    //
    // If this is a resource fetch then proxy_fetch was never initialized.
        if (proxyFetch)
        {
            proxyFetch->Done(false /* failure */);
            proxyFetch = NULL;
        }
        if (driver)
        {
            driver->Cleanup();
            driver = NULL;
        }
        if (recorder)
        {
            recorder->Fail();
            recorder->DoneAndSetHeaders(NULL, false);    // Deletes recorder.
            recorder = NULL;
        }
        if (baseFetch)
        {
            baseFetch->Release();
            baseFetch = NULL;
        }
    }
}; 


#define PSF_IS_SUBREQ       1
#define PSF_NO_HOOK         2
#define PSF_OPT_OVERRIDE    4
#define PSF_IS_ADMIN        8
#define PSF_IS_PS_RES       16
#define PSF_END_RESP        32


struct LsPsReq
{
    StringPiece         userAgent;
    GoogleString        urlString;
    RequestContextPtr   request_context;
    GoogleString        pagespeed_query_params;
    GoogleString        pagespeed_option_cookies;
    RequestHeaders     *reqHeaders;
    GoogleString       *urlStriped; 
    GoogleUrl          *url;
    RewriteOptions     *options;
    ResponseHeaders    *respHeaders;
    LSI_REQ_METHOD      method;

public:
    
    LsPsReq()
    {
        LS_ZERO_FILL( reqHeaders, method);
    }
    
    ~LsPsReq()
    {
        if (urlStriped && urlStriped != &urlString)
            delete urlStriped;
        if (url)
            delete url;
        if (reqHeaders)
            delete reqHeaders;
        if (respHeaders)
            delete respHeaders;
    }
};


struct PsMData
{
    LsPsReqCtx          *reqCtx;
    LsPsVhCtx           *vhCtx;
    LsPsReq             *request;

    //return result
    int16_t              statusCode;
    ResponseHeaders     *respHeaders;

    int16_t              flags;
    int8_t               doneCalled;
    size_t               nBuffOffset;
    int8_t               state;
    GoogleString         sBuff;

public:
    PsMData()
    {
        LS_ZERO_FILL( reqCtx, state);
    }
    
    ~PsMData()
    {
        if (reqCtx)
        {
            if (reqCtx->baseFetch)
            {
                reqCtx->baseFetch->SetRequestHeadersTakingOwnership(
                    request->reqHeaders);
                request->reqHeaders = NULL;
            }
            delete reqCtx;
        }
        if (flags & PSF_OPT_OVERRIDE)
            delete request->options;
        
        if (request)
            delete request;
        
        if (respHeaders)
            delete respHeaders;
    }
    
    void ReleaseBaseFetch()
    {
        // In the normal flow BaseFetch doesn't delete itself in HandleDone() because
        // we still need to receive notification via pipe and call
        // CollectAccumulatedWrites.  If there's an error and we're cleaning up early
        // then HandleDone() hasn't been called yet and we need the base fetch to wait
        // for that and then delete itself.
        if (reqCtx == NULL)
            return ;
        
        if (reqCtx->baseFetch != NULL)
        {
            reqCtx->baseFetch->Release();
            reqCtx->baseFetch = NULL;
        }

        sBuff.clear();
        nBuffOffset = 0;
        doneCalled = false;
    }
    

};

const char *kInternalEtagName = "@psol-etag";
// The process context takes care of proactively initialising
// a few libraries for us, some of which are not thread-safe
// when they are initialized lazily.
ProcessContext *g_pProcessContext = new ProcessContext();

//LsiRewriteOptions* is data in all level and just inherit with the flow
//global --> Vhost  --> context  --> session
static LsPsGlobalCtx *g_pPsGlobalCtx = NULL;
static int g_bMainConfInited = 0;


//////////////////////

int SetCacheControl(lsi_session_t *session, char *cache_control)
{
    g_api->set_resp_header(session, LSI_RSPHDR_CACHE_CTRL, NULL, 0,
                           cache_control, strlen(cache_control), LSI_HEADEROP_SET);
    return 0;
}

int SetLimitCacheControl(lsi_session_t *session, char *buffer, int len)
{
    GoogleString str;
    str.append(buffer, len);
    char *p = (char *)strcasestr(str.c_str(), "max-age");
    if (p)
    {
        p = strchr(p + 7, '=');
        if (p)
        {
            int age = atoi(p + 1);
            if (age > CACHE_MAX_AGE)
            {
                int width = strlen(CACHE_MAX_AGE_STR);
                strncpy((char *)p + 1, CACHE_MAX_AGE_STR, width);
                p += 1 + width;
                while(isdigit(*p))
                {
                    *p = ' ';
                    ++p;
                }
            }
        }
    }
    SetCacheControl(session, (char *)str.c_str());
    return 0;
}


//If copy_request is 0, then copy response headers
//Othercopy request headers.
template<class Headers>
void CopyHeaders(lsi_session_t *session, int is_from_request, Headers *to)
{
#define MAX_HEADER_NUM  50
    struct iovec iov_key[MAX_HEADER_NUM], iov_val[MAX_HEADER_NUM];
    int count = 0;

    if (is_from_request)
        count = g_api->get_req_headers(session, iov_key, iov_val, MAX_HEADER_NUM);
    else
        count = g_api->get_resp_headers(session, iov_key, iov_val, MAX_HEADER_NUM);

    for (int i = 0; i < count; ++i)
    {
        StringPiece key = "", value = "";
        key.set(iov_key[i].iov_base, iov_key[i].iov_len);
        value.set(iov_val[i].iov_base, iov_val[i].iov_len);
        to->Add(key, value);
    }
}

//return 1001 for 1.1, 2000 for 2.0 etc
static int GetHttpVersion(lsi_session_t *session)
{
    int major = 0, minor = 0;
    char val[10] = {0};
    int n = g_api->get_req_var_by_id(session, LSI_VAR_SERVER_PROTO, val, 10);
    if (n >= 8)   //should be http/
    {
        char *p = strchr(val, '/');
        if (p)
            sscanf(p + 1, "%d.%d", &major, &minor);
    }

    return major * 1000 + minor;
}

void net_instaweb::CopyRespHeadersFromServer(
    lsi_session_t *session, ResponseHeaders *headers)
{
    int version = GetHttpVersion(session);
    headers->set_major_version(version / 1000);
    headers->set_minor_version(version % 1000);
    CopyHeaders(session, 0, headers);
    headers->set_status_code(g_api->get_status_code(session));

    struct iovec iov[1];
    if (g_api->get_resp_header(session, LSI_RSPHDR_CONTENT_TYPE, NULL, 0,
                               iov, 1) == 1)
    {
        StringPiece content_type = "";
        content_type.set(iov[0].iov_base, iov[0].iov_len);
        headers->Add(HttpAttributes::kContentType, content_type);
    }

    // When we don't have a date header, set one with the current time.
    if (headers->Lookup1(HttpAttributes::kDate) == NULL)
    {
        int64 date_ms;
        int32_t date_us;
        date_ms = (g_api->get_cur_time(&date_us)) * 1000;
        date_ms += date_us / 1000;
        headers->SetDate(date_ms);
    }

    headers->ComputeCaching();
}

void net_instaweb::CopyReqHeadersFromServer(lsi_session_t *session,
        RequestHeaders *headers)
{
    int version = GetHttpVersion(session);
    headers->set_major_version(version / 1000);
    headers->set_minor_version(version % 1000);
    CopyHeaders(session, 1, headers);
}

int net_instaweb::CopyRespHeadersToServer(
    lsi_session_t *session,
    const ResponseHeaders &pagespeed_headers,
    PreserveCachingHeaders preserve_caching_headers)
{
    int i;
    for (i = 0 ; i < pagespeed_headers.NumAttributes() ; i++)
    {
        const GoogleString &name_gs = pagespeed_headers.Name(i);
        const GoogleString &value_gs = pagespeed_headers.Value(i);
        
        //If etag not PAGESPEED style, meas not optimized, so not cahce it
        if (StringCaseEqual(name_gs, "etag")
            && !StringCaseStartsWith(value_gs, "W/"))
            g_api->set_req_env(session, "cache-control", 13, "no-cache", 8);
        
        if (preserve_caching_headers == kPreserveAllCachingHeaders)
        {
            if (StringCaseEqual(name_gs, "ETag") ||
                StringCaseEqual(name_gs, "Expires") ||
                StringCaseEqual(name_gs, "Date") ||
                StringCaseEqual(name_gs, "Last-Modified") ||
                StringCaseEqual(name_gs, "Cache-Control"))
                continue;
        }
        else if (preserve_caching_headers == kPreserveOnlyCacheControl)
        {
            // Retain the original Cache-Control header, but send the recomputed
            // values for all other cache-related headers.
            if (StringCaseEqual(name_gs, "Cache-Control"))
                continue;
        } // else we don't preserve any headers

        AutoStr2 name, value;

        // To prevent the gzip module from clearing weak etags, we output them
        // using a different name here. The etag header filter module runs behind
        // the gzip compressors header filter, and will rename it to 'ETag'
        if (StringCaseEqual(name_gs, "etag")
            && StringCaseStartsWith(value_gs, "W/"))
            name.setStr(kInternalEtagName, strlen(kInternalEtagName));
        else
            name.setStr(name_gs.data(), name_gs.length());
        
        value.setStr(value_gs.data(), value_gs.length());


        if (STR_EQ_LITERAL(name, "Cache-Control"))
        {
            SetLimitCacheControl(session, (char *)value_gs.c_str(),
                                 value_gs.length());
            continue;
        }
        else if (STR_EQ_LITERAL(name, "Content-Type"))
        {
            g_api->set_resp_header(session, LSI_RSPHDR_CONTENT_TYPE, NULL, 0,
                                   value.c_str(), value.len(), LSI_HEADEROP_SET);
            continue;
        }
        else if (STR_EQ_LITERAL(name, "Connection"))
            continue;
        else if (STR_EQ_LITERAL(name, "Keep-Alive"))
            continue;
        else if (STR_EQ_LITERAL(name, "Transfer-Encoding"))
            continue;
        else if (STR_EQ_LITERAL(name, "Server"))
            continue;

        bool need_set = false;

        // Populate the shortcuts to commonly used headers.
        if (STR_EQ_LITERAL(name, "Date"))
            need_set = true;
        else if (STR_EQ_LITERAL(name, "Etag"))
            need_set = true;
        else if (STR_EQ_LITERAL(name, "Expires"))
            need_set = true;
        else if (STR_EQ_LITERAL(name, "Last-Modified"))
            need_set = true;
        else if (STR_EQ_LITERAL(name, "Location"))
            need_set = true;
        else if (STR_EQ_LITERAL(name, "Server"))
            need_set = true;
        else if (STR_EQ_LITERAL(name, "Content-Length"))
        {
            need_set = false;
         //   g_api->set_resp_content_length(session, (int64_t) atol(value.c_str()));
        }

        else if (STR_EQ_LITERAL(name, "Content-Encoding"))
            need_set = true;
        else if (STR_EQ_LITERAL(name, "Refresh"))
            need_set = true;
        else if (STR_EQ_LITERAL(name, "Content-Range"))
            need_set = true;
        else if (STR_EQ_LITERAL(name, "Accept-Ranges"))
            need_set = true;
        else if (STR_EQ_LITERAL(name, "WWW-Authenticate"))
            need_set = true;

        if (need_set)
        {
            g_api->set_resp_header(session, -1, name.c_str(), name.len(),
                                   value.c_str(), value.len(), LSI_HEADEROP_SET);
        }
    }

    return 0;
}


int net_instaweb::CopyRespBodyToBuf(lsi_session_t *session, GoogleString &str,
                                    int done_called)
{
    PsMData *pMyData = (PsMData *) g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);
    //pMyData->status_code = 200;
    if (pMyData->sBuff.size() > 0)
        pMyData->sBuff.append(str);
    else
        pMyData->sBuff.swap(str);
    g_api->log(session, LSI_LOG_DEBUG,
               "[modpagespeed] receive resposne body %zd bytes from base fetch, doneCalled: %d\n",
               pMyData->sBuff.size(), done_called);

    pMyData->nBuffOffset = 0;
    pMyData->doneCalled = done_called;
    return 0;
}


static void PageSpeedAtExit()
{
    if (g_pPsGlobalCtx)
    {
        LsRewriteOptions::Terminate();
        LsRewriteDriverFactory::Terminate();
        delete g_pPsGlobalCtx;
        g_pPsGlobalCtx = NULL;
    }

    if (g_pProcessContext)
    {
        delete g_pProcessContext;
        g_pProcessContext = NULL;
    }
}


int TerminateMainConf(lsi_param_t *rec)
{
    PageSpeedAtExit();
    return 0;
}

static int ReleaseVhCtx(void *p)
{
    if (!p)
        return 0;
    LsPsVhCtx *ctx = (LsPsVhCtx *) p;
    delete ctx;

    return 0;
}




static int ReleaseMydata(void *data)
{
    PsMData *pData = (PsMData *) data;

    if (!pData)
        return 0;

    pData->sBuff.clear();
    pData->nBuffOffset = 0;
    delete pData;
    return 0;
}

int EndSession(lsi_param_t *rec)
{
    lsi_session_t *session = (lsi_session_t *)rec->session;
    PsMData *pData = (PsMData *) g_api->get_module_data(session, &MNAME,
                     LSI_DATA_HTTP);

    if (pData != NULL)
    {
        g_api->log(session, LSI_LOG_DEBUG,
                   "[%s] ps_end_session, session=%p pData=%p.\n",
                   ModuleName, session, pData);
        long evt_obj;
        if (pData->reqCtx && pData->reqCtx->baseFetch 
            && (evt_obj = pData->reqCtx->baseFetch->AtomicSetEventObj(0)) != 0)
        {
            g_api->log(session, LSI_LOG_DEBUG,
                       "[%s] pending event: %ld for base fetch need to be cancelled for session=%p.\n",
                       ModuleName, evt_obj, session);
            g_api->cancel_event(session, evt_obj);
        }
        
        g_api->free_module_data(session, &MNAME, LSI_DATA_HTTP, ReleaseMydata);
    }


    return 0;
}

bool IsHttps(lsi_session_t *session)
{
    char s[12] = {0};
    int len = g_api->get_req_var_by_id(session, LSI_VAR_HTTPS, s, 12);
    if( len == 2)
        return true;
    return false;
}

void IgnoreSigpipe()
{
    struct sigaction act;
    memset(&act, 0, sizeof(act));
    act.sa_handler = SIG_IGN;
    sigemptyset(&act.sa_mask);
    act.sa_flags = 0;
    sigaction(SIGPIPE, &act, NULL);
}

void InitDir(const StringPiece &directive,
             const StringPiece &path)
{
    if (path.size() == 0 || path[0] != '/')
    {
        g_api->log(NULL, LSI_LOG_ERROR, "[%s] %s %s must start with a slash.\n",
                   ModuleName, directive.as_string().c_str(),
                   path.as_string().c_str());
        return ;
    }

    net_instaweb::StdioFileSystem file_system;
    net_instaweb::NullMessageHandler message_handler;
    GoogleString gs_path;
    path.CopyToString(&gs_path);

    if (!file_system.IsDir(gs_path.c_str(), &message_handler).is_true())
    {
        if (!file_system.RecursivelyMakeDir(path, &message_handler))
        {
            g_api->log(NULL, LSI_LOG_ERROR,
                       "[%s] %s path %s does not exist and could not be created.\n",
                       ModuleName, directive.as_string().c_str(),
                       path.as_string().c_str());
            return ;
        }

        // Directory created, but may not be readable by the worker processes.
    }

    if (geteuid() != 0)
    {
        return;  // We're not root, so we're staying whoever we are.
    }

    uid_t user = ServerProcessConfig::getInstance().getUid();
    gid_t group = ServerProcessConfig::getInstance().getGid();


    struct stat gs_stat;

    if (stat(gs_path.c_str(), &gs_stat) != 0)
    {
        g_api->log(NULL, LSI_LOG_ERROR, "[%s] %s path %s stat() failed.\n",
                   ModuleName, directive.as_string().c_str(),
                   path.as_string().c_str());
        return ;
    }

    if (gs_stat.st_uid != user)
    {
        if (chown(gs_path.c_str(), user, group) != 0)
        {
            g_api->log(NULL, LSI_LOG_ERROR,
                       "[%s] %s path %s unable to set permissions.\n",
                       ModuleName, directive.as_string().c_str(),
                       path.as_string().c_str());
            return ;
        }
    }
}


//return 0 OK, -1 error
static int InitGlobalCtx()
{
    if (g_bMainConfInited == 1)
        return 0;

    g_bMainConfInited = 1;
    g_api->log(NULL, LSI_LOG_INFO, "[%s] Initializing pagespeed library %s ...\n", 
               ModuleName, net_instaweb::kModPagespeedVersion);
    g_pPsGlobalCtx = new LsPsGlobalCtx;

    if (!g_pPsGlobalCtx)
    {
        g_api->log(NULL, LSI_LOG_ERROR, "[%s]GDItem init error.\n", ModuleName);
        return LS_FAIL;
    }

    LsRewriteOptions::Initialize();
    LsRewriteDriverFactory::Initialize();

    g_pPsGlobalCtx->driverFactory = new LsRewriteDriverFactory(
        *g_pProcessContext,
        new SystemThreadSystem(),
        "" /* hostname, not used */,
        -1 /* port, not used */);

    if (g_pPsGlobalCtx->driverFactory == NULL)
    {
        delete g_pPsGlobalCtx;
        g_pPsGlobalCtx = NULL;
        g_api->log(NULL, LSI_LOG_ERROR, "[%s]GDItem init error 2.\n", ModuleName);
        return LS_FAIL;
    }

    g_pPsGlobalCtx->driverFactory->LoggingInit();
    g_pPsGlobalCtx->driverFactory->Init();
    
    SystemRewriteDriverFactory::InitApr();
    //atexit(PageSpeedAtExit);
    return 0;
}


void releaseDriverFactory()
{
    if (g_pPsGlobalCtx->driverFactory)
    {
        delete g_pPsGlobalCtx->driverFactory;
        g_pPsGlobalCtx->driverFactory = NULL;
    }
}


inline void TrimLeadingSpace(const char **p)
{
    char ch;
    while (((ch = **p) == ' ') || (ch == '\t') || (ch == '\r'))
        ++ (*p);
}

static void ParseOption(LsRewriteOptions *pOption, const char *sLine,
                        int len, int level, const char *name)
{
    /***
     * The parameters can have "ModPagespeed" or "pagespeed" at the beginning.
     * Just for compatible with pagespeed module of Apache and Nginx configures.
     */
    const char *pEnd = sLine + len;
    TrimLeadingSpace(&sLine);
    
    while (isspace(*(pEnd - 1)))
        -- pEnd;
    if (*(pEnd - 1) == ';')
        -- pEnd;

    if (pEnd - sLine >= 12 && strncasecmp(sLine, "pagespeed", 9) == 0)
    {
        //assert(isblank(sLine[9]);
        sLine += 10;
    }
    else if (pEnd - sLine >= 14 && strncasecmp(sLine, "ModPagespeed", 12) == 0)
    {
        sLine += 12;
    }
    skip_leading_space(&sLine);
    
    if (pEnd - sLine < 2)
        return ;

    g_api->log(NULL, LSI_LOG_DEBUG,
                   "[modpagespeed] ParseOption parsing '%.*s' on level %d [%s]\n",
                   (int)(pEnd - sLine), sLine, level, name);

#define MAX_ARG_NUM 5
    StringPiece args[MAX_ARG_NUM];
    int narg = 0;
    const char *argBegin, *argEnd, *pError;


    while (narg < MAX_ARG_NUM && sLine < pEnd &&
           StringTool::parseNextArg(sLine, pEnd, argBegin, argEnd, pError) == 0)
    {
        args[narg ++].set(argBegin, argEnd - argBegin);
        skip_leading_space(&sLine);
    }

    MessageHandler *handler = g_pPsGlobalCtx->driverFactory->message_handler();
    RewriteOptions::OptionScope scope;

    switch (level)
    {
    case LSI_CFG_SERVER:
        scope = RewriteOptions::kProcessScope;// customized at process level only (command-line flags)
        break;

    case LSI_CFG_VHOST:
        scope = RewriteOptions::kServerScope;// customized at server level (e.g. VirtualHost)
        break;

    case LSI_CFG_CONTEXT:
        //customized at directory level (.htaccess, <Directory>)
        scope = RewriteOptions::kDirectoryScope;
        break;

    default:
        scope = RewriteOptions::kProcessScope;
        break;
    }

    if (narg == 2 &&
        (net_instaweb::StringCaseEqual("LogDir", args[0]) ||
         net_instaweb::StringCaseEqual("FileCachePath", args[0])))
        InitDir(args[0], args[1]);

    // The directory has been prepared, but we haven't actually parsed the
    // directive yet.  That happens below in ParseAndSetOptions().
    pOption->ParseAndSetOptions(args, narg, handler,
                                g_pPsGlobalCtx->driverFactory, scope);

}

#define DEFAULT_SERVER_CONFIG  "pagespeed FileCachePath /tmp/httpd_pagespeed_/"
static void *ParseConfig(module_param_info_t *param, int paramCount,
                         void *_initial_config, int level, const char *name)
{
    if (InitGlobalCtx())
        return NULL;

    LsRewriteOptions *pInitOption = (LsRewriteOptions *) _initial_config;
    LsRewriteOptions *pOption = NULL;

    if (level == LSI_CFG_SERVER)
    {
        //Server level should not have higher level config(_initial_config)
        assert(_initial_config == 0x00);
        pOption = (LsRewriteOptions *)g_pPsGlobalCtx->driverFactory
                                ->default_options()->Clone();
    }
    else if (pInitOption)
        pOption = pInitOption->Clone();
    else
        pOption = new LsRewriteOptions(
            g_pPsGlobalCtx->driverFactory->thread_system());

    if (!pOption)
        return NULL;

    if (!param || paramCount == 0)
    {
        if (level == LSI_CFG_SERVER)
        {
            ParseOption(pOption, DEFAULT_SERVER_CONFIG,
                        sizeof(DEFAULT_SERVER_CONFIG) -1, level, name);
        }
        return (void *) pOption;
    }

    for (int i=0; i< paramCount; ++i)
    {
        ParseOption(pOption, param[i].val, param[i].val_len, level, name);
    }

    return (void *) pOption;
}

static void FreeConfig(void *_config)
{
    delete(LsRewriteOptions *) _config;
}

// static void *MergeConfig(void *child, const void *parent)
// {
//     const LsRewriteOptions *parent_options = (LsRewriteOptions *)parent;
//     
//     LsRewriteOptions *options;
//     options = parent_options->Clone();
//     options->Merge(*(LsRewriteOptions *)child);
//     return options;
// }



static int dummy_port = 0;
static int InitGlobalStats()
{
    std::vector<SystemServerContext *> server_contexts;
    if (!g_pPsGlobalCtx)
        return LS_FAIL;
    LsServerContext *serverContext = g_pPsGlobalCtx->driverFactory
        ->MakeLsServerContext("dummy_hostname", --dummy_port, 1);

    LsRewriteOptions *server_option;
    server_option = (LsRewriteOptions *)g_api->get_config(NULL, &MNAME);
    if (server_option)
        serverContext->global_options()->Merge(*server_option);
    server_contexts.push_back(serverContext);

    GoogleString error_message = "";
    int error_index = -1;
    Statistics *global_statistics = NULL;

    g_api->log(NULL, LSI_LOG_DEBUG,
               "mod_pagespeed post_config call PostConfig()\n");
    g_pPsGlobalCtx->driverFactory->PostConfig(
        server_contexts, &error_message, &error_index, &global_statistics);


    if (error_index != -1)
    {
        //server_contexts[error_index]->message_handler()->Message(
        //    kError, "mod_pagespeed is enabled. %s", error_message.c_str());
        g_api->log(NULL, LSI_LOG_ERROR, "mod_pagespeed is disabled. %s\n", 
                   error_message.c_str());
        releaseDriverFactory();
        return LS_FAIL;
    }

    IgnoreSigpipe();

    if (global_statistics == NULL)
        LsRewriteDriverFactory::InitStats(
            g_pPsGlobalCtx->driverFactory->statistics());
    else
        g_pPsGlobalCtx->global_statistics = global_statistics;
    g_pPsGlobalCtx->driverFactory->LoggingInit();
    g_pPsGlobalCtx->driverFactory->RootInit();
    //delete serverContext;
    return LS_OK;
}


static LsPsVhCtx *initVhostContext(const void *vhost)
{
    if (g_pPsGlobalCtx->driverFactory == NULL)
        return NULL;
    LsRewriteOptions *vhost_option;
    vhost_option = (LsRewriteOptions *) g_api->get_vhost_module_param(vhost, 
                                                                      &MNAME);

    //Comment: when Amdin/html parse, this will be NULL, we need not to add it
    if (vhost_option == NULL)
        return NULL;
    
    LsPsVhCtx *vhCtx = new LsPsVhCtx;
    vhCtx->options = vhost_option;
    g_api->set_vhost_module_data(vhost, &MNAME, vhCtx);
    vhCtx->serverContext = g_pPsGlobalCtx->driverFactory->MakeLsServerContext(
                                "dummy_hostname", --dummy_port, 0);

    SystemRewriteOptions* options;
    options = vhCtx->serverContext->global_system_rewrite_options();
    options->Merge(*vhost_option);
    vhCtx->handler = g_pPsGlobalCtx->driverFactory->message_handler();

    const char *file_cache_path =
        vhCtx->serverContext->Config()->file_cache_path().c_str();

    if (file_cache_path[0] == '\0')
    {
        g_api->log(NULL, LSI_LOG_ERROR,
                    "mod_pagespeed post_config ERROR, file_cache_path is "
                    "NULL, PageSpeed is disabled\n");
        options->set_enabled(
            RewriteOptions::kEnabledUnplugged);
        return vhCtx;
    }
    else if (!g_pPsGlobalCtx->driverFactory->file_system()->IsDir(
                    file_cache_path, vhCtx->handler).is_true())
    {
        g_api->log(NULL, LSI_LOG_ERROR,
                    "mod_pagespeed post_config ERROR, FileCachePath must "
                    "be an writeable directory, PageSpeed is disabled.\n");
        options->set_enabled(
            RewriteOptions::kEnabledUnplugged);
        return vhCtx;
    }

    g_api->log(NULL, LSI_LOG_DEBUG,
                "mod_pagespeed post_config OK, file_cache_path is %s\n",
                file_cache_path);
    vhCtx->serverContext->CollapseConfigOverlaysAndComputeSignatures();
    g_pPsGlobalCtx->driverFactory->caches()->RegisterConfig(options);
    
    if (options->statistics_enabled()) {
      // Lazily create shared-memory statistics if enabled in any config, even
      // when PageSpeed is totally disabled.  This allows statistics to work if
      // PageSpeed gets turned on via .htaccess or query param.

      // If we have per-vhost statistics on as well, then set it up.
      if (g_pPsGlobalCtx->driverFactory->use_per_vhost_statistics()) {
        vhCtx->serverContext->CreateLocalStatistics(
            g_pPsGlobalCtx->global_statistics, g_pPsGlobalCtx->driverFactory);
      }
    }
    
    vhCtx->serverContext->ChildInit(g_pPsGlobalCtx->driverFactory);
    
    vhCtx->proxyFetchFactory = new ProxyFetchFactory(vhCtx->serverContext);
    g_pPsGlobalCtx->driverFactory->SetServerContextMessageHandler(
        vhCtx->serverContext);
    return vhCtx;
}


static int ChildInit(lsi_param_t *rec);
static int PostConfig(lsi_param_t *rec)
{
    InitGlobalCtx();
    return InitGlobalStats();
//     std::vector<SystemServerContext *> server_contexts;
//     int vhost_count = g_api->get_vhost_count();
// 
//     for (int s = 0; s < vhost_count; s++)
//     {
//         const void *vhost = g_api->get_vhost(s);
// 
//         LsRewriteOptions *vhost_option = (LsRewriteOptions *)
//                                           g_api->get_vhost_module_param(vhost, &MNAME);
// 
//         //Comment: when Amdin/html parse, this will be NULL, we need not to add it
//         if (vhost_option != NULL)
//         {
//             LsPsVhCtx *vhCtx = new LsPsVhCtx;
//             vhCtx->serverContext = g_pPsGlobalCtx->driverFactory->MakeLsServerContext(
//                                        "dummy_hostname", --dummy_port);
// 
//             vhCtx->serverContext->global_options()->Merge(*vhost_option);
//             vhCtx->handler =
//                 g_pPsGlobalCtx->driverFactory->message_handler();
//             // LsiMessageHandler(pMainConf->driver_factory->thread_system()->NewMutex());
//             //Why GoogleMessageHandler() but not LsMessageHandler
// 
//             if (vhCtx->serverContext->global_options()->enabled())
//             {
//                 //GoogleMessageHandler handler;
//                 const char *file_cache_path =
//                     vhCtx->serverContext->Config()->file_cache_path().c_str();
// 
//                 if (file_cache_path[0] == '\0')
//                 {
//                     g_api->log(NULL, LSI_LOG_ERROR,
//                                "mod_pagespeed post_config ERROR, file_cache_path is NULL\n");
//                     return LS_FAIL;
//                 }
//                 else if (!g_pPsGlobalCtx->driverFactory->file_system()->IsDir(
//                              file_cache_path, vhCtx->handler).is_true())
//                 {
//                     g_api->log(NULL, LSI_LOG_ERROR,
//                                "mod_pagespeed post_config ERROR, FileCachePath must be an writeable directory.\n");
//                     return LS_FAIL;
//                 }
// 
//                 g_api->log(NULL, LSI_LOG_DEBUG,
//                            "mod_pagespeed post_config OK, file_cache_path is %s\n",
//                            file_cache_path);
//             }
// 
//             g_api->set_vhost_module_data(vhost, &MNAME, vhCtx);
//             server_contexts.push_back(vhCtx->serverContext);
//         }
//     }
// 
// 
//     GoogleString error_message = "";
//     int error_index = -1;
//     Statistics *global_statistics = NULL;
// 
//     g_api->log(NULL, LSI_LOG_DEBUG,
//                "mod_pagespeed post_config call PostConfig()\n");
//     g_pPsGlobalCtx->driverFactory->PostConfig(
//         server_contexts, &error_message, &error_index, &global_statistics);
// 
//     if (error_index != -1)
//     {
//         server_contexts[error_index]->message_handler()->Message(
//             kError, "mod_pagespeed is enabled. %s", error_message.c_str());
//         //g_api->log( NULL, LSI_LOG_ERROR, "mod_pagespeed is enabled. %s\n", error_message.c_str() );
//         return LS_FAIL;
//     }
// 
// 
//     if (!server_contexts.empty())
//     {
//         IgnoreSigpipe();
// 
//         if (global_statistics == NULL)
//             LsRewriteDriverFactory::InitStats(
//                 g_pPsGlobalCtx->driverFactory->statistics());
// 
//         g_pPsGlobalCtx->driverFactory->LoggingInit();
//         g_pPsGlobalCtx->driverFactory->RootInit();
//     }
//     else
//     {
//         delete g_pPsGlobalCtx->driverFactory;
//         g_pPsGlobalCtx->driverFactory = NULL;
//     }
// 

}

static int ChildInit(lsi_param_t *rec)
{
    if (!g_pPsGlobalCtx)
        return LS_FAIL;
    if (g_pPsGlobalCtx->driverFactory == NULL)
        return 0;

    g_pPsGlobalCtx->driverFactory->LoggingInit();
    g_pPsGlobalCtx->driverFactory->ChildInit();

    g_pPsGlobalCtx->driverFactory->StartThreads();
    return 0;
}

static int BaseFetchDoneCb(evtcbhead_s *session_, long, void *);
static int CreateBaseFetch(PsMData *pMyData, lsi_session_t *session,
                    RequestContextPtr request_context,
                    RequestHeaders *request_headers,
                    BaseFetchType type,
                    evtcb_pf callback)
{
    if (pMyData->reqCtx->baseFetch)
    {
        long evt_obj;
        if ((evt_obj = pMyData->reqCtx->baseFetch->AtomicSetEventObj(0)) != 0)
            g_api->cancel_event(session, evt_obj);
    }

    pMyData->reqCtx->baseFetch = new LsiBaseFetch(
        session, pMyData->vhCtx->serverContext, request_context,
        pMyData->reqCtx->preserveCachingHeaders, type);

    //When the base_fetch is good then set the callback, otherwise, may cause crash.
    if (pMyData->reqCtx->baseFetch)
    {
        //pMyData->reqCtx->baseFetch->SetRequestHeadersTakingOwnership(request_headers);
        pMyData->reqCtx->baseFetch->set_request_headers(request_headers);
        long event_obj = g_api->get_event_obj(callback, session, 0, 0);
        g_api->log(session, LSI_LOG_DEBUG,
               "[ModPagespeed] CreateBaseFetch() get event obj %ld, session=%p\n",
               event_obj, session);
        pMyData->reqCtx->baseFetch->AtomicSetEventObj(event_obj);
// //        session->setBackRefPtr(&pMyData->ctx->session, 1);
//         g_api->set_session_back_ref_ptr(session, 
//                                         g_api->get_session_ref_ptr(event_obj));
        return 0;
    }
    else
        return LS_FAIL;
}

static bool IsHtmlLikeContent(PsMData *pMyData, lsi_session_t *session)
{
//     //Check status code is it is 200
//     if( g_api->get_status_code( session ) != 200 )
//     {
//         return false;
//     }

    // We can't operate on Content-Ranges.
    iovec iov;

    if (g_api->get_resp_header(session, LSI_RSPHDR_CONTENT_TYPE, NULL, 0,
                               &iov, 1) != 1)
    {
        g_api->log(session, LSI_LOG_DEBUG,
                   "[%s] Request not rewritten because: no Content-Type set.\n",
                   ModuleName);
        return false;
    }
  
    //only "text/html", "application/xhtml+xml", "application/ce-html+xml"
    //  are considered as html like content.

    const char *pContentType = (const char *)iov.iov_base;
    
    switch(*pContentType)
    {
    case 't':
    case 'T':
        if (iov.iov_len >= 9
            && strncasecmp(pContentType, "text/html", 9) == 0)
            return true;
        break;
    case 'a':
    case 'A':
        if (iov.iov_len >= 21 
            && strncasecmp(pContentType, "application/", 12) == 0)
        {
            if (strncasecmp(pContentType + 12, "xhtml+xml", 9) == 0)
                return true;
            else if(iov.iov_len >= 23
                    && strncasecmp(pContentType + 12, "ce-html+xml", 11) == 0)
                return true;
        }
        break;
    }
    g_api->log(session, LSI_LOG_DEBUG,
               "[%s]Request not rewritten because:[%.*s] not 'html like' Content-Type.\n",
               ModuleName, (int)iov.iov_len, pContentType);
    return false;
}

int net_instaweb::DeterminePort(lsi_session_t *session)
{
    const int maxLen = 12;
    int port = -1;
    char portC[maxLen];
    g_api->get_req_var_by_id(session, LSI_VAR_SERVER_PORT, portC, maxLen);
    StringPiece port_str = portC;
    bool ok = StringToInt(port_str, &port);

    if (!ok)
    {
        // Might be malformed port, or just IPv6 with no port specified.
        return LS_FAIL;
    }

    return port;
}


static void DetermineUrl(lsi_session_t *session, GoogleString &str)
{
    int port = DeterminePort(session);
    GoogleString port_string;
    int isHttps = IsHttps(session);

    if ((isHttps && (port == 443 || port == -1)) ||
        (!isHttps && (port == 80 || port == -1)))
    {
        // No port specifier needed for requests on default ports.
        port_string = "";
    }
    else
        port_string = StrCat(":", IntegerToString(port));

    char host[512];
    g_api->get_req_var_by_id(session, LSI_VAR_SERVER_NAME, host, 512);

    int iQSLen;
    const char *pQS = g_api->get_req_query_string(session, &iQSLen);
    int uriLen = g_api->get_req_org_uri(session, NULL, 0);
    char *uri = new char[uriLen + 1 + iQSLen + 1];
    g_api->get_req_org_uri(session, uri, uriLen + 1);
    if (iQSLen > 0)
    {
        strcat(uri, "?");
        strncat(uri, pQS, iQSLen);
    }

    str = StrCat(isHttps ? "https://" : "http://",
                           host, port_string, uri);
    delete []uri;
}



// Wrapper around GetQueryOptions()
static RewriteOptions *DetermineRequestOptions(
    lsi_session_t *session,
    const RewriteOptions *domain_options, /* may be null */
    LsPsReq * pReq,
    RequestContextPtr request_context,
    LsPsVhCtx *vhCtx)
{
    // Sets option from request headers and url.
    RewriteQuery rewrite_query;

    if (!vhCtx->serverContext->GetQueryOptions(
            request_context, domain_options, pReq->url, pReq->reqHeaders,
            pReq->respHeaders, &rewrite_query))
    {
        // Failed to parse query params or request headers.  Treat this as if there
        // were no query params given.
        g_api->log(session, LSI_LOG_ERROR,
                   "ps_route request: parsing headers or query params failed.\n");
        return NULL;
    }

    pReq->pagespeed_query_params =
        rewrite_query.pagespeed_query_params().ToEscapedString();
    pReq->pagespeed_option_cookies =
        rewrite_query.pagespeed_option_cookies().ToEscapedString();

    // Will be NULL if there aren't any options set with query params or in
    // headers.
    return rewrite_query.ReleaseOptions();
}

// Check whether this visitor is already in an experiment.  If they're not,
// classify them into one by setting a cookie.  Then set options appropriately
// for their experiment.
//
// See InstawebContext::SetExperimentStateAndCookie()
static bool SetExperimentStateAndCookie(lsi_session_t *session,
                                 LsPsVhCtx *vhCtx,
                                 RequestHeaders *request_headers,
                                 RewriteOptions *options,
                                 const StringPiece &host)
{
    CHECK(options->running_experiment());
    bool need_cookie = vhCtx->serverContext->experiment_matcher()->
                       ClassifyIntoExperiment(*request_headers, 
                                              *vhCtx->serverContext->user_agent_matcher(),
                                              options);

    if (need_cookie && host.length() > 0)
    {
        PosixTimer timer;
        int64 time_now_ms = timer.NowMs();
        int64 expiration_time_ms = (time_now_ms +
                                    options->experiment_cookie_duration_ms());

        // TODO(jefftk): refactor SetExperimentCookie to expose the value we want to
        // set on the cookie.
        int state = options->experiment_id();
        GoogleString expires;
        ConvertTimeToString(expiration_time_ms, &expires);
        GoogleString value;
        SStringPrintf(&value,
                     "%s=%s; Expires=%s; Domain=.%s; Path=/",
                     experiment::kExperimentCookie,
                     experiment::ExperimentStateToCookieString(state).c_str(),
                     expires.c_str(), host.as_string().c_str());

        g_api->set_resp_header(session, LSI_RSPHDR_SET_COOKIE, NULL, 0,
                               value.c_str(), value.size(), LSI_HEADEROP_MERGE);
    }

    return true;
}

// There are many sources of options:
//  - the request (query parameters, headers, and cookies)
//  - location block
//  - global server options
//  - experiment framework
// Consider them all, returning appropriate options for this request, of which
// the caller takes ownership.  If the only applicable options are global,
// set options to NULL so we can use server_context->global_options().
static bool DetermineOptions(lsi_session_t *session,
                             LsPsReq *pReq,
                             const RewriteOptions *parent_options,
                             RewriteOptions **final_options,
                             RequestContextPtr request_context,
                             LsPsVhCtx *vhCtx,
                             bool html_rewrite)
{
    // Request-specific options, nearly always null.  If set they need to be
    // rebased on the directory options.
    RewriteOptions *request_options = DetermineRequestOptions(
        session, parent_options, pReq, request_context, vhCtx);
    bool have_request_options = request_options != NULL;

    RewriteOptions *options;
    // Modify our options in response to request options if specified.
    if (have_request_options)
    {
        options = parent_options->Clone();
        options->Merge(*request_options);
        delete request_options;
        request_options = NULL;
    }
    else
        options = (RewriteOptions *)parent_options;
    *final_options = options;

    // If we're running an experiment and processing html then modify our options
    // in response to the experiment.  Except we generally don't want experiments
    // to be contaminated with unexpected settings, so ignore experiments if we
    // have request-specific options.  Unless EnrollExperiment is on, probably set
    // by a query parameter, in which case we want to go ahead and apply the
    // experimental settings even if it means bad data, because we're just seeing
    // what it looks like.
    if (options->running_experiment() &&
        html_rewrite &&
        (!have_request_options ||
         options->enroll_experiment()))
    {
        if (options == parent_options)
            *final_options =  options = parent_options->Clone();
        bool ok = SetExperimentStateAndCookie(session, vhCtx, pReq->reqHeaders, 
                                              options, pReq->url->Host());
        if (!ok)
            return false;
    }

    return true;
}


// // Fix URL based on X-Forwarded-Proto.
// // http://code.google.com/p/modpagespeed/issues/detail?id=546 For example, if
// // Apache gives us the URL "http://www.example.com/" and there is a header:
// // "X-Forwarded-Proto: https", then we update this base URL to
// // "https://www.example.com/".  This only ever changes the protocol of the url.
// //
// // Returns true if it modified url, false otherwise.
// static bool ApplyXForwardedProto(lsi_session_t *session, GoogleString *url)
// {
//     int valLen = 0;
//     const char *buf = g_api->get_req_header_by_id(session,
//                       LSI_HDR_X_FORWARDED_PROTO, &valLen);
// 
//     if (valLen == 0 || buf == NULL)
//     {
//         return false;  // No X-Forwarded-Proto header found.
//     }
// 
//     StringPiece x_forwarded_proto = new StringPiece(buf, valLen);
// 
//     if (!STR_CASE_EQ_LITERAL(bufStr, "http") &&
//         !STR_CASE_EQ_LITERAL(bufStr, "https"))
//     {
//         LOG(WARNING) << "Unsupported X-Forwarded-Proto: " << x_forwarded_proto
//                      << " for URL " << url << " protocol not changed.";
//         return false;
//     }
// 
//     StringPiece url_sp(*url);
//     StringPiece::size_type colon_pos = url_sp.find(":");
// 
//     if (colon_pos == StringPiece::npos)
//     {
//         return false;  // URL appears to have no protocol; give up.
//     }
// 
// //
//     // Replace URL protocol with that specified in X-Forwarded-Proto.
//     *url = StrCat(x_forwarded_proto, url_sp.substr(colon_pos));
// 
//     return true;
// }

static bool IsPagespeedSubrequest(const char *ua,
                           int uaLen)
{
    if (ua && uaLen > 0)
    {
        if (memmem(ua, uaLen, kModPagespeedSubrequestUserAgent,
                   sizeof(kModPagespeedSubrequestUserAgent) - 1))
        {
            return true;
        }
    }

    return false;
}

static void BeaconHandlerHelper(PsMData *pMyData, lsi_session_t *session,
                         StringPiece &beacon_data)
{
    g_api->log(session, LSI_LOG_DEBUG,
               "[modpagespeed] BeaconHandlerHelper(): beacon[%zd] %.*s\n",
                beacon_data.size(), (int)beacon_data.size(), beacon_data.data());

    CHECK(pMyData->vhCtx != NULL);

    RequestContextPtr request_context(
        pMyData->vhCtx->serverContext->NewRequestContext(session));

    request_context->set_options(
        pMyData->vhCtx->serverContext->global_options()->ComputeHttpOptions());

    pMyData->vhCtx->serverContext->HandleBeacon(
        beacon_data,
        pMyData->request->userAgent,
        request_context);

    SetCacheControl(session, const_cast<char *>("max-age=0,no-cache"));
}

// Parses out query params from the request.
//isPost: 1, use both query param and post bosy, 0, use query param
static void QueryParamsHandler(lsi_session_t *session, AutoBuf *pBuf, int isPost)
{
    int iQSLen;
    const char *pQS = g_api->get_req_query_string(session, &iQSLen);

    if (iQSLen > 0)
        pBuf->append(pQS, iQSLen);
    char body[1024];
    int ret;
    bool bReqBodyStart = false;

    while ((ret = g_api->read_req_body(session, body, 1024)) > 0)
    {
        if (!bReqBodyStart)
        {
            pBuf->append( "&", 1);
            bReqBodyStart = true;
        }

        pBuf->append(body, ret);
    }
}


static int BeaconHandler(PsMData *pMyData, lsi_session_t *session)
{
    // Use query params.
    AutoBuf     buf;
    StringPiece query_param_beacon_data;
    int isPost = (pMyData->request->method == LSI_METHOD_POST);
    QueryParamsHandler(session, &buf, isPost);
    query_param_beacon_data.set(buf.begin(), buf.size());
    BeaconHandlerHelper(pMyData, session, query_param_beacon_data);
    pMyData->statusCode = (isPost ? 200 : 204);
    return 0;
}

int SimpleHandler(PsMData *pMyData, lsi_session_t *session,
                  LsServerContext *server_context,
                  REQ_ROUTE req_route)
{
    LsRewriteDriverFactory *factory =
        static_cast<LsRewriteDriverFactory *>(
            server_context->factory());
    LsMessageHandler *message_handler = factory->GetLsiMessageHandler();

    int uriLen = g_api->get_req_org_uri(session, NULL, 0);
    char *uri = new char[uriLen + 1];

    g_api->get_req_org_uri(session, uri, uriLen + 1);
    uri[uriLen] = 0x00;
    StringPiece request_uri_path = uri;//

    QueryParams query_params;

    query_params.ParseFromUrl(*pMyData->request->url);

    GoogleString output;
    StringWriter writer(&output);
    pMyData->statusCode = 200;
    HttpStatus::Code status = HttpStatus::kOK;
    ContentType content_type = kContentTypeHtml;
    StringPiece cache_control = HttpAttributes::kNoCache;
    const char *error_message = NULL;

    switch (req_route)
    {
    case REQ_ROUTE_STATIC:
        {
            StringPiece file_contents;

            if (!server_context->static_asset_manager()->GetAsset(
                    request_uri_path.substr(factory->static_asset_prefix().length()),
                    &file_contents, &content_type, &cache_control))
                return LS_FAIL;

            file_contents.CopyToString(&output);
            break;
        }

    case REQ_ROUTE_MESSAGE:
        {
            GoogleString log;
            StringWriter log_writer(&log);

            if (!message_handler->Dump(&log_writer))
            {
                writer.Write("Writing to pagespeed_message failed. \n"
                             "Please check if it's enabled in pagespeed.conf.\n",
                             message_handler);
            }
            else
                HtmlKeywords::WritePre(log, "", &writer, message_handler);

            break;
        }

    default:
        g_api->log(session, LSI_LOG_WARN,
                   "[modpagespeed] ps_simple_handler: unknown RequestRouting.\n");
        return LS_FAIL;
    }

    if (error_message != NULL)
    {
        pMyData->statusCode = HttpStatus::kNotFound;
        content_type = kContentTypeHtml;
        output = error_message;
    }


    pMyData->respHeaders = new ResponseHeaders;
    ResponseHeaders &response_headers = *pMyData->respHeaders;
    response_headers.SetStatusAndReason(status);
    response_headers.set_major_version(1);
    response_headers.set_minor_version(1);
    response_headers.Add(HttpAttributes::kContentType,
                         content_type.mime_type());


//     g_api->set_resp_header( session, LSI_RSPHDR_CONTENT_TYPE, NULL, 0, content_type.mime_type(),
//                             strlen( content_type.mime_type() ), LSI_HEADEROP_SET );

    // http://msdn.microsoft.com/en-us/library/ie/gg622941(v=vs.85).aspx
    // Script and styleSheet elements will reject responses with
    // incorrect MIME types if the server sends the response header
    // "X-Content-Type-Options: nosniff". This is a security feature
    // that helps prevent attacks based on MIME-type confusion.
    response_headers.Add("X-Content-Type-Options", "nosniff");
//     g_api->set_resp_header( session, -1, "X-Content-Type-Options", sizeof( "X-Content-Type-Options" ) - 1,
//                             "nosniff", 7, LSI_HEADEROP_SET );

    //TODO: add below
    int64 now_ms = factory->timer()->NowMs();
    response_headers.SetDate(now_ms);
    response_headers.SetLastModified(now_ms);
    response_headers.Add(HttpAttributes::kCacheControl, cache_control);
//     g_api->set_resp_header( session, -1, HttpAttributes::kCacheControl, strlen( HttpAttributes::kCacheControl ),
//                             cache_control.as_string().c_str(), cache_control.size(), LSI_HEADEROP_SET );

//   char* cache_control_s = string_piece_to_pool_string(r->pool, cache_control);
//   if (cache_control_s != NULL) {
    if (FindIgnoreCase(cache_control, "private") == StringPiece::npos)
        response_headers.Add(HttpAttributes::kEtag, "W/\"0\"");

    pMyData->sBuff.clear();
    pMyData->nBuffOffset = 0;
    pMyData->sBuff.append(output);

    return 0;
}


static RewriteDriver *CreateRewriteDriver(PsMData *pMyData, 
                                          lsi_session_t *session)
{
    LsPsVhCtx *vhCtx = pMyData->vhCtx;
    
    RewriteDriver *driver;
    
    RewriteOptions *custom_option = pMyData->request->options;
    g_api->log(session, LSI_LOG_DEBUG,
            "[%s] CreateRewriteDriver, custom_option: %s\n", ModuleName, 
            custom_option->OptionsToString().c_str());

    if (custom_option != vhCtx->options)
    //if (!custom_option->frozen())
    {
        custom_option = custom_option->Clone();
        custom_option->ComputeSignature();
        driver = vhCtx->serverContext->NewCustomRewriteDriver(
            custom_option, pMyData->request->request_context);
    } else {
        driver = vhCtx->serverContext->NewRewriteDriver(
                        pMyData->request->request_context);
    }
    
    driver->SetRequestHeaders(*pMyData->request->reqHeaders);
    return driver;
}


static void RegisterLsHandler(PsMData *pMyData, lsi_session_t *session, 
                              const char *LogMessage)
{
    pMyData->flags |= PSF_NO_HOOK;
    g_api->register_req_handler(session, &MNAME, 0);
    g_api->log(session, LSI_LOG_DEBUG,
            "[%s] RegisterLsHandler: %s\n", ModuleName, LogMessage);
}


static int StartRecordForInPlace(PsMData *pMyData, lsi_session_t *session)
{
    LsPsVhCtx *vhCtx = pMyData->vhCtx;
    LsPsReqCtx *ctx = pMyData->reqCtx;
    LsServerContext *server_context = vhCtx->serverContext;
    MessageHandler *message_handler = vhCtx->handler;
    if (ctx->driver == NULL)
        ctx->driver = CreateRewriteDriver(pMyData, session);
    const SystemRewriteOptions *options = SystemRewriteOptions::DynamicCast(
            ctx->driver->options());


    g_api->log(session, LSI_LOG_DEBUG,
                "[modpagespeed] new InPlaceResourceRecorder() for cache response\n");
    // This URL was not found in cache (neither the input resource nor
    // a ResourceNotCacheable entry) so we need to get it into cache
    // (or at least a note that it cannot be cached stored there).
    // We do that using an Apache output filter.
    ctx->recorder = new InPlaceResourceRecorder(
        pMyData->request->request_context,
        *(pMyData->request->urlStriped),
        ctx->driver->CacheFragment(),
        pMyData->request->reqHeaders->GetProperties(),
        options->ipro_max_response_bytes(),
        options->ipro_max_concurrent_recordings(),
        server_context->http_cache(),
        server_context->statistics(),
        message_handler);
//     // set in memory flag for in place_body_filter
//     r->filter_need_in_memory = 1;

    ctx->recorder->ConsiderResponseHeaders(
        InPlaceResourceRecorder::kFullHeaders, 
        pMyData->request->respHeaders);
    if (ctx->recorder->failed())
    {
        delete ctx->recorder;
        ctx->recorder = NULL;
        ctx->inPlace = false;
    }
    return 0;
}


static int BaseFetchHandler(PsMData *pMyData, lsi_session_t *session);
static int InPlaceBaseFetchDoneCb(evtcbhead_s *session_, long param, void *pParam)
{
    g_api->log((lsi_session_t *)session_, LSI_LOG_DEBUG,
               "[%s] InPlaceBaseFetchDoneCb(), session=%p.\n", ModuleName, 
               session_);
    
    if (!session_)
    {
        return -1;
    }

    lsi_session_t *session = (lsi_session_t *) session_;
    PsMData *pMyData = (PsMData *) g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);
    if (!pMyData)
        return 0;

    //pMyData->ctx->session can be updated to NULL when httpsession releaseresources
//     if (pMyData->ctx->session != session_)
//     {
//         g_api->free_module_data(session, &MNAME, LSI_DATA_HTTP);
//         return 0;
//     }
    LsPsReqCtx *ctx = pMyData->reqCtx;

    assert(ctx->inPlace);
    assert(ctx->baseFetch);
//     if (!pMyData->reqCtx->fetchDone)
//         BaseFetchHandler(pMyData, session);
//     else
//     {
//         CHECK(0);//should NEVER BE HERE since call only once
//         pMyData->reqCtx->baseFetch->CollectAccumulatedWrites(session);
//     }
    
 
    g_api->log(session, LSI_LOG_DEBUG,
               "[modpagespeed] in place check base fetch resp header: %s\n",
               pMyData->request->urlString.c_str());

    int status_code = ctx->baseFetch->response_headers()->status_code();

    bool status_ok = (status_code != 0) && (status_code < 400);

    LsPsVhCtx *vhCtx = pMyData->vhCtx;
    LsServerContext *server_context = vhCtx->serverContext;

    // The URL we use for cache key is a bit different since it may
    // have PageSpeed query params removed.
    GoogleString &cache_url = *(pMyData->request->urlStriped);

    // continue process
    if (status_ok)
    {
        g_api->log(session, LSI_LOG_DEBUG,
            "[modpagespeed] serve resource in-place "
            "because URL is in cache: %s, status: %d\n",
            cache_url.c_str(), status_code);

        pMyData->statusCode = status_code;

        ctx->inPlace = false;
        server_context->rewrite_stats()->ipro_served()->Add(1);
        RegisterLsHandler(pMyData, session, "serve in-place fetch result");
    }
    else if (status_code == CacheUrlAsyncFetcher::kNotInCacheStatus)
    {
        server_context->rewrite_stats()->ipro_not_in_cache()->Add(1);
        g_api->log(session, LSI_LOG_DEBUG,
                   "[modpagespeed] Could not rewrite resource in-place "
                   "because URL is not in cache: %s\n",
                    cache_url.c_str());
        //Need to setup recorder at response header done hookpoint
    }
    else
    {
        ctx->inPlace = false;
        server_context->rewrite_stats()->ipro_not_rewritable()->Add(1);
        g_api->log(session, LSI_LOG_DEBUG,
                   "Could not rewrite resource in-place: %s\n",
                   pMyData->request->urlString.c_str());
    }
    
    //ctx->driver->Cleanup();
    //ctx->driver = NULL;
    // enable html_rewrite

    // re init ctx
    //ctx->fetchDone = false;
    if (ctx->fetchDone)
    {
        g_api->log(session, LSI_LOG_DEBUG, "InPlaceBaseFetch is done, ReleaseBaseFetch()\n");
        pMyData->ReleaseBaseFetch();
        ctx->fetchDone = false;
    }
    g_api->create_session_resume_event(session, &MNAME);
    g_api->set_handler_write_state(session, 1);
    return 0;
}



static int StartFetchInPlaceResource(PsMData *pMyData,
                    lsi_session_t *session)
{
    LsPsReqCtx *ctx = pMyData->reqCtx;
    CreateBaseFetch(pMyData, session, 
                    pMyData->request->request_context,
                    pMyData->request->reqHeaders, 
                    kIproLookup,
                    InPlaceBaseFetchDoneCb
                   );
    
    // Do not store driver in request_context, it's not safe.
    RewriteDriver *driver = CreateRewriteDriver(pMyData, session);
    
    ctx->driver = driver;

    g_api->log(session, LSI_LOG_DEBUG,
                "[modpagespeed] Trying to serve rewritten resource in-place: %s\n",
                pMyData->request->urlStriped->c_str());

    ctx->inPlace = true;
    ctx->baseFetch->SetIproLookup(true);
    ctx->driver->FetchInPlaceResource(
        *(pMyData->request->url), false /* proxy_mode */, ctx->baseFetch);

    return 1;
}


static int StartFetchProxy(PsMData *pMyData,
                    lsi_session_t *session, 
                    BaseFetchType type,
                    GoogleString &url_string,
                    bool set_callback)
{
    LsPsReqCtx *ctx = pMyData->reqCtx;
    LsPsVhCtx *vhCtx = pMyData->vhCtx;

    CreateBaseFetch(pMyData, session, 
                    pMyData->request->request_context,
                    pMyData->request->reqHeaders, 
                    type, BaseFetchDoneCb);
    // Do not store driver in request_context, it's not safe.
    RewriteDriver *driver = CreateRewriteDriver(pMyData, session);

    driver->set_pagespeed_query_params(
        pMyData->request->pagespeed_query_params);
    driver->set_pagespeed_option_cookies(
        pMyData->request->pagespeed_option_cookies);

    ProxyFetchPropertyCallbackCollector *property_callback = NULL;
    if (set_callback)
        property_callback = ProxyFetchFactory::InitiatePropertyCacheLookup(
            0 /* is_resource_fetch */,
            *(pMyData->request->url),
            vhCtx->serverContext,
            pMyData->request->options,
            ctx->baseFetch,
            false);

    ctx->proxyFetch = vhCtx->proxyFetchFactory->CreateNewProxyFetch(
                            url_string, ctx->baseFetch, driver,
                            property_callback,
                            NULL /* original_content_fetch */);

//    g_api->log(NULL, LSI_LOG_DEBUG, "[modpagespeed] Create ProxyFetch  %s.\n",
//                url_string.c_str());
    return 0;
}


static int StartFetchHtmlRewrite(PsMData *pMyData, lsi_session_t *session)
{
    LsPsReqCtx *ctx = pMyData->reqCtx;
    GoogleString &url_string = *(pMyData->request->urlStriped);

    StartFetchProxy(pMyData, session, kHtmlTransform, url_string, true);
    ctx->proxyFetch->set_trusted_input(true);

    g_api->log(NULL, LSI_LOG_DEBUG, "[modpagespeed] Create HtmlRewrite ProxyFetch %s.\n",
                url_string.c_str());
    return 0;
}


static int StartAdminHandler(PsMData *pMyData, lsi_session_t *session,
                             REQ_ROUTE response_category)
{
    LsPsReqCtx *ctx = pMyData->reqCtx;
    LsPsVhCtx *vhCtx = pMyData->vhCtx;

    CreateBaseFetch(pMyData, session, pMyData->request->request_context,
                    pMyData->request->reqHeaders, kAdminPage, BaseFetchDoneCb);
    QueryParams query_params;
    query_params.ParseFromUrl(*(pMyData->request->url));

    PosixTimer timer;
    int64 now_ms = timer.NowMs();
    ctx->baseFetch->response_headers()->SetDateAndCaching(
        now_ms, 0 /* max-age */, ", no-cache");

    if (response_category == REQ_ROUTE_STATISTICS ||
        response_category == REQ_ROUTE_GLOBAL_STATS)
    {
        vhCtx->serverContext->StatisticsPage(
            response_category == REQ_ROUTE_GLOBAL_STATS,
            query_params,
            vhCtx->serverContext->Config(),
            ctx->baseFetch);
    }
    else if (response_category == REQ_ROUTE_CONSOLE)
    {
        vhCtx->serverContext->ConsoleHandler(
            *vhCtx->serverContext->Config(),
            AdminSite::kStatistics,
            query_params,
            ctx->baseFetch);
    }
    else if (response_category == REQ_ROUTE_ADMIN ||
                response_category == REQ_ROUTE_GLOBAL_ADMIN)
    {
        vhCtx->serverContext->AdminPage(
            response_category == REQ_ROUTE_GLOBAL_ADMIN,
            *(pMyData->request->url),
            query_params,
            vhCtx->serverContext->Config(),
            ctx->baseFetch);
    }
    else if (response_category == REQ_ROUTE_PURGE)
    {
        AdminSite *admin_site = vhCtx->serverContext->admin_site();
        admin_site->PurgeHandler(*(pMyData->request->urlStriped),
                                 vhCtx->serverContext->cache_path(),
                                 ctx->baseFetch);
    }
    else
        CHECK(false);

    return 1;

}


static LsPsReqCtx *createLsPsReqCtx(PsMData *pMyData)
{
    LsPsReqCtx *ctx;
    RequestHeaders *request_headers = pMyData->request->reqHeaders;
    RewriteOptions *options = pMyData->request->options;
    // create request ctx
    ctx = new LsPsReqCtx;

    //ctx->session = session;
    //session->setBackRefPtr(NULL, 1);
    ctx->htmlRewrite = false;
    ctx->inPlace = false;
    ctx->proxyFetch = NULL;
    ctx->baseFetch = NULL;
    ctx->fetchDone = false;
    ctx->driver = NULL;
    ctx->recorder = NULL;
    //ctx->pagespeed_connection = NULL;
    ctx->preserveCachingHeaders = kDontPreserveHeaders;

    if (!options->modify_caching_headers())
        ctx->preserveCachingHeaders = kPreserveAllCachingHeaders;
    else if (!options->IsDownstreamCacheIntegrationEnabled())
    {
        // Downstream cache integration is not enabled. Disable original
        // Cache-Control headers.
        ctx->preserveCachingHeaders = kDontPreserveHeaders;
    }
    else if ((pMyData->flags & (PSF_IS_PS_RES | PSF_IS_ADMIN)) == 0)
    {
        ctx->preserveCachingHeaders = kDontPreserveHeaders;//kPreserveOnlyCacheControl;
        // Downstream cache integration is enabled. If a rebeaconing key has been
        // configured and there is a ShouldBeacon header with the correct key,
        // disable original Cache-Control headers so that the instrumented page is
        // served out with no-cache.
        StringPiece should_beacon(request_headers->Lookup1(kPsaShouldBeacon));

        if (options->MatchesDownstreamCacheRebeaconingKey(should_beacon))
            ctx->preserveCachingHeaders = kDontPreserveHeaders;
    }

    ctx->recorder = NULL;
    //pMyData->urlString = url_string;
    pMyData->reqCtx = ctx;
    //ctx->location_field_set = false;
    return ctx;
}



static int StartFetchPageSpeedResource(PsMData *pMyData, lsi_session_t *session)
{
    g_api->log(session, LSI_LOG_DEBUG,
               "[modpagespeed] StartFetchPageSpeedResource() begin: %s\n",
               pMyData->request->urlString.c_str());
    LsPsVhCtx *vhCtx = pMyData->vhCtx;
    LsPsReqCtx *ctx = createLsPsReqCtx(pMyData);
    const GoogleUrl &url = *(pMyData->request->url);
    RequestHeaders *request_headers = pMyData->request->reqHeaders;

    CreateBaseFetch(pMyData, session, pMyData->request->request_context,
                    request_headers, kPageSpeedResource, BaseFetchDoneCb);
    ResourceFetch::Start(
        url,
        NULL,
        false /* using_spdy */, vhCtx->serverContext, ctx->baseFetch);

    return 1;
}


static int StartPageSpeedProxyFetch(PsMData *pMyData, lsi_session_t *session)
{
    bool is_proxy = false;
    GoogleString mapped_url;
    GoogleString host_header;
    const GoogleUrl &url = *(pMyData->request->url);

    RewriteOptions *options = pMyData->request->options;
    if (options->domain_lawyer()->MapOriginUrl(
            url, &mapped_url, &host_header, &is_proxy) && is_proxy) {
        StartFetchProxy(pMyData, session, kPageSpeedProxy, 
                        mapped_url, false);
        return 1;
    }
    return 0;
}



// Send each buffer in the chain to the proxyFetch for optimization.
// Eventually it will make it's way, optimized, to base_fetch.
// return false for error
static bool SendToPagespeed(PsMData *pMyData, lsi_param_t *rec,
                     LsPsReqCtx *ctx)
{
    if (ctx->proxyFetch == NULL)
        return false;
    g_api->log(rec->session, LSI_LOG_DEBUG,
               "[%s] SendToPagespeed() bytes: %d\n",
               ModuleName, rec->len1);

    if (rec->len1 > 0) {
        ctx->proxyFetch->Write(
            StringPiece((const char *) rec->ptr1, rec->len1),
            pMyData->vhCtx->handler);
    }
    
    if (rec->flag_in & LSI_CBFI_EOF)
    {
        ctx->proxyFetch->Done(true /* success */);
        ctx->proxyFetch = NULL;  // ProxyFetch deletes itself on Done().
    }
    else
        ctx->proxyFetch->Flush(pMyData->vhCtx->handler);
    return true;
}

 

static void DropUnwantedRespHeaders(lsi_session_t *session)
{
    g_api->remove_resp_header(session, LSI_RSPHDR_CONTENT_LENGTH, NULL, 0);
    g_api->remove_resp_header(session, LSI_RSPHDR_ACCEPT_RANGES, NULL, 0);
}

static int HtmlRewriteFixHeadersFilter(PsMData *pMyData,
                                lsi_session_t *session, LsPsReqCtx *ctx)
{
    if (ctx == NULL || !ctx->htmlRewrite
        || ctx->preserveCachingHeaders == kPreserveAllCachingHeaders)
        return 0;

    if (ctx->preserveCachingHeaders == kDontPreserveHeaders)
    {
        struct iovec iov[1] = {{NULL, 0}};
        int iovCount = g_api->get_resp_header(session, LSI_RSPHDR_CACHE_CTRL,
                                              NULL, 0, iov, 1);
        if (iovCount)
            SetLimitCacheControl(session, (char *) iov[0].iov_base,
                                 iov[0].iov_len);

        // Don't cache html.  See mod_instaweb:instaweb_fix_headers_filter.
//         LsiCachingHeaders caching_headers(session);
//         SetCacheControl(session,(char *) caching_headers.GenerateDisabledCacheControl().c_str());
    }

    // Pagespeed html doesn't need etags: it should never be cached.
    g_api->remove_resp_header(session, LSI_RSPHDR_ETAG, NULL, 0);

    // An html page may change without the underlying file changing, because of
    // how resources are included.  Pagespeed adds cache control headers for
    // resources instead of using the last modified header.
    g_api->remove_resp_header(session, LSI_RSPHDR_LAST_MODIFIED, NULL, 0);

    g_api->set_resp_header(session, -1, PAGESPEED_RESP_HEADER, 
                           sizeof(PAGESPEED_RESP_HEADER) - 1,
                           MODPAGESPEEDVERSION, sizeof(MODPAGESPEEDVERSION) -1,
                           LSI_HEADEROP_SET);
//   // Clear expires
//   if (r->headers_out.expires) {
//     r->headers_out.expires->hash = 0;
//     r->headers_out.expires = NULL;
//   }

    return 0;
}

static int InPlaceCheckRespHeaderFilter(PsMData *pMyData, lsi_session_t *session,
                             LsPsReqCtx *ctx)
{
    if (ctx->recorder != NULL)
    {
        g_api->log(session, LSI_LOG_DEBUG,
                   "[modpagespeed] in place check header filter recording: %s\n",
                   pMyData->request->urlString.c_str());

        CHECK(!ctx->inPlace);

        // The recorder will do this checking, so pass it the headers.
        ctx->recorder->ConsiderResponseHeaders(
            InPlaceResourceRecorder::kPreliminaryHeaders, 
            pMyData->request->respHeaders);
        return 0;
    }

    if (!ctx->inPlace)
        return 0;

    g_api->log(session, LSI_LOG_DEBUG,
               "[modpagespeed] in place check header filter initial: %s\n",
               pMyData->request->urlString.c_str());

    int status_code = ctx->baseFetch->response_headers()->status_code();

    bool status_ok = (status_code != 0) && (status_code < 400);

    LsPsVhCtx *vhCtx = pMyData->vhCtx;
    LsServerContext *server_context = vhCtx->serverContext;
    //MessageHandler *message_handler = vhCtx->handler;
    // The URL we use for cache key is a bit different since it may
    // have PageSpeed query params removed.
    GoogleString &cache_url = *(pMyData->request->urlStriped);

    // continue process
    if (status_ok)
    {
        ctx->inPlace = false;

        server_context->rewrite_stats()->ipro_served()->Add(1);
        g_api->log(session, LSI_LOG_DEBUG,
                   "[modpagespeed] Serving rewritten resource in-place: %s\n",
                   pMyData->request->urlString.c_str());

        return 0;
    }

    if (status_code == CacheUrlAsyncFetcher::kNotInCacheStatus)
    {
        server_context->rewrite_stats()->ipro_not_in_cache()->Add(1);
        g_api->log(session, LSI_LOG_DEBUG,
                   "[modpagespeed] Could not rewrite resource in-place "
                   "because URL is not in cache: %s\n",
                    cache_url.c_str());
        
        StartRecordForInPlace(pMyData, session);
    }
    else
    {
        server_context->rewrite_stats()->ipro_not_rewritable()->Add(1);
        g_api->log(session, LSI_LOG_DEBUG,
                   "Could not rewrite resource in-place: %s\n",
                   pMyData->request->urlString.c_str());
    }

    ctx->driver->Cleanup();
    ctx->driver = NULL;
    // enable html_rewrite
    ctx->htmlRewrite = true;
    ctx->inPlace = false;

    // re init ctx
    ctx->fetchDone = false;

    g_api->log(session, LSI_LOG_DEBUG, "ReleaseBaseFetch()\n");
    pMyData->ReleaseBaseFetch();

    return LS_FAIL;
}

static int InPlaceBodyFilter(PsMData *pMyData, lsi_param_t *rec,
                      LsPsReqCtx *ctx, StringPiece &contents, int length)
{
    g_api->log(rec->session, LSI_LOG_DEBUG,
               "[modpagespeed] ps in place body filter: %s, bufLen=%d\n",
               pMyData->request->urlString.c_str(), length);

    InPlaceResourceRecorder *recorder = ctx->recorder;
    if (length > 0)
    {
        recorder->Write(contents, recorder->handler());
    }

    if (rec->flag_in & LSI_CBFI_FLUSH)
        recorder->Flush(recorder->handler());

    if (rec->flag_in & LSI_CBFI_EOF || recorder->failed())
    {
        recorder->Flush(recorder->handler());
        ctx->recorder->DoneAndSetHeaders(
            pMyData->request->respHeaders, true);
        ctx->recorder = NULL;
    }

    return 0;
}

//Comment: return value different with ent
static int sendRespBody(lsi_param_t *rec)
{
    LsPsVhCtx *vhCtx;
    LsPsReqCtx *ctx;
    PsMData *pMyData = (PsMData *) g_api->get_module_data(rec->session,
                       &MNAME, LSI_DATA_HTTP);
    /**
     * Wrong case, will not deal with it
     */
    if (pMyData == NULL || (vhCtx = pMyData->vhCtx) == NULL
        || (ctx = pMyData->reqCtx) == NULL)
        return g_api->stream_write_next(rec, (const char *) rec->ptr1,
                                        rec->len1);


    g_api->log(rec->session, LSI_LOG_DEBUG,
               "[%s] sendRespBody() flag_in %d, buffer in: %d, "
               "html rewrite: %d, doneCalled: %d, baseFetch: %p, recorder: %p\n",
               ModuleName, rec->flag_in, rec->len1, ctx->htmlRewrite, 
               pMyData->doneCalled, ctx->baseFetch, ctx->recorder);

    if (pMyData->flags & PSF_NO_HOOK)
        return g_api->stream_write_next(rec, (const char *) rec->ptr1,
                                        rec->len1);

    int ret = rec->len1;
    StringPiece contents;

    if (ctx->htmlRewrite && !pMyData->doneCalled)
    {
        if (rec->len1 > 0 ||  rec->flag_in)
        {
            SendToPagespeed(pMyData, rec, ctx);
        }
    }

    if (pMyData->sBuff.size() - pMyData->nBuffOffset == 0 &&
        (!ctx->htmlRewrite || ctx->baseFetch == NULL))
    {
        if (rec->len1 >= 0)
        {
            ret = g_api->stream_write_next(rec, (const char *) rec->ptr1, rec->len1);
            if (ret >= 0)
            {
                if (ctx->recorder)
                {
                    contents = StringPiece((char *) rec->ptr1, rec->len1);
                    InPlaceBodyFilter(pMyData, rec, ctx, contents, rec->len1);
                }
            }
        }
        return ret;
    }


    int len;
    int writtenTotal = 0;
    while ((len = pMyData->sBuff.size() - pMyData->nBuffOffset) > 0)
    {
        const char *buf = pMyData->sBuff.c_str() + pMyData->nBuffOffset;
        if (pMyData->doneCalled)
            rec->flag_in = LSI_CBFI_EOF;
        else
            rec->flag_in = LSI_CBFI_FLUSH;
        
        int written = g_api->stream_write_next(rec, buf, len);
        if (written > 0)
        {
            if (ctx->recorder)
            {
                contents = StringPiece(buf, written);
                InPlaceBodyFilter(pMyData, rec, ctx, contents, written);
            }
            pMyData->nBuffOffset += written;
            writtenTotal += written;
        }
        else if (written < 0)
            return LS_FAIL;
        else
            break;
    }

    if (!pMyData->doneCalled || pMyData->sBuff.size() - pMyData->nBuffOffset > 0)
    {
        if (rec->flag_out)
            *rec->flag_out |= LSI_CBFO_BUFFERED;
    }
    
    if (pMyData->doneCalled && (pMyData->flags & PSF_END_RESP) == 0)
    {
        pMyData->flags |= PSF_END_RESP;
        g_api->end_resp(rec->session);
    }


    if (*rec->flag_out && rec->flag_in == LSI_CBFI_EOF)
        g_api->set_handler_write_state(rec->session, 0);


    g_api->log(rec->session, LSI_LOG_DEBUG,
               "[%s] sendRespBody() flag_in %d, flag out %d, done_called %d, Accumulated %d, write to next %d, buffer data written %d.\n",
               ModuleName, rec->flag_in, *rec->flag_out, pMyData->doneCalled,
               rec->len1, ret, writtenTotal);
    return ret; //Must use updated buffer.

}


static void UpdateEtag(lsi_session_t *session)
{
    struct iovec iov[1] = {{NULL, 0}};
    int iovCount = g_api->get_resp_header(session, -1, kInternalEtagName,
                                          strlen(kInternalEtagName), iov, 1);

    if (iovCount == 1)
    {
        g_api->remove_resp_header(session, -1, kInternalEtagName,
                                  strlen(kInternalEtagName));
        g_api->set_resp_header(session, LSI_RSPHDR_ETAG, NULL, 0,
                               (const char *) iov[0].iov_base,
                               iov[0].iov_len, LSI_HEADEROP_SET);
//         //If etag not PAGESPEED style, meas not optimized, so not cahce it
//         if (strncasecmp((const char *) iov[0].iov_base, "W/", 2) == 0)
//             g_api->set_req_env(session, "cache-control", 13, "no-cache", 8);
    }
}

//TODO: comment out seems to be useless
// int ps_base_fetch_filter(PsMData *pMyData, lsi_param_t *rec, ps_request_ctx_t* ctx)
// {
//   if (ctx == NULL || ctx->base_fetch == NULL)
//     return 0;
//
//   g_api->log(rec->_session, LSI_LOG_DEBUG,
//                "http pagespeed write filter: %s", ctx->url_string.c_str());
//
//   return 0;
// }


//Check the resp header and set the htmlWrite
static int HtmlRewriteHeaderFilter(PsMData *pMyData, lsi_session_t *session,
                            LsPsReqCtx *ctx, LsPsVhCtx *vhCtx)
{
    // Poll for cache flush on every request (polls are rate-limited).
    //vhCtx->server_context->FlushCacheIfNecessary();

    if (ctx->htmlRewrite == false)
        return 0;

    if (!IsHtmlLikeContent(pMyData, session))
    {
        ctx->htmlRewrite = false;
        return 0;
    }

    g_api->log(session, LSI_LOG_DEBUG,
               "[modpagespeed] HtmlRewriteHeaderFilter() handle resource \"%s\"\n",
               pMyData->request->urlString.c_str());


    pMyData->ReleaseBaseFetch();
    int rc = StartFetchHtmlRewrite(pMyData, session);

    if (rc != 0)
    {
        ctx->htmlRewrite = false;
        return 0;
    }

    //FIXME: not sure should drop those header now yet
    DropUnwantedRespHeaders(session);
//     CopyRespHeadersFromServer(session,
//                              ctx->baseFetch->response_headers());
    
    //This is more efficient, just use the copy we already have.
    ctx->baseFetch->response_headers()->CopyFrom(
        *(pMyData->request->respHeaders));

    return 0;
}

static int rcvdRespHeaderHook(lsi_param_t *rec)
{
    lsi_session_t *session = (lsi_session_t *)rec->session;
    LsPsVhCtx *vhCtx;
    PsMData *pMyData = (PsMData *) g_api->get_module_data(session,
                       &MNAME, LSI_DATA_HTTP);

    if (pMyData == NULL || (vhCtx = pMyData->vhCtx) == NULL)
        //|| (ctx = pMyData->reqCtx) == NULL)
        return LS_FAIL;

    if ((pMyData->flags & (PSF_NO_HOOK|PSF_IS_SUBREQ)) 
        || pMyData->state == PS_STATE_RECV_RESP_HEADER)
        return 0;

    pMyData->state = PS_STATE_RECV_RESP_HEADER;
    
    LsPsReqCtx *ctx = pMyData->reqCtx;
    struct iovec iov;
    int count = g_api->get_resp_header(session, LSI_RSPHDR_CONTENT_TYPE, 
                                       NULL, 0, &iov, 1);
    if (count <= 0)
        return 0;
    
    StringPiece ctHeader((const char *)iov.iov_base, iov.iov_len);
    const ContentType* content_type = MimeTypeToContentType(ctHeader);
    if (content_type == NULL)
        return 0;
    
    int in_place = false;
    int html_rewrite = false;
    if (content_type->IsImage() || content_type->IsCss() 
        || content_type->IsJs()) 
        in_place = true;
    else if (content_type->IsHtmlLike())
        html_rewrite = true;
    else
        return 0;
    
    UpdateEtag(session);

    LsPsReq * pReq = pMyData->request;
    pReq->respHeaders = new ResponseHeaders();
    CopyRespHeadersFromServer(session, pReq->respHeaders);

    RewriteQuery rewrite_query;

    if (!vhCtx->serverContext->GetQueryOptions(
            pReq->request_context, pReq->options, 
            pReq->url, NULL, pReq->respHeaders, &rewrite_query))
    {
        // Failed to parse query params or request headers.  Treat this as if there
        // were no query params given.
        g_api->log(session, LSI_LOG_ERROR,
                   "ps_route request: parsing response headers failed.\n");
    }

    RewriteOptions *resp_options = rewrite_query.ReleaseOptions();
    
    bool have_resp_options = resp_options != NULL;

    RewriteOptions *options;
    // Modify our options in response to request options if specified.
    if (have_resp_options)
    {
        if (!resp_options->enabled())
        {
            delete resp_options;
            return 0;
        }

        options = pReq->options->Clone();
        options->Merge(*resp_options);
        delete resp_options;
        resp_options = NULL;

        if (!options->enabled())
            return 0;

        if (pMyData->flags & PSF_OPT_OVERRIDE)
            delete pReq->options;
        else
            pMyData->flags |= PSF_OPT_OVERRIDE;
        pReq->options = options;

        pReq->request_context->set_options(
            options->ComputeHttpOptions());
    }

    if (!pReq->options->enabled())
        return 0;
    
    if (ctx == NULL)
        ctx = createLsPsReqCtx(pMyData);

    //FIXME: may not call this here, mix logic for InPlace response header 
    // processing, check base fetch result, to do in palce or not should be 
    // processed in the baseFetch callback. 
    // record original response header should be in rcvdRespHeader. 
    
    InPlaceCheckRespHeaderFilter(pMyData, session, ctx);
//     if (in_place)
//         StartRecordForInPlace(pMyData, session);
    if (ctx->driver)
    {
        ctx->driver->Cleanup();
        ctx->driver = NULL;
    }
    // enable html_rewrite
    ctx->inPlace = false;

    if (html_rewrite)
    {
        ctx->htmlRewrite = true;
        HtmlRewriteHeaderFilter(pMyData, session, ctx, vhCtx);
    }

    HtmlRewriteFixHeadersFilter(pMyData, (lsi_session_t *)session, ctx);
    return 0;
}


// Set us up for processing a request.  Creates a request context and determines
// which handler should deal with the request.
static REQ_ROUTE RouteRequest(PsMData *pMyData,
                                      lsi_session_t  *session, bool is_resource_fetch)
{
    LsPsVhCtx *vhCtx = pMyData->vhCtx;

    if (pMyData->request->url->PathSansLeaf() 
                == dynamic_cast<LsRewriteDriverFactory *>(
                    vhCtx->serverContext->factory())->static_asset_prefix())
        return REQ_ROUTE_STATIC;
    const LsRewriteOptions *global_options = vhCtx->serverContext->Config();
    StringPiece path = pMyData->request->url->PathSansQuery();

    if (StringCaseEqual(path, global_options->GetStatisticsPath()))
        return REQ_ROUTE_STATISTICS;
    else if (StringCaseEqual(path, global_options->GetGlobalStatisticsPath()))
        return REQ_ROUTE_GLOBAL_STATS;
    else if (StringCaseEqual(path, global_options->GetConsolePath()))
        return REQ_ROUTE_CONSOLE;
    else if (StringCaseEqual(path, global_options->GetMessagesPath()))
        return REQ_ROUTE_MESSAGE;
    else if ( // The admin handlers get everything under a path (/path/*) while
        // all the other handlers only get exact matches (/path).  So match
        // all paths starting with the handler path.
        !global_options->GetAdminPath().empty() &&
        StringCaseStartsWith(path, global_options->GetAdminPath()))
        return REQ_ROUTE_ADMIN;
    else if (!global_options->GetGlobalAdminPath().empty() &&
             StringCaseStartsWith(path, global_options->GetGlobalAdminPath()))
        return REQ_ROUTE_GLOBAL_ADMIN;
    else if (global_options->enable_cache_purge() &&
             !global_options->purge_method().empty() &&
             pMyData->request->method == LSI_METHOD_PURGE)
        return REQ_ROUTE_PURGE;

    const GoogleString *beacon_url;

    if (IsHttps(session))
        beacon_url = & (global_options->beacon_url().https);
    else
        beacon_url = & (global_options->beacon_url().http);

    if (pMyData->request->url->PathSansQuery() == StringPiece(*beacon_url))
        return REQ_ROUTE_BEACON;

    RewriteOptions *options = pMyData->request->options;
    if (options->in_place_rewriting_enabled()
        && options->enabled()
        && options->IsAllowed(pMyData->request->url->Spec()))
    {
        return REQ_ROUTE_IN_PLACE;
    }
    return REQ_ROUTE_DISABLED;
}


static LsPsReq * CreateLsPsReq(lsi_session_t *session, 
                               LsPsVhCtx *vhCtx, RewriteOptions *pConfig)
{
    LsPsReq *req = new LsPsReq();
    
    DetermineUrl((lsi_session_t *)session, req->urlString);
    //assert(pMyData->urlString == url_string);
    
    g_api->log(session, LSI_LOG_DEBUG,
               "[modpagespeed] CreateLsPsReq() for: %s\n",
               req->urlString.c_str());
    
    req->url = new GoogleUrl(req->urlString);
    if (!req->url->IsWebValid())
    {
        g_api->log(session, LSI_LOG_DEBUG, "[modpagespeed] invalid url\n");
        delete req;
        return NULL;
    }

    req->reqHeaders = new RequestHeaders();
    CopyReqHeadersFromServer(session, req->reqHeaders);
    
//     if (vhCtx->serverContext->global_options()->respect_x_forwarded_proto())
//     {
//         bool modified_url = ApplyXForwardedProto(session, &url_string);
// 
//         if (modified_url)
//         {
//             url.Reset(url_string);
//             CHECK(url.IsWebValid()) << "The output of ps_apply_x_forwarded_proto"
//                                     << " should always be a valid url because it only"
//                                     << " changes the scheme between http and https.";
//         }
//     }
    
    RequestContextPtr request_context(
        vhCtx->serverContext->NewRequestContext(session));

    RewriteOptions *pReqConfig = NULL;
    //Diffirent from google code, here the option is always inherit from the context, and it should never be NULL
    if (!DetermineOptions(session, req, pConfig,
                          &pReqConfig, request_context, vhCtx, 
                          false))
    {
        delete req;
        return NULL;
    }
    req->options = pReqConfig;

    request_context->set_options(pReqConfig->ComputeHttpOptions());
    req->request_context = request_context;

    if (req->pagespeed_query_params.size() != 0)
    {
        // ps_determine_options modified url, removing any ModPagespeedFoo=Bar query
        // parameters.  Keep url_string in sync with url.
        req->urlStriped = new GoogleString();
        req->url->Spec().CopyToString(req->urlStriped);
    }
    else
        req->urlStriped = &req->urlString;
    
    return req;
}

/***
 * RcvdReqHeaderHook do test if need to set the UACode to hashTable
 * And setup ModuleData
 * 
 */
static int RcvdReqHeaderHook(lsi_param_t *rec)
{
    lsi_session_t *session = (lsi_session_t *)rec->session;
    g_api->log(session, LSI_LOG_DEBUG, "[%s] RcvdReqHeaderHook().\n",
               ModuleName);

    LSI_REQ_METHOD method = g_api->get_req_method(session);
    if (method != LSI_METHOD_GET && method != LSI_METHOD_POST 
        && method != LSI_METHOD_PURGE && method != LSI_METHOD_HEAD)
    {
        g_api->log(session, LSI_LOG_DEBUG,
                   "[%s] RcvdReqHeaderHook, skip method %d.\n",
                   ModuleName, (int)method);
        return LSI_OK;
    }

    //init the VHost data
    LsPsVhCtx *vhCtx = (LsPsVhCtx *) g_api->get_module_data(
                              session, &MNAME, LSI_DATA_VHOST);

    if (vhCtx == NULL || vhCtx->serverContext == NULL)
    {
        //NOTE: add code to create need data structure on demand.
        // too late, need to do it earlier, otherwise, the directory level 
        // configuration wont be parased
        vhCtx = initVhostContext(g_api->get_req_vhost(session));
    }
    if (!vhCtx || vhCtx->serverContext->global_options()->unplugged())
    {
        g_api->log(session, LSI_LOG_DEBUG,
                "[%s] pagespeed is unplugged.\n",
                ModuleName);
        return LSI_OK;
    }
    
    
    RewriteOptions *pSessConfig = (RewriteOptions *) g_api->get_config(
                                     session, &MNAME);
    if (!pSessConfig)
    {
        g_api->log(session, LSI_LOG_DEBUG,
                   "[%s] RcvdReqHeaderHook, configuration is not available.\n",
                   ModuleName);
        return LSI_OK;
    }
    
    
    LsPsReq *req = CreateLsPsReq(session, vhCtx, pSessConfig);
    if (!req)
    {
        g_api->log(session, LSI_LOG_DEBUG,
                   "[%s] RcvdReqHeaderHook, CreateLsPsReq() failed.\n",
                   ModuleName);
        return LSI_OK;
    }
    
    
    int uaLen;
    const char * pUA = g_api->get_req_header_by_id(session,
                         LSI_HDR_USERAGENT, &uaLen);
    req->method = method;
    req->userAgent = StringPiece(pUA, uaLen);
    
    bool pagespeed_resource = vhCtx->serverContext->IsPagespeedResource(
        *req->url);
    
    if (!req->options->enabled() && !pagespeed_resource)
    {
        // Pagespeed is off, not enabled via query params or request headers.
        // Wait for response header phase to make the final decision.
        return LSI_OK;
    }
    
    //FOR SUBREQUEST, NEED TO SET
    if (pUA && uaLen > 0)
    {
        char *ua = strndup(pUA, uaLen);
        char sHex[15] = {'v', 'a', 'r', 'y', '=', };
        char *p = g_api->get_ua_code(ua);
        if (p)
            strcpy(sHex + 5, p);
        else
        {
            snprintf(sHex + 5, 8, "%02X",
                LsUAMatcher::getInstance().getUaCode(ua));
            g_api->set_ua_code(ua, sHex + 5);
        }
        g_api->set_req_env(rec->session, "cache-control", 13, sHex, strlen(sHex));
        free(ua);
    }
    
    
    if (IsPagespeedSubrequest(pUA, uaLen))
        return LSI_OK;
    
    
    //If URI_MAP called before, should return
    PsMData *pMyData = (PsMData *) g_api->get_module_data(session,
                       &MNAME, LSI_DATA_HTTP);

    if (pMyData)
    {
        if (pMyData->flags & PSF_NO_HOOK || pMyData->state == PS_STATE_RECV_REQ)
            return LSI_OK;
        g_api->free_module_data(session, &MNAME, LSI_DATA_HTTP, ReleaseMydata);
    }

    
    pMyData = new PsMData;
    if (pMyData == NULL)
    {
        g_api->log(session, LSI_LOG_DEBUG,
                   "[%s] RcvdReqHeaderHook returned, pMyData == NULL.\n",
                   ModuleName);
        return LSI_OK;
    }

    pMyData->state = PS_STATE_INIT;
    pMyData->sBuff = "";
    pMyData->request = req;
    pMyData->vhCtx = vhCtx;
    
    if (req->options != pSessConfig)
    {
        pMyData->flags |= PSF_OPT_OVERRIDE;
        pSessConfig = req->options;
    }
    g_api->set_module_data(session, &MNAME, LSI_DATA_HTTP, pMyData);


    
    int aEnableHkpt[] = {LSI_HKPT_URI_MAP,};
    g_api->enable_hook(rec->session, &MNAME, 1, aEnableHkpt, 1);
    return LSI_OK;
}

static int UriMapHook(lsi_param_t *rec)
{
    lsi_session_t *session = (lsi_session_t *)rec->session;
    g_api->log(session, LSI_LOG_DEBUG,
               "[%s] UriMapHook(), begin.\n",
               ModuleName);


    PsMData *pMyData = (PsMData *) g_api->get_module_data(session,
                       &MNAME, LSI_DATA_HTTP);
    
    LsPsReq *req = pMyData->request;
    LsPsVhCtx *vhCtx = pMyData->vhCtx;
    
    bool pagespeed_resource = vhCtx->serverContext->IsPagespeedResource(
        *req->url);

    if (g_api->is_req_handler_registered(rec->session))
    {
        g_api->free_module_data(session, &MNAME, LSI_DATA_HTTP, ReleaseMydata);
        return LSI_OK;
    }
    else
    {
        int aEnableHkpt[] = {LSI_HKPT_HANDLER_RESTART,
                             LSI_HKPT_HTTP_END,
                             LSI_HKPT_RCVD_RESP_HEADER,
                             LSI_HKPT_SEND_RESP_BODY
                            };
        g_api->enable_hook(rec->session, &MNAME, 1, aEnableHkpt, 4);
    }

    
    
//     bool pagespeed_resource = vhCtx->serverContext->IsPagespeedResource(
//         *(pMyData->request->url));
    
    REQ_ROUTE response_category;
    if (pagespeed_resource)
    {
        pMyData->flags |= PSF_IS_PS_RES;
        response_category = REQ_ROUTE_RESOURCE;
    }
    else
        response_category = RouteRequest(pMyData, session, true);

    int ret = 0;
    g_api->set_req_wait_full_body(session);

    //Disable cache module
    //g_api->set_req_env(rec->session, "cache-control", 13, "no-cache", 8);

    switch (response_category)
    {
    case REQ_ROUTE_BEACON:
        ret = BeaconHandler(pMyData, session);
        if (ret == 0)
        {
            //statuc_code already set.
            pMyData->flags |= PSF_NO_HOOK;
            g_api->register_req_handler(session, &MNAME, 0);
            g_api->log(session, LSI_LOG_DEBUG,
                       "[%s] ps_uri_map_filter register_req_handler OK.\n",
                       ModuleName);
        }
        break;

    case REQ_ROUTE_STATIC:
    case REQ_ROUTE_MESSAGE:
        ret = SimpleHandler(pMyData, session, vhCtx->serverContext,
                            response_category);
        if (ret == 0)
        {
            pMyData->flags |= PSF_NO_HOOK;
            g_api->register_req_handler(session, &MNAME, 0);
            g_api->log(session, LSI_LOG_DEBUG,
                       "[%s] recv_req_header_check register_req_handler OK after call ps_simple_handler.\n",
                       ModuleName);
        }
        break;

    case REQ_ROUTE_STATISTICS:
    case REQ_ROUTE_GLOBAL_STATS:
    case REQ_ROUTE_CONSOLE:
    case REQ_ROUTE_ADMIN:
    case REQ_ROUTE_GLOBAL_ADMIN:
    case REQ_ROUTE_PURGE:
        createLsPsReqCtx(pMyData);
        ret = StartAdminHandler(pMyData, session, response_category);
        pMyData->state = PS_STATE_RECV_REQ;
        return LSI_SUSPEND;

    case REQ_ROUTE_IN_PLACE:
        createLsPsReqCtx(pMyData);
        ret = StartFetchInPlaceResource(pMyData, session);
        pMyData->state = PS_STATE_RECV_REQ;
        return LSI_SUSPEND;
        
    case REQ_ROUTE_RESOURCE:
        ret = StartFetchPageSpeedResource(pMyData, session);
        if (ret == 1) //suspended
        {
            g_api->log(session, LSI_LOG_DEBUG,
                       "[%s] recv_req_header_check suspend hook, pData=%p.\n",
                       ModuleName, pMyData);
            pMyData->state = PS_STATE_RECV_REQ;
            return LSI_SUSPEND;
        }
        break;

    default:
        break;
    }

    pMyData->state = PS_STATE_RECV_REQ;
    return LSI_OK;
}


static int BaseFetchHandler(PsMData *pMyData, lsi_session_t *session)
{
    LsPsReqCtx *ctx = pMyData->reqCtx;
    int rc = ctx->baseFetch->CollectAccumulatedWrites(session);
    g_api->log(session, LSI_LOG_DEBUG,
               "[modpagespeed] BaseFetchHandler called CollectAccumulatedWrites, ret %d, session=%p\n",
               rc, session);

    if (rc == LSI_OK)
        ctx->fetchDone = true;

    return 0;
}


static int CopyRespBody(PsMData *pMyData, lsi_session_t *session)
{
    int len;
    while ((len = pMyData->sBuff.size() - pMyData->nBuffOffset) > 0)
    {
        const char *pBuf = pMyData->sBuff.c_str() + pMyData->nBuffOffset;
        int written = g_api->append_resp_body(session, pBuf, len);//g_api->append_resp_body(session,  pBuf, len);
        if (written > 0)
        {
            pMyData->nBuffOffset += written;
        }
        else
        {
            //if (offset > 0)
            //    pMyData->sBuff.swap(GoogleString(pBuf, len));
            return LS_FAIL;//ERROR occured
        }
    }
    pMyData->sBuff.clear();
    return LS_OK;
}


//This event shoule occur only once!
static int BaseFetchDoneCb(evtcbhead_s *session_, long, void *)
{
    g_api->log((lsi_session_t *)session_, LSI_LOG_DEBUG,
               "[%s] BaseFetchDoneCb(), session=%p.\n", ModuleName, 
               session_);
    
    if (!session_)
    {
         //session has been closed. PsMData has been released. 
        return -1;
    }

    lsi_session_t *session = (lsi_session_t *) session_;
    PsMData *pMyData = (PsMData *) g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);
    if (!pMyData)
        return 0;

    //pMyData->ctx->session can be updated to NULL when httpsession releaseresources
//     if (pMyData->ctx->session != session_)
//     {
//         g_api->free_module_data(session, &MNAME, LSI_DATA_HTTP);
//         return 0;
//     }

    if (pMyData->reqCtx->baseFetch)
    {
        if (!pMyData->reqCtx->fetchDone)
            BaseFetchHandler(pMyData, session);
        else
        {
            CHECK(0);//should NEVER BE HERE since call only once
            pMyData->reqCtx->baseFetch->CollectAccumulatedWrites(session);
        }
    }

    //g_api->reset_session_back_ref_ptr(session);
    
    //For suspended case, use the following to resume
    int status_code =
        pMyData->reqCtx->baseFetch->response_headers()->status_code();
    bool status_ok = (status_code != 0) && (status_code < 400);
    if (status_ok)
    {
        pMyData->statusCode = status_code;

        //Add below code to avoid register_req_handler when it is only filters.
        if (!pMyData->reqCtx->htmlRewrite) {
            pMyData->flags |= PSF_NO_HOOK;
            g_api->register_req_handler(session, &MNAME, 0);
            g_api->log(session, LSI_LOG_DEBUG,
                   "[%s] register_req_handler to serve base fetch result.\n", ModuleName);
        }
    }

//     if (pMyData->reqCtx->htmlRewrite)
//     {
//         //pMyData->reqCtx->baseFetch->CollectHeaders(session);
//         g_api->set_resp_content_length(session, -1);
//         g_api->log(session, LSI_LOG_DEBUG,
//                    "[%s] session: %p, BaseFetech RespBody size=%zd.\n",
//                    ModuleName, session, pMyData->sBuff.size());
// 
//         if (CopyRespBody(pMyData, session) == LS_FAIL)
//         {
//             g_api->log(session, LSI_LOG_DEBUG,
//                        "[%s] Failed to copy RespBody.\n", ModuleName);
//         }
//     }
    
    g_api->create_session_resume_event(session, &MNAME);
    g_api->set_handler_write_state(session, 1);

    return 0;
}

static int PsHandlerProcess(const lsi_session_t *session)
{
    PsMData *pMyData = (PsMData *) g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);

    if (!pMyData)
    {
        g_api->log(session, LSI_LOG_ERROR,
                   "[%s] internal error during myhandler_process.\n", ModuleName);
        return 500;
    }
    pMyData->flags |= PSF_NO_HOOK;
    pMyData->state = PS_STATE_DONE;

    g_api->log(session, LSI_LOG_DEBUG,
                       "[%s] PsHandlerProcess called with code %d.\n", 
               ModuleName, pMyData->statusCode);
    g_api->set_status_code(session, pMyData->statusCode);

    if (pMyData->respHeaders)
        CopyRespHeadersToServer((lsi_session_t *)session, *pMyData->respHeaders,
                                kDontPreserveHeaders);
    else
    {
        if (pMyData->reqCtx && pMyData->reqCtx->baseFetch)
        {
            pMyData->reqCtx->baseFetch->CollectHeaders(session);
            if (!pMyData->reqCtx->fetchDone)
                BaseFetchHandler(pMyData, (lsi_session_t *)session);
            
        }
    }
    g_api->remove_resp_header(session, LSI_RSPHDR_CONTENT_LENGTH, NULL, 0);

    g_api->set_resp_header(session, -1, PAGESPEED_RESP_HEADER, 
                           sizeof(PAGESPEED_RESP_HEADER) - 1,
                           MODPAGESPEEDVERSION "-0", 
                           sizeof(MODPAGESPEEDVERSION "-0") - 1,
                           LSI_HEADEROP_SET);

//     //TEST
//     char sHex[15] = {0};
//     snprintf(sHex, 13, "vary=%02X",
//             LsUAMatcher::getInstance().getUaCode(pMyData->request->userAgent.as_string().c_str()));
//     g_api->set_resp_header(session, -1, "UACODE", 6, sHex, strlen(sHex),
//                            LSI_HEADEROP_SET);
//     //TEST
    
    
    
    if (!pMyData->sBuff.empty())
    {
        if (CopyRespBody(pMyData, (lsi_session_t *)session) == LS_FAIL)
        {
            g_api->log(session, LSI_LOG_DEBUG,
                       "[%s] internal error during processing.\n", ModuleName);
            return 500;
        }
    }
    g_api->end_resp(session);
    g_api->free_module_data(session, &MNAME, LSI_DATA_HTTP, ReleaseMydata);
    return 0;
}



static lsi_serverhook_t serverHooks[] =
{
    { LSI_HKPT_MAIN_INITED,         PostConfig,         LSI_HOOK_NORMAL,    LSI_FLAG_ENABLED },
    { LSI_HKPT_WORKER_INIT,         ChildInit,          LSI_HOOK_NORMAL,    LSI_FLAG_ENABLED },
    { LSI_HKPT_MAIN_ATEXIT,         TerminateMainConf,  LSI_HOOK_NORMAL,    LSI_FLAG_ENABLED },
    { LSI_HKPT_RCVD_REQ_HEADER,     RcvdReqHeaderHook,  LSI_HOOK_NORMAL,    LSI_FLAG_ENABLED},
    { LSI_HKPT_URI_MAP,             UriMapHook,         LSI_HOOK_NORMAL,    0 },
    { LSI_HKPT_HANDLER_RESTART,     EndSession,         LSI_HOOK_NORMAL,    0 },
    { LSI_HKPT_HTTP_END,            EndSession,         LSI_HOOK_NORMAL,    0 },
    { LSI_HKPT_RCVD_RESP_HEADER,    rcvdRespHeaderHook,     LSI_HOOK_NORMAL,    0 },
    {
        LSI_HKPT_SEND_RESP_BODY,      sendRespBody,       LSI_HOOK_NORMAL,
        LSI_FLAG_TRANSFORM | LSI_FLAG_PROCESS_STATIC | LSI_FLAG_DECOMPRESS_REQUIRED
    },
    LSI_HOOK_END   //Must put this at the end position
};

static int Init(lsi_module_t *pModule)
{
    g_api->init_module_data(pModule, ReleaseMydata, LSI_DATA_HTTP);
    g_api->init_module_data(pModule, ReleaseVhCtx, LSI_DATA_VHOST);

//#define TEST_UAMATCHER
#ifdef  TEST_UAMATCHER
    extern void UAMatcherTest();
    UAMatcherTest();
#endif

    return 0;
}


static lsi_confparser_t dealConfig = { ParseConfig, FreeConfig, paramArray };/*MergeConfig*/
static lsi_reqhdlr_t _handler = { PsHandlerProcess, NULL, NULL, NULL };
LSMODULE_EXPORT lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, Init, &_handler,
                &dealConfig, MODPAGESPEEDVERSION, serverHooks, {0} };

