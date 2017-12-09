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

//  Author: dxu@litespeedtech.com (David Shue)

#include "pagespeed.h"
#include <string.h>
#include <lsr/ls_loopbuf.h>
#include <lsr/ls_xpool.h>


//#include <net/base/iovec.h>
//#include <apr_poll.h>
#include <util/autostr.h>
#include <util/autobuf.h>
#include <util/stringtool.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "log_message_handler.h"
#include "../../src/http/serverprocessconfig.h"
#include <signal.h>

#include "ls_base_fetch.h"
#include "ls_caching_headers.h"
#include "ls_message_handler.h"
#include "ls_rewrite_driver_factory.h"
#include "ls_rewrite_options.h"
#include "ls_server_context.h"

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

DECL_COMPONENT_LOG("modpagespeed");

#define  POST_BUF_READ_SIZE 65536

// Needed for SystemRewriteDriverFactory to use shared memory.
#define PAGESPEED_SUPPORT_POSIX_SHARED_MEM
LsiRewriteDriverFactory* active_driver_factory = NULL;
bool factory_deleted = false;

#define PAGESPEED_RESP_HEADER "X-LS-Pagespeed"

enum HTTP_METHOD
{
    HTTP_UNKNOWN = 0,
    HTTP_OPTIONS,
    HTTP_GET ,
    HTTP_HEAD,
    HTTP_POST,
    HTTP_PUT ,
    HTTP_DELETE,
    HTTP_TRACE,
    HTTP_CONNECT,
    HTTP_MOVE,

    //Some unused valus deleted.

    HTTP_PURGE,
    HTTP_REFRESH,
    HTTP_METHOD_END,
};




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


//process level data, can be accessed anywhere
struct ps_main_conf_t
{
    LsiRewriteDriverFactory    *driverFactory;
};

//VHost level data
struct ps_vh_conf_t
{
    LsServerContext            *serverContext;
    ProxyFetchFactory          *proxyFetchFactory;
    MessageHandler             *handler;
};

typedef struct
{
    LsiBaseFetch *baseFetch;

    // for html rewrite
    ProxyFetch *proxyFetch;

    // for in place resource
    RewriteDriver *driver;
    InPlaceResourceRecorder *recorder;

    bool htmlRewrite;
    bool inPlace;
    bool fetchDone;
    PreserveCachingHeaders preserveCachingHeaders;
} ps_request_ctx_t; //session module data

struct PsMData
{
    ps_request_ctx_t    *ctx;
    ps_vh_conf_t        *cfg_s;
    
    const char          *userAgent;
    int                  uaLen;
    GoogleString         urlString;
    HTTP_METHOD          method;

    //return result
    int16_t              statusCode;
    ResponseHeaders     *respHeaders;

    GoogleString         sBuff;
    size_t               nBuffOffset;
    int8_t               endRespCalled;
    int8_t               doneCalled;
};

const char *kInternalEtagName = "@psol-etag";
// The process context takes care of proactively initialising
// a few libraries for us, some of which are not thread-safe
// when they are initialized lazily.
ProcessContext *g_pProcessContext = new ProcessContext();

//LsiRewriteOptions* is data in all level and just inherit with the flow
//global --> Vhost  --> context  --> session
static ps_main_conf_t *g_pMainConf = NULL;
static int g_bMainConfInited = 0;


//////////////////////
StringPiece StrToStringPiece(AutoStr2 s)
{
    return StringPiece(s.c_str(), s.len());
}

//All of the parameters should have "pagespeed" as the first word.
lsi_config_key_s paramArray[] =
{
    {"pagespeed", 0, 0},
    {NULL,0,0} //Must have NULL in the last item
};


int SetCacheControl(const lsi_session_t *session, char *cache_control)
{
    g_api->set_resp_header(session, LSI_RSPHDR_CACHE_CTRL, NULL, 0,
                           cache_control, strlen(cache_control), LSI_HEADEROP_SET);
    return 0;
}


int SetLimitCacheControl(const lsi_session_t *session, char *buffer, int len)
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


//If copy_request is 0, then copy response headers, Other copy request headers.
template<class Headers>
void CopyHeaders(const lsi_session_t *session, int is_from_request, Headers *to)
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
static int GetHttpVersion(const lsi_session_t *session)
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
    const lsi_session_t *session, ResponseHeaders *headers)
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

void net_instaweb::CopyReqHeadersFromServer(const lsi_session_t *session,
        RequestHeaders *headers)
{
    int version = GetHttpVersion(session);
    headers->set_major_version(version / 1000);
    headers->set_minor_version(version % 1000);
    CopyHeaders(session, 1, headers);
}

int net_instaweb::CopyRespHeadersToServer(
    const lsi_session_t *session,
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
            /***
             * In this case, to keep cache-control header for ls cache
             */
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
            //g_api->set_resp_content_length(session, (int64_t) atol(value.c_str()));
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

int net_instaweb::CopyRespBodyToBuf(const lsi_session_t *session, GoogleString &str,
                                    int done_called)
{
    PsMData *pMyData = (PsMData *) g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);
    //pMyData->status_code = 200;
    if (pMyData->sBuff.size() > 0)
        pMyData->sBuff.append(str);
    else
        pMyData->sBuff.swap(str);
    
    pMyData->nBuffOffset = 0;
    pMyData->doneCalled = done_called;
    return 0;
}

int TerminateMainConf(lsi_param_t *rec)
{
    delete g_pProcessContext;
    g_pProcessContext = NULL;

    if (g_pMainConf)
    {
        LsiRewriteOptions::Terminate();
        LsiRewriteDriverFactory::Terminate();
        delete g_pMainConf->driverFactory;
        //delete pMainConf->handler;
        //pMainConf->handler = NULL;
        delete g_pMainConf;
        g_pMainConf = NULL;
    }
    factory_deleted = false;
    return 0;
}

static int ReleaseVhConf(void *p)
{
    if (p)
    {
        ps_vh_conf_t *cfg_s = (ps_vh_conf_t *) p;

        if (!factory_deleted && cfg_s->serverContext != NULL) {
            if (active_driver_factory == cfg_s->serverContext->factory()) {
                active_driver_factory = NULL;
            }
            delete cfg_s->serverContext->factory();
            factory_deleted = true;
        }


        if (cfg_s->proxyFetchFactory)
        {
            delete cfg_s->proxyFetchFactory;
            cfg_s->proxyFetchFactory = NULL;
        }

        delete cfg_s;
    }

    return 0;
}

void ReleaseBaseFetch(PsMData *pData)
{
    // In the normal flow BaseFetch doesn't delete itself in HandleDone() because
    // we still need to receive notification via pipe and call
    // CollectAccumulatedWrites.  If there's an error and we're cleaning up early
    // then HandleDone() hasn't been called yet and we need the base fetch to wait
    // for that and then delete itself.
    if (pData->ctx == NULL)
        return ;

    if (pData->ctx->baseFetch != NULL)
    {
        pData->ctx->baseFetch->DecrementRefCount();
        pData->ctx->baseFetch = NULL;
    }

    pData->sBuff.clear();
    pData->nBuffOffset = 0;
    pData->doneCalled = false;
}

static int ReleaseRequestContext(PsMData *pData)
{
    // proxy_fetch deleted itself if we called Done(), but if an error happened
    // before then we need to tell it to delete itself.
    //
    // If this is a resource fetch then proxy_fetch was never initialized.
    if (pData->ctx->proxyFetch != NULL)
    {
        pData->ctx->proxyFetch->Done(false /* failure */);
        pData->ctx->proxyFetch = NULL;
    }

    if (pData->ctx->driver != NULL)
    {
        pData->ctx->driver->Cleanup();
        pData->ctx->driver = NULL;
    }

    if (pData->ctx->recorder != NULL)
    {
        pData->ctx->recorder->Fail();
        pData->ctx->recorder->DoneAndSetHeaders(NULL, false);
        pData->ctx->recorder = NULL;
    }

    ReleaseBaseFetch(pData);
    delete pData->ctx;
    pData->ctx = NULL;
    return 0;
}

static int ReleaseMydata(void *data)
{
    PsMData *pData = (PsMData *) data;

    if (!pData)
        return 0;

    if (pData->ctx)
        ReleaseRequestContext(pData);

    if (pData->respHeaders)
        delete pData->respHeaders;

    pData->urlString.clear();
    pData->sBuff.clear();
    pData->nBuffOffset = 0;
    delete pData;
    return 0;
}

int EndSession(lsi_param_t *rec)
{
    PsMData *pData = (PsMData *) g_api->get_module_data(rec->session, &MNAME,
                     LSI_DATA_HTTP);

    if (pData)
    {
        LSC_DBG(rec->session, "ps_end_session, session=%p pData=%p.\n",
                rec->session, pData);

        long evt_obj;
        if (pData->ctx && pData->ctx->baseFetch 
            && (evt_obj = pData->ctx->baseFetch->AtomicSetEventObj(0)) != 0)
        {
            LSC_DBG(rec->session,
                    "pending event: %ld for base fetch need to be cancelled for session=%p.\n",
                    evt_obj, rec->session);
            g_api->cancel_event(rec->session, evt_obj);
        }

        g_api->free_module_data(rec->session, &MNAME, LSI_DATA_HTTP,
                                ReleaseMydata);
    }


    return 0;
}

bool IsHttps(const lsi_session_t *session)
{
    char s[12] = {0};
    int len = g_api->get_req_var_by_id(session, LSI_VAR_HTTPS, s, 12);
    if (len == 2)
        return true;
    else
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
            LSC_ERR(NULL,
                    "%s path %s does not exist and could not be created.\n",
                    directive.as_string().c_str(),
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
        LSC_DBG(NULL, "%s path %s stat() failed.\n",
                directive.as_string().c_str(), path.as_string().c_str());
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
static int CreateMainConf()
{
    if (g_bMainConfInited == 1)
        return 0;

    g_pMainConf = new ps_main_conf_t;

    if (!g_pMainConf)
    {
        g_api->log(NULL, LSI_LOG_ERROR, "[%s]GDItem init error.\n", ModuleName);
        return LS_FAIL;
    }

    LsiRewriteOptions::Initialize();
    LsiRewriteDriverFactory::Initialize();

    g_pMainConf->driverFactory = new LsiRewriteDriverFactory(
        *g_pProcessContext,
        new SystemThreadSystem(),
        "" /* hostname, not used */,
        -1 /* port, not used */);

    if (g_pMainConf->driverFactory == NULL)
    {
        delete g_pMainConf;
        g_pMainConf = NULL;
        g_api->log(NULL, LSI_LOG_ERROR, "[%s]GDItem init error 2.\n", ModuleName);
        return LS_FAIL;
    }

    active_driver_factory = g_pMainConf->driverFactory;
    active_driver_factory->LoggingInit();
    g_pMainConf->driverFactory->Init();
    g_bMainConfInited = 1;
    return 0;
}

inline void TrimLeadingSpace(const char **p)
{
    char ch;
    while (((ch = **p) == ' ') || (ch == '\t') || (ch == '\r'))
        ++ (*p);
}

static void ParseOption(LsiRewriteOptions *pOption, const char *sLine,
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
                   "modpagespeed ParseOption parssing '%.*s' on level %d [%s]\n",
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

    MessageHandler *handler = g_pMainConf->driverFactory->message_handler();
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
                                g_pMainConf->driverFactory, scope);

}

#define DEFAULT_SERVER_CONFIG  "pagespeed FileCachePath /tmp/lshttpd/pagespeed/"

static void *ParseConfig(module_param_info_t *param, int paramCount,
                         void *_initial_config, int level, const char *name)
{
    if (CreateMainConf())
        return NULL;

    LsiRewriteOptions *pInitOption = (LsiRewriteOptions *) _initial_config;
    LsiRewriteOptions *pOption = NULL;

    if (pInitOption)
        pOption = pInitOption->Clone();
    else
        pOption = new LsiRewriteOptions(
            g_pMainConf->driverFactory->thread_system());

    if (!pOption)
        return NULL;

    //For server level config, must at least set the "FileCachePath", otherwise 
    //will cause FileCachePath not set and init failed.
    
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
    delete(LsiRewriteOptions *) _config;
}

static int ChildInit(lsi_param_t *rec);
static int dummy_port = 0;
static int PostConfig(lsi_param_t *rec)
{
    std::vector<SystemServerContext *> server_contexts;
    int vhost_count = g_api->get_vhost_count();

    for (int s = 0; s < vhost_count; s++)
    {
        const void *vhost = g_api->get_vhost(s);

        LsiRewriteOptions *vhost_option = (LsiRewriteOptions *)
                                          g_api->get_vhost_module_param(vhost, &MNAME);

        //Comment: when Amdin/html parse, this will be NULL, we need not to add it
        if (vhost_option != NULL)
        {
            g_pMainConf->driverFactory->SetMainConf(vhost_option);

            ps_vh_conf_t *cfg_s = new ps_vh_conf_t;
            cfg_s->serverContext = g_pMainConf->driverFactory->MakeLsiServerContext(
                                       "dummy_hostname", --dummy_port);

            cfg_s->serverContext->global_options()->Merge(*vhost_option);
            cfg_s->handler =
                g_pMainConf->driverFactory->message_handler();
            // LsiMessageHandler(pMainConf->driver_factory->thread_system()->NewMutex());
            //Why GoogleMessageHandler() but not LsMessageHandler

            if (cfg_s->serverContext->global_options()->enabled())
            {
                //GoogleMessageHandler handler;
                const char *file_cache_path =
                    cfg_s->serverContext->Config()->file_cache_path().c_str();

                if (file_cache_path[0] == '\0')
                {
                    g_api->log(NULL, LSI_LOG_ERROR,
                               "mod_pagespeed post_config ERROR, file_cache_path is NULL\n");
                    return LS_FAIL;
                }
                else if (!g_pMainConf->driverFactory->file_system()->IsDir(
                             file_cache_path, cfg_s->handler).is_true())
                {
                    g_api->log(NULL, LSI_LOG_ERROR,
                               "mod_pagespeed post_config ERROR, FileCachePath must be an writeable directory.\n");
                    return LS_FAIL;
                }

                g_api->log(NULL, LSI_LOG_DEBUG,
                           "mod_pagespeed post_config OK, file_cache_path is %s\n",
                           file_cache_path);
            }

            g_api->set_vhost_module_data(vhost, &MNAME, cfg_s);
            server_contexts.push_back(cfg_s->serverContext);
        }
    }


    GoogleString error_message = "";
    int error_index = -1;
    Statistics *global_statistics = NULL;

    g_api->log(NULL, LSI_LOG_DEBUG,
               "mod_pagespeed post_config call PostConfig()\n");
    g_pMainConf->driverFactory->PostConfig(
        server_contexts, &error_message, &error_index, &global_statistics);

    if (error_index != -1)
    {
        server_contexts[error_index]->message_handler()->Message(
            kError, "mod_pagespeed is enabled. %s", error_message.c_str());
        //g_api->log( NULL, LSI_LOG_ERROR, "mod_pagespeed is enabled. %s\n", error_message.c_str() );
        return LS_FAIL;
    }


    if (!server_contexts.empty())
    {
        IgnoreSigpipe();

        if (global_statistics == NULL)
            LsiRewriteDriverFactory::InitStats(
                g_pMainConf->driverFactory->statistics());

        g_pMainConf->driverFactory->LoggingInit();
        g_pMainConf->driverFactory->RootInit();
    }
    else
    {
        delete g_pMainConf->driverFactory;
        g_pMainConf->driverFactory = NULL;
        active_driver_factory = NULL;
    }


    return 0;
}

static int ChildInit(lsi_param_t *rec)
{
    if (g_pMainConf->driverFactory == NULL)
        return 0;

    SystemRewriteDriverFactory::InitApr();
    g_pMainConf->driverFactory->LoggingInit();
    g_pMainConf->driverFactory->ChildInit();

    int vhostCount = g_api->get_vhost_count();

    for (int s = 0; s < vhostCount; s++)
    {
        const void *vhost = g_api->get_vhost(s);
        ps_vh_conf_t *cfg_s = (ps_vh_conf_t *) g_api->get_vhost_module_data(vhost,
                              &MNAME);

        if (cfg_s && cfg_s->serverContext)
        {
            cfg_s->proxyFetchFactory = new ProxyFetchFactory(cfg_s->serverContext);
            g_pMainConf->driverFactory->SetServerContextMessageHandler(
                cfg_s->serverContext);
        }
    }


    g_pMainConf->driverFactory->StartThreads();
    return 0;
}

int EventCb(evtcbhead_s *session, long, void *);
int CreateBaseFetch(PsMData *pMyData, const lsi_session_t *session,
                    RequestContextPtr request_context,
                    RequestHeaders *request_headers,
                    BaseFetchType type)
{
    if (pMyData->ctx->baseFetch)
    {
        long evtObj = pMyData->ctx->baseFetch->AtomicSetEventObj(0);
        if (evtObj != 0)
            g_api->cancel_event(session, evtObj);
    }
    pMyData->ctx->baseFetch = new LsiBaseFetch(session,
                                               pMyData->cfg_s->serverContext,
                                               request_context,
                                               pMyData->ctx->preserveCachingHeaders,
                                               type);

    //When the base_fetch is good then set the callback, otherwise, may cause crash.
    if (pMyData->ctx->baseFetch)
    {
        pMyData->ctx->baseFetch->SetRequestHeadersTakingOwnership(request_headers);
        long event_obj = g_api->get_event_obj(EventCb, session, 0, 0);
        g_api->log(session, LSI_LOG_DEBUG,
               "[Module:ModPagespeed]ps_create_base_fetch get event obj %p, session=%p\n",
               (void *)event_obj, session);
        pMyData->ctx->baseFetch->AtomicSetEventObj(event_obj);
//         g_api->set_session_back_ref_ptr(session, 
//                                         g_api->get_session_ref_ptr(event_obj));
        return 0;
    }
    else
        return LS_FAIL;
}

bool CheckPagespeedApplicable(PsMData *pMyData, const lsi_session_t *session)
{
//     //Check status code is it is 200
//     if( g_api->get_status_code( session ) != 200 )
//     {
//         return false;
//     }

    // We can't operate on Content-Ranges.
    iovec iov[1];

    if (g_api->get_resp_header(session, LSI_RSPHDR_CONTENT_TYPE, NULL, 0,
                               iov, 1) != 1)
    {
        g_api->log(session, LSI_LOG_DEBUG,
                   "[%s]Request not rewritten because: no Content-Type set.\n",
                   ModuleName);
        return false;
    }

    StringPiece str = StringPiece((const char *)(iov[0].iov_base),
                                  iov[0].iov_len);
    const ContentType *content_type =  MimeTypeToContentType(str);
    if (content_type == NULL || !content_type->IsHtmlLike())
    {
        g_api->log(session, LSI_LOG_DEBUG,
                   "[%s]Request not rewritten because:[%s] not 'html like' Content-Type.\n",
                   ModuleName, str.as_string().c_str());
        return false;
    }

    return true;
}

char *net_instaweb::DetermineHost(const lsi_session_t *session,
                                  char *hostC, int maxLen)
{
    g_api->get_req_var_by_id(session, LSI_VAR_SERVER_NAME, hostC, maxLen);
    return hostC;
}

int net_instaweb::DeterminePort(const lsi_session_t *session)
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


void DetermineUrl(const lsi_session_t *session, GoogleString &str)
{
    int port = DeterminePort(session);
    GoogleString port_string;

    if ((IsHttps(session) && (port == 443 || port == -1)) ||
        (!IsHttps(session) && (port == 80 || port == -1)))
    {
        // No port specifier needed for requests on default ports.
        port_string = "";
    }
    else
        port_string = StrCat(":", IntegerToString(port));

    char hostC[512] = {0};
    StringPiece host = DetermineHost(session, hostC, 512);

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

    str = StrCat(IsHttps(session) ? "https://" : "http://",
                             host, port_string, uri);
    delete []uri;
}



// Wrapper around GetQueryOptions()
RewriteOptions *DetermineRequestOptions(
    const lsi_session_t *session,
    const RewriteOptions *domain_options, /* may be null */
    RequestHeaders *request_headers,
    ResponseHeaders *response_headers,
    RequestContextPtr request_context,
    ps_vh_conf_t *cfg_s,
    GoogleUrl *url,
    GoogleString *pagespeed_query_params,
    GoogleString *pagespeed_option_cookies)
{
    // Sets option from request headers and url.
    RewriteQuery rewrite_query;

    if (!cfg_s->serverContext->GetQueryOptions(
            request_context, domain_options, url, request_headers,
            response_headers, &rewrite_query))
    {
        // Failed to parse query params or request headers.  Treat this as if there
        // were no query params given.
        g_api->log(session, LSI_LOG_ERROR,
                   "ps_route request: parsing headers or query params failed.\n");
        return NULL;
    }

    *pagespeed_query_params =
        rewrite_query.pagespeed_query_params().ToEscapedString();
    *pagespeed_option_cookies =
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
bool SetExperimentStateAndCookie(const lsi_session_t *session,
                                 ps_vh_conf_t *cfg_s,
                                 RequestHeaders *request_headers,
                                 RewriteOptions *options,
                                 const StringPiece &host)
{
    CHECK(options->running_experiment());
    bool need_cookie = cfg_s->serverContext->experiment_matcher()->
                       ClassifyIntoExperiment(*request_headers, 
                                              *cfg_s->serverContext->user_agent_matcher(),
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
bool DetermineOptions(const lsi_session_t *session,
                      RequestHeaders *request_headers,
                      ResponseHeaders *response_headers,
                      RewriteOptions *options,
                      RequestContextPtr request_context,
                      ps_vh_conf_t *cfg_s,
                      GoogleUrl *url,
                      GoogleString *pagespeed_query_params,
                      GoogleString *pagespeed_option_cookies,
                      bool html_rewrite)
{
    // Request-specific options, nearly always null.  If set they need to be
    // rebased on the directory options.
    RewriteOptions *request_options = DetermineRequestOptions(
                                          session, options, request_headers,
                                          response_headers, request_context,
                                          cfg_s, url, pagespeed_query_params,
                                          pagespeed_option_cookies);
    bool have_request_options = (request_options != NULL);

    // Modify our options in response to request options if specified.
    if (have_request_options)
    {
        options->Merge(*request_options);
        delete request_options;
        request_options = NULL;
    }

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
        bool ok = SetExperimentStateAndCookie(
                      session, cfg_s, request_headers, options, url->Host());
        if (!ok)
            return false;
    }

    return true;
}


// Fix URL based on X-Forwarded-Proto.
// http://code.google.com/p/modpagespeed/issues/detail?id=546 For example, if
// Apache gives us the URL "http://www.example.com/" and there is a header:
// "X-Forwarded-Proto: https", then we update this base URL to
// "https://www.example.com/".  This only ever changes the protocol of the url.
//
// Returns true if it modified url, false otherwise.
bool ApplyXForwardedProto(const lsi_session_t *session, GoogleString *url)
{
    int valLen = 0;
    const char *buf = g_api->get_req_header_by_id(session,
                      LSI_HDR_X_FORWARDED_FOR, &valLen);

    if (valLen == 0 || buf == NULL)
    {
        return false;  // No X-Forwarded-Proto header found.
    }

    AutoStr2 bufStr(buf);
    StringPiece x_forwarded_proto =
        StrToStringPiece(bufStr);

    if (!STR_CASE_EQ_LITERAL(bufStr, "http") &&
        !STR_CASE_EQ_LITERAL(bufStr, "https"))
    {
        LOG(WARNING) << "Unsupported X-Forwarded-Proto: " << x_forwarded_proto
                     << " for URL " << url << " protocol not changed.";
        return false;
    }

    StringPiece url_sp(*url);
    StringPiece::size_type colon_pos = url_sp.find(":");

    if (colon_pos == StringPiece::npos)
    {
        return false;  // URL appears to have no protocol; give up.
    }

//
    // Replace URL protocol with that specified in X-Forwarded-Proto.
    *url = StrCat(x_forwarded_proto, url_sp.substr(colon_pos));

    return true;
}

bool IsPagespeedSubrequest(const lsi_session_t *session, const char *ua,
                           int &uaLen)
{
    if (ua && uaLen > 0)
    {
        if (memmem(ua, uaLen, kModPagespeedSubrequestUserAgent,
                   strlen(kModPagespeedSubrequestUserAgent)))
        {
            g_api->log(session, LSI_LOG_DEBUG,
                       "[Module:ModPagespeed]Request not rewritten because: User-Agent appears to be %s.\n",
                       kModPagespeedSubrequestUserAgent);
            return true;
        }
    }

    return false;
}

void BeaconHandlerHelper(PsMData *pMyData, const lsi_session_t *session,
                         StringPiece beacon_data)
{
    g_api->log(session, LSI_LOG_DEBUG,
               "ps_beacon_handler_helper: beacon[%zd] %s",
               beacon_data.size(),  beacon_data.data());

    StringPiece user_agent = StringPiece(pMyData->userAgent, pMyData->uaLen);
    CHECK(pMyData->cfg_s != NULL);

    RequestContextPtr request_context(
        pMyData->cfg_s->serverContext->NewRequestContext(session));

    request_context->set_options(
        pMyData->cfg_s->serverContext->global_options()->ComputeHttpOptions());

    pMyData->cfg_s->serverContext->HandleBeacon(
        beacon_data,
        user_agent,
        request_context);

    SetCacheControl(session, const_cast<char *>("max-age=0, no-cache"));
}

// Parses out query params from the request.
//isPost: 1, use both query param and post bosy, 0, use query param
static void QueryParamsHandler(const lsi_session_t *session, AutoBuf *pBuf, int isPost)
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


int BeaconHandler(PsMData *pMyData, const lsi_session_t *session)
{
    // Use query params.
    AutoBuf     buf;
    StringPiece query_param_beacon_data;
    int isPost = (pMyData->method == HTTP_POST);
    QueryParamsHandler(session, &buf, isPost);
    query_param_beacon_data.set(buf.begin(), buf.size());
    BeaconHandlerHelper(pMyData, session, query_param_beacon_data);
    pMyData->statusCode = (isPost ? 200 : 204);
    return 0;
}

int SimpleHandler(PsMData *pMyData, const lsi_session_t *session,
                  LsServerContext *server_context,
                  RequestRouting::Response response_category)
{
    LsiRewriteDriverFactory *factory =
        static_cast<LsiRewriteDriverFactory *>(
            server_context->factory());
    LsiMessageHandler *message_handler = factory->GetLsiMessageHandler();

    int uriLen = g_api->get_req_org_uri(session, NULL, 0);
    char *uri = new char[uriLen + 1];

    g_api->get_req_org_uri(session, uri, uriLen + 1);
    uri[uriLen] = 0x00;
    StringPiece request_uri_path = uri;//

    GoogleString &url_string = pMyData->urlString;
    GoogleUrl url(url_string);
    QueryParams query_params;

    if (url.IsWebValid())
        query_params.ParseFromUrl(url);

    GoogleString output;
    StringWriter writer(&output);
    pMyData->statusCode = 200;
    HttpStatus::Code status = HttpStatus::kOK;
    ContentType content_type = kContentTypeHtml;
    StringPiece cache_control = HttpAttributes::kNoCache;
    const char *error_message = NULL;

    switch (response_category)
    {
    case RequestRouting::kStaticContent:
        {
            StringPiece file_contents;

            if (!server_context->static_asset_manager()->GetAsset(
                    request_uri_path.substr(factory->static_asset_prefix().length()),
                    &file_contents, &content_type, &cache_control))
                return LS_FAIL;

            file_contents.CopyToString(&output);
            break;
        }

    case RequestRouting::kMessages:
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
                   "ps_simple_handler: unknown RequestRouting.");
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

    //g_api->append_body_buf(session, output.c_str(), output.size());
    pMyData->sBuff.clear();
    pMyData->nBuffOffset = 0;
    pMyData->sBuff.append(output);

    return 0;
}



int ResourceHandler(PsMData *pMyData,
                    const lsi_session_t *session,
                    bool html_rewrite,
                    RequestRouting::Response response_category)
{
    ps_request_ctx_t *ctx = pMyData->ctx;
    ps_vh_conf_t *cfg_s = pMyData->cfg_s;
    CHECK(!(html_rewrite && (ctx == NULL || ctx->htmlRewrite == false)));

    if (!html_rewrite &&
        pMyData->method != HTTP_GET &&
        pMyData->method != HTTP_HEAD &&
        pMyData->method != HTTP_POST &&
        response_category != RequestRouting::kCachePurge)
        return LS_FAIL;

    GoogleString url_string;
    DetermineUrl(session, url_string);
    GoogleUrl url(url_string);
    if (!url.IsWebValid())
    {
        g_api->log(session, LSI_LOG_DEBUG, "invalid url");
        return LS_FAIL;
    }


    ::scoped_ptr<RequestHeaders> request_headers(new RequestHeaders);
    ::scoped_ptr<ResponseHeaders> response_headers(new ResponseHeaders);

    CopyReqHeadersFromServer(session, request_headers.get());
    CopyRespHeadersFromServer(session, response_headers.get());

    RequestContextPtr request_context(
        cfg_s->serverContext->NewRequestContext(session));
    LsiRewriteOptions *options = (LsiRewriteOptions *) g_api->get_config(
                                     session, &MNAME);;
    GoogleString pagespeed_query_params;
    GoogleString pagespeed_option_cookies;

    //Diffirent from google code, here the option is always inherit from the context, and it should never be NULL
    if (!DetermineOptions(session, request_headers.get(),
                          response_headers.get(),
                          options, request_context, cfg_s, &url,
                          &pagespeed_query_params, &pagespeed_option_cookies,
                          html_rewrite))
        return LS_FAIL;

    if (options == NULL)
    {
        //Never happen!!!
        CHECK(0);
        options = (LsiRewriteOptions *)cfg_s->serverContext->global_options();
    }

    if (!options->enabled())
    {
        // Disabled via query params or request headers.
        return LS_FAIL;
    }

    request_context->set_options(options->ComputeHttpOptions());

    // ps_determine_options modified url, removing any ModPagespeedFoo=Bar query
    // parameters.  Keep url_string in sync with url.
    url.Spec().CopyToString(&url_string);




    if (cfg_s->serverContext->global_options()->respect_x_forwarded_proto())
    {
        bool modified_url = ApplyXForwardedProto(session, &url_string);

        if (modified_url)
        {
            url.Reset(url_string);
            CHECK(url.IsWebValid()) << "The output of ps_apply_x_forwarded_proto"
                                    << " should always be a valid url because it only"
                                    << " changes the scheme between http and https.";
        }
    }

    bool pagespeed_resource =
        !html_rewrite && cfg_s->serverContext->IsPagespeedResource(url);
    bool is_an_admin_handler =
        response_category == RequestRouting::kStatistics ||
        response_category == RequestRouting::kGlobalStatistics ||
        response_category == RequestRouting::kConsole ||
        response_category == RequestRouting::kAdmin ||
        response_category == RequestRouting::kGlobalAdmin ||
        response_category == RequestRouting::kCachePurge;

    if (html_rewrite)
        ReleaseBaseFetch(pMyData);
    else
    {
        // create request ctx
        CHECK(ctx == NULL);
        ctx = new ps_request_ctx_t();

        ctx->htmlRewrite = false;
        ctx->inPlace = false;
        ctx->proxyFetch = NULL;
        ctx->baseFetch = NULL;
        ctx->fetchDone = false;
        ctx->driver = NULL;
        ctx->recorder = NULL;
        ctx->preserveCachingHeaders = kDontPreserveHeaders;

        if (!options->modify_caching_headers())
            ctx->preserveCachingHeaders = kPreserveAllCachingHeaders;
        else if (!options->IsDownstreamCacheIntegrationEnabled())
        {
            // Downstream cache integration is not enabled. Disable original
            // Cache-Control headers.
            ctx->preserveCachingHeaders = kDontPreserveHeaders;
        }
        else if (!pagespeed_resource && !is_an_admin_handler)
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
        //ctx->location_field_set = false;
        //ctx->psol_vary_accept_only = false;
        pMyData->urlString = url_string;
        pMyData->ctx = ctx;
    }

    if (pagespeed_resource)
    {
        CreateBaseFetch(pMyData, session, request_context,
                        request_headers.release(), kPageSpeedResource);
        ResourceFetch::Start(
            url,
            NULL,
            false /* using_spdy */, cfg_s->serverContext, ctx->baseFetch);

        return 1;
    }
    else if (is_an_admin_handler)
    {
        CreateBaseFetch(pMyData, session, request_context,
                        request_headers.release(), kAdminPage);
        QueryParams query_params;
        query_params.ParseFromUrl(url);

        PosixTimer timer;
        int64 now_ms = timer.NowMs();
        ctx->baseFetch->response_headers()->SetDateAndCaching(
            now_ms, 0 /* max-age */, ", no-cache");

        if (response_category == RequestRouting::kStatistics ||
            response_category == RequestRouting::kGlobalStatistics)
        {
            cfg_s->serverContext->StatisticsPage(
                response_category == RequestRouting::kGlobalStatistics,
                query_params,
                cfg_s->serverContext->Config(),
                ctx->baseFetch);
        }
        else if (response_category == RequestRouting::kConsole)
        {
            cfg_s->serverContext->ConsoleHandler(
                *cfg_s->serverContext->Config(),
                AdminSite::kStatistics,
                query_params,
                ctx->baseFetch);
        }
        else if (response_category == RequestRouting::kAdmin ||
                 response_category == RequestRouting::kGlobalAdmin)
        {
            cfg_s->serverContext->AdminPage(
                response_category == RequestRouting::kGlobalAdmin,
                url,
                query_params,
                cfg_s->serverContext->Config(),
                ctx->baseFetch);
        }
        else if (response_category == RequestRouting::kCachePurge)
        {
            AdminSite *admin_site = cfg_s->serverContext->admin_site();
            admin_site->PurgeHandler(url_string,
                                     cfg_s->serverContext->cache_path(),
                                     ctx->baseFetch);
        }
        else
            CHECK(false);

        return 1;
    } else if (!html_rewrite && response_category == RequestRouting::kResource) {
        bool is_proxy = false;
        GoogleString mapped_url;
        GoogleString host_header;

        if (options->domain_lawyer()->MapOriginUrl(
                url, &mapped_url, &host_header, &is_proxy) && is_proxy) {
            CreateBaseFetch(pMyData, session, request_context,
                            request_headers.release(), kPageSpeedProxy);
            
            RewriteDriver* driver;
            driver = cfg_s->serverContext->NewRewriteDriver(
                         ctx->baseFetch->request_context());
        
            driver->SetRequestHeaders(*ctx->baseFetch->request_headers());
            driver->set_pagespeed_query_params(pagespeed_query_params);
            driver->set_pagespeed_option_cookies(pagespeed_option_cookies);
    
            cfg_s->proxyFetchFactory->StartNewProxyFetch(mapped_url,
                                                         ctx->baseFetch, driver,
                                                         NULL /*property_callback*/,
                                                         NULL /*original_content_fetch*/);
            return 1;
        }
    }

    if (html_rewrite)
    {
        CreateBaseFetch(pMyData, session, request_context,
                        request_headers.release(), kHtmlTransform);
        // Do not store driver in request_context, it's not safe.
        RewriteDriver *driver;

        // If we don't have custom options we can use NewRewriteDriver which reuses
        // rewrite drivers and so is faster because there's no wait to construct
        // them.  Otherwise we have to build a new one every time.

        driver = cfg_s->serverContext->NewRewriteDriver(
                     ctx->baseFetch->request_context());

        driver->SetRequestHeaders(*ctx->baseFetch->request_headers());
        driver->set_pagespeed_query_params(pagespeed_query_params);
        driver->set_pagespeed_option_cookies(pagespeed_option_cookies);

        ProxyFetchPropertyCallbackCollector *property_callback =
            ProxyFetchFactory::InitiatePropertyCacheLookup(
                !html_rewrite /* is_resource_fetch */,
                url,
                cfg_s->serverContext,
                options,
                ctx->baseFetch,
                false);

        ctx->proxyFetch = cfg_s->proxyFetchFactory->CreateNewProxyFetch(
                              url_string, ctx->baseFetch, driver,
                              property_callback,
                              NULL /* original_content_fetch */);

        ctx->proxyFetch->set_trusted_input(true);
        g_api->log(NULL, LSI_LOG_DEBUG, "Create ProxyFetch %s.\n",
                   url_string.c_str());
        return 0;
    }

    if (options->in_place_rewriting_enabled() &&
        options->enabled() &&
        options->IsAllowed(url.Spec()))
    {
        CreateBaseFetch(pMyData, session, request_context,
                        request_headers.release(), kIproLookup);
        // Do not store driver in request_context, it's not safe.
        RewriteDriver *driver;

        driver = cfg_s->serverContext->NewRewriteDriver(
                     ctx->baseFetch->request_context());


        driver->SetRequestHeaders(*ctx->baseFetch->request_headers());

        ctx->driver = driver;

        cfg_s->serverContext->message_handler()->Message(
            kInfo, "Trying to serve rewritten resource in-place: %s",
            url_string.c_str());

        ctx->inPlace = true;
        ctx->baseFetch->SetIproLookup(true);
        ctx->driver->FetchInPlaceResource(
            url, false /* proxy_mode */, ctx->baseFetch);

        return 1;
    }

    //NEVER RUN TO THIS POINT BECAUSE THE PREVOIUS CHEKCING NBYPASS THIS ONE
    // NOTE: We are using the below debug message as is for some of our system
    // tests. So, be careful about test breakages caused by changing or
    // removing this line.
    g_api->log(session, LSI_LOG_DEBUG,
               "Passing on content handling for non-pagespeed resource '%s'\n",
               url_string.c_str());

    CHECK(ctx->baseFetch == NULL);
//     ctx->baseFetch->Done(false);
//     ReleaseBaseFetch(pMyData);
    // set html_rewrite flag.
    ctx->htmlRewrite = true;
    return LS_FAIL;
}



// Send each buffer in the chain to the proxyFetch for optimization.
// Eventually it will make it's way, optimized, to base_fetch.
//return 0 for error, 1 for
bool SendToPagespeed(PsMData *pMyData, lsi_param_t *rec,
                     StringPiece &str, int len,
                     ps_request_ctx_t *ctx)
{
    if (ctx->proxyFetch == NULL)
        return false;

    CHECK(ctx->proxyFetch != NULL);
    if (len > 0)
        ctx->proxyFetch->Write(str, pMyData->cfg_s->handler);

    if (rec->flag_in & LSI_CBFI_EOF)
    {
        ctx->proxyFetch->Done(true /* success */);
        ctx->proxyFetch = NULL;  // ProxyFetch deletes itself on Done().
    }
    else
        ctx->proxyFetch->Flush(pMyData->cfg_s->handler);
    return true;
}

void StripHtmlHeaders(const lsi_session_t *session)
{
    g_api->remove_resp_header(session, LSI_RSPHDR_CONTENT_LENGTH, NULL, 0);
    g_api->remove_resp_header(session, LSI_RSPHDR_ACCEPT_RANGES, NULL, 0);
}

int HtmlRewriteFixHeadersFilter(PsMData *pMyData,
                                const lsi_session_t *session, ps_request_ctx_t *ctx)
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
//         SetCacheControl(session,
//                         (char *) caching_headers.GenerateDisabledCacheControl().c_str());
    }

    // Pagespeed html doesn't need etags: it should never be cached.
    g_api->remove_resp_header(session, LSI_RSPHDR_ETAG, NULL, 0);

    // An html page may change without the underlying file changing, because of
    // how resources are included.  Pagespeed adds cache control headers for
    // resources instead of using the last modified header.
    g_api->remove_resp_header(session, LSI_RSPHDR_LAST_MODIFIED, NULL, 0);

    g_api->set_resp_header(session, -1, PAGESPEED_RESP_HEADER,
                           sizeof(PAGESPEED_RESP_HEADER) - 1,
                           MNAME.about, strlen(MNAME.about),
                           LSI_HEADEROP_SET);

//   // Clear expires
//   if (r->headers_out.expires) {
//     r->headers_out.expires->hash = 0;
//     r->headers_out.expires = NULL;
//   }

    return 0;
}

int InPlaceCheckHeaderFilter(PsMData *pMyData, const lsi_session_t *session,
                             ps_request_ctx_t *ctx)
{



    if (ctx->recorder != NULL)
    {
        g_api->log(session, LSI_LOG_DEBUG,
                   "ps in place check header filter recording: %s",
                   pMyData->urlString.c_str());

        CHECK(!ctx->inPlace);

        // The recorder will do this checking, so pass it the headers.
        ResponseHeaders response_headers;
        CopyRespHeadersFromServer(session, &response_headers);
        ctx->recorder->ConsiderResponseHeaders(
            InPlaceResourceRecorder::kPreliminaryHeaders, &response_headers);
        return 0;
    }

    if (!ctx->inPlace)
        return 0;

    g_api->log(session, LSI_LOG_DEBUG,
               "[Module:ModPagespeed]ps in place check header filter initial: %s\n",
               pMyData->urlString.c_str());

    int status_code =
        pMyData->ctx->baseFetch->response_headers()->status_code();
    //g_api->get_status_code( session );
    bool status_ok = (status_code != 0) && (status_code < 400);

    ps_vh_conf_t *cfg_s = pMyData->cfg_s;
    LsServerContext *server_context = cfg_s->serverContext;
    MessageHandler *message_handler = cfg_s->handler;
    GoogleString url;
    DetermineUrl(session, url);
    // The URL we use for cache key is a bit different since it may
    // have PageSpeed query params removed.
    GoogleString cache_url = pMyData->urlString;

    // continue process
    if (status_ok)
    {
        ctx->inPlace = false;

        server_context->rewrite_stats()->ipro_served()->Add(1);
        message_handler->Message(
            kInfo, "Serving rewritten resource in-place: %s",
            url.c_str());

        return 0;
    }

    if (status_code == CacheUrlAsyncFetcher::kNotInCacheStatus)
    {
        server_context->rewrite_stats()->ipro_not_in_cache()->Add(1);
        server_context->message_handler()->Message(
            kInfo,
            "Could not rewrite resource in-place "
            "because URL is not in cache: %s",
            cache_url.c_str());
        const SystemRewriteOptions *options = SystemRewriteOptions::DynamicCast(
                ctx->driver->options());

        RequestContextPtr request_context(
            cfg_s->serverContext->NewRequestContext(session));
        request_context->set_options(options->ComputeHttpOptions());

        RequestHeaders request_headers;
        CopyReqHeadersFromServer(session, &request_headers);
        // This URL was not found in cache (neither the input resource nor
        // a ResourceNotCacheable entry) so we need to get it into cache
        // (or at least a note that it cannot be cached stored there).
        // We do that using an Apache output filter.
        ctx->recorder = new InPlaceResourceRecorder(
            request_context,
            cache_url,
            ctx->driver->CacheFragment(),
            request_headers.GetProperties(),
            options->ipro_max_response_bytes(),
            options->ipro_max_concurrent_recordings(),
            server_context->http_cache(),
            server_context->statistics(),
            message_handler);
//     // set in memory flag for in place_body_filter
//     r->filter_need_in_memory = 1;

        // We don't have the response headers at all yet because we haven't yet gone
        // to the backend.


        /************************
         *
         * DIFF FROM NGX
         *
         *
         */
        ResponseHeaders response_headers;
        CopyRespHeadersFromServer(session, &response_headers);
        ctx->recorder->ConsiderResponseHeaders(
            InPlaceResourceRecorder::kPreliminaryHeaders, &response_headers);
        /*******************************
         *
         *
         */

    }
    else
    {
        server_context->rewrite_stats()->ipro_not_rewritable()->Add(1);
        message_handler->Message(kInfo,
                                 "Could not rewrite resource in-place: %s",
                                 url.c_str());
    }

    ctx->driver->Cleanup();
    ctx->driver = NULL;
    // enable html_rewrite
    ctx->htmlRewrite = true;
    ctx->inPlace = false;

    // re init ctx
    ctx->fetchDone = false;

    ReleaseBaseFetch(pMyData);

    return LS_FAIL;
}

int InPlaceBodyFilter(PsMData *pMyData, lsi_param_t *rec,
                      ps_request_ctx_t *ctx, StringPiece &contents, int length)
{
    g_api->log(rec->session, LSI_LOG_DEBUG,
               "[Module:ModPagespeed]ps in place body filter: %s, bufLen=%d\n",
               pMyData->urlString.c_str(), rec->len1);

    InPlaceResourceRecorder *recorder = ctx->recorder;
    if (length > 0)
        recorder->Write(contents, recorder->handler());

    if (rec->flag_in & LSI_CBFI_FLUSH)
        recorder->Flush(recorder->handler());

    if (rec->flag_in & LSI_CBFI_EOF || recorder->failed())
    {
        recorder->Flush(recorder->handler());
        ResponseHeaders response_headers;
        CopyRespHeadersFromServer(rec->session, &response_headers);
        ctx->recorder->DoneAndSetHeaders(&response_headers, true);
        ctx->recorder = NULL;
    }

    return 0;
}

int sendRespBody(lsi_param_t *rec)
{
    ps_vh_conf_t *cfg_s;
    ps_request_ctx_t *ctx;
    PsMData *pMyData = (PsMData *) g_api->get_module_data(rec->session,
                       &MNAME, LSI_DATA_HTTP);

    if (pMyData == NULL || (cfg_s = pMyData->cfg_s) == NULL
        || (ctx = pMyData->ctx) == NULL)
        return g_api->stream_write_next(rec, (const char *) rec->ptr1,
                                        rec->len1);
    g_api->log(rec->session, LSI_LOG_DEBUG,
               "[%s] sendRespBody() flag_in %d, buffer in %d.\n",
               ModuleName, rec->flag_in, rec->len1 );

    int doneCalled = pMyData->doneCalled;
    int ret = rec->len1;
    StringPiece contents;
    int writtenTotal = 0;
    if (ctx->htmlRewrite && !doneCalled)
    {
        if (rec->len1 > 0 ||  rec->flag_in)
        {
            contents = StringPiece((char *) rec->ptr1, rec->len1);
            SendToPagespeed(pMyData, rec, contents, rec->len1, ctx);
        }
    }

    if (pMyData->sBuff.size() - pMyData->nBuffOffset == 0 &&
        (!ctx->htmlRewrite || ctx->baseFetch == NULL))
    {
        ret = g_api->stream_write_next(rec, (const char *) rec->ptr1, rec->len1);
        if (ret >= 0)
        {
            if (ctx->recorder)
            {
                contents = StringPiece((char *) rec->ptr1, ret);
                InPlaceBodyFilter(pMyData, rec, ctx, contents, ret);
            }

        }
        return ret;
    }

    int len;
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

    if (pMyData->sBuff.size() - pMyData->nBuffOffset <= 0)
    {
        pMyData->sBuff.clear();
        pMyData->nBuffOffset = 0;
    }
    
    if (rec->flag_out)
    {
        if (!doneCalled || pMyData->sBuff.size() - pMyData->nBuffOffset > 0)
            *rec->flag_out |= LSI_CBFO_BUFFERED;
    }

    if (doneCalled && !pMyData->endRespCalled)
    {
        pMyData->endRespCalled = true;
        g_api->end_resp(rec->session);
    }

    if (*rec->flag_out && rec->flag_in == LSI_CBFI_EOF)
        g_api->set_handler_write_state(rec->session, 0);


    g_api->log(rec->session, LSI_LOG_DEBUG,
               "[%s] sendRespBody() flag_in %d, flag out %d, done_called %d, Accumulated %d, write to next %d, buffer data written %d.\n",
               ModuleName, rec->flag_in, *rec->flag_out, doneCalled,
               rec->len1, ret, writtenTotal);

    return ret;

}


void UpdateEtag(lsi_param_t *rec)
{
    struct iovec iov[1] = {{NULL, 0}};
    int iovCount = g_api->get_resp_header(rec->session, -1, kInternalEtagName,
                                          strlen(kInternalEtagName), iov, 1);

    if (iovCount == 1)
    {
        g_api->remove_resp_header(rec->session, -1, kInternalEtagName,
                                  strlen(kInternalEtagName));
        g_api->set_resp_header(rec->session, LSI_RSPHDR_ETAG, NULL, 0,
                               (const char *) iov[0].iov_base,
                               iov[0].iov_len, LSI_HEADEROP_SET);

        //If etag not PAGESPEED style, meas not optimized, so not cahce it
        if (strncasecmp((const char *) iov[0].iov_base, "W/", 2) == 0)
            g_api->set_req_env(rec->session, "cache-control", 13, "no-cache", 8);
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
int HtmlRewriteHeaderFilter(PsMData *pMyData, const lsi_session_t *session,
                            ps_request_ctx_t *ctx, ps_vh_conf_t *cfg_s)
{
    // Poll for cache flush on every request (polls are rate-limited).
    //cfg_s->server_context->FlushCacheIfNecessary();

    if (ctx->htmlRewrite == false)
        return 0;

    if (!CheckPagespeedApplicable(pMyData, session))
    {
        ctx->htmlRewrite = false;
        return 0;
    }

    g_api->log(session, LSI_LOG_DEBUG,
               "[Module:ModPagespeed]http pagespeed html rewrite header filter \"%s\"\n",
               pMyData->urlString.c_str());


    int rc = ResourceHandler(pMyData, session, true,
                             RequestRouting::kResource);

    if (rc != 0)
    {
        ctx->htmlRewrite = false;
        return 0;
    }

    StripHtmlHeaders(session);
    CopyRespHeadersFromServer(session,
                              ctx->baseFetch->response_headers());

    return 0;
}

int revdRespHeader(lsi_param_t *rec)
{
    UpdateEtag(rec);

    ps_vh_conf_t *cfg_s;
    ps_request_ctx_t *ctx;
    PsMData *pMyData = (PsMData *) g_api->get_module_data(rec->session,
                       &MNAME, LSI_DATA_HTTP);

    if (pMyData == NULL || (cfg_s = pMyData->cfg_s) == NULL
        || (ctx = pMyData->ctx) == NULL)
        return 0;

    if (IsPagespeedSubrequest(rec->session, pMyData->userAgent,
                              pMyData->uaLen))
        return 0;

    InPlaceCheckHeaderFilter(pMyData, rec->session, ctx);
    HtmlRewriteHeaderFilter(pMyData, rec->session, ctx, cfg_s);
    HtmlRewriteFixHeadersFilter(pMyData, rec->session, ctx);

    return 0;
}


// Set us up for processing a request.  Creates a request context and determines
// which handler should deal with the request.
RequestRouting::Response RouteRequest(PsMData *pMyData,
                                      const lsi_session_t  *session, bool is_resource_fetch)
{
    ps_vh_conf_t *cfg_s = pMyData->cfg_s;

    if (!cfg_s->serverContext->global_options()->enabled())
    {
        // Not enabled for this server block.
        return RequestRouting::kPagespeedDisabled;
    }

    GoogleString url_string;
    DetermineUrl(session, url_string);
    GoogleUrl url(url_string);

    if (!url.IsWebValid())
    {
        g_api->log(session, LSI_LOG_ERROR, "[%s]invalid url \"%s\".\n",
                   ModuleName, url_string.c_str());
        return RequestRouting::kInvalidUrl;
    }

    if (IsPagespeedSubrequest(session, pMyData->userAgent, pMyData->uaLen))
        return RequestRouting::kPagespeedSubrequest;
    else if (
        url.PathSansLeaf() == dynamic_cast<LsiRewriteDriverFactory *>(
            cfg_s->serverContext->factory())->static_asset_prefix())
        return RequestRouting::kStaticContent;

    const LsiRewriteOptions *global_options = cfg_s->serverContext->Config();
    StringPiece path = url.PathSansQuery();

    if (StringCaseEqual(path, global_options->GetStatisticsPath()))
        return RequestRouting::kStatistics;
    else if (StringCaseEqual(path, global_options->GetGlobalStatisticsPath()))
        return RequestRouting::kGlobalStatistics;
    else if (StringCaseEqual(path, global_options->GetConsolePath()))
        return RequestRouting::kConsole;
    else if (StringCaseEqual(path, global_options->GetMessagesPath()))
        return RequestRouting::kMessages;
    else if ( // The admin handlers get everything under a path (/path/*) while
        // all the other handlers only get exact matches (/path).  So match
        // all paths starting with the handler path.
        !global_options->GetAdminPath().empty() &&
        StringCaseStartsWith(path, global_options->GetAdminPath()))
        return RequestRouting::kAdmin;
    else if (!global_options->GetGlobalAdminPath().empty() &&
             StringCaseStartsWith(path, global_options->GetGlobalAdminPath()) &&
             global_options->GlobalAdminAccessAllowed(url)) {
        return RequestRouting::kGlobalAdmin;
    } else if (global_options->enable_cache_purge() &&
             !global_options->purge_method().empty() &&
             pMyData->method == HTTP_PURGE)
        return RequestRouting::kCachePurge;

    const GoogleString *beacon_url;

    if (IsHttps(session))
        beacon_url = & (global_options->beacon_url().https);
    else
        beacon_url = & (global_options->beacon_url().http);

    if (url.PathSansQuery() == StringPiece(*beacon_url))
        return RequestRouting::kBeacon;

    return RequestRouting::kResource;
}


static int RecvReqHeaderCheck(lsi_param_t *rec)
{
    //init the VHost data
    ps_vh_conf_t *cfg_s = (ps_vh_conf_t *) g_api->get_module_data(
                              rec->session, &MNAME, LSI_DATA_VHOST);

    if (cfg_s == NULL || cfg_s->serverContext == NULL)
    {
        g_api->log(rec->session, LSI_LOG_ERROR,
                   "[%s]recv_req_header_check error, cfg_s == NULL || cfg_s->server_context == NULL.\n",
                   ModuleName);
        return LSI_OK;
    }

    LsiRewriteOptions *pConfig = (LsiRewriteOptions *) g_api->get_config(
                                     rec->session, &MNAME);

    if (!pConfig)
    {
        g_api->log(rec->session, LSI_LOG_ERROR,
                   "[%s]recv_req_header_check error 2.\n", ModuleName);
        return LSI_OK;
    }

    if (!pConfig->enabled())
    {
        g_api->log(rec->session, LSI_LOG_DEBUG,
                   "[%s]recv_req_header_check returned [Not enabled].\n",
                   ModuleName);
        return LSI_OK;
    }

    if (g_api->is_req_handler_registered(rec->session))
        return LSI_OK;
    else
    {
        int aEnableHkpt[] = {LSI_HKPT_HANDLER_RESTART,
                             LSI_HKPT_HTTP_END,
                             LSI_HKPT_RCVD_RESP_HEADER,
                             LSI_HKPT_SEND_RESP_BODY
                            };
        g_api->enable_hook(rec->session, &MNAME, 1, aEnableHkpt, 4);
    }


    char httpMethod[10] = {0};
    int methodLen = g_api->get_req_var_by_id(rec->session,
                    LSI_VAR_REQ_METHOD, httpMethod, 10);
    int method = HTTP_UNKNOWN;

    switch (methodLen)
    {
    case 3:
        if ((httpMethod[0] | 0x20) == 'g')     //"GET"
            method = HTTP_GET;

        break;

    case 4:
        if ((httpMethod[0] | 0x20) == 'h')     //"HEAD"
            method = HTTP_HEAD;
        else if ((httpMethod[0] | 0x20) == 'p')     //"POST"
            method = HTTP_POST;

        break;

    case 5:
        if ((httpMethod[0] | 0x20) == 'p')     //"PURGE"
            method = HTTP_PURGE;
        break;

    default:
        break;
    }

    if (method == HTTP_UNKNOWN)
    {
        g_api->log(rec->session, LSI_LOG_DEBUG,
                   "[%s]recv_req_header_check returned, method %s.\n",
                   ModuleName,
                   httpMethod);
        return 0;
    }

    //cfg_s->server_context->FlushCacheIfNecessary();

    //If URI_MAP called before, should release then first
    PsMData *pMyData = (PsMData *) g_api->get_module_data(rec->session,
                       &MNAME, LSI_DATA_HTTP);

    if (pMyData)
        g_api->free_module_data(rec->session, &MNAME, LSI_DATA_HTTP,
                                ReleaseMydata);

    pMyData = new PsMData;

    if (pMyData == NULL)
    {
        g_api->log(rec->session, LSI_LOG_DEBUG,
                   "[%s]recv_req_header_check returned, can't alloc memory for pMyData.\n",
                   ModuleName);
        return LSI_OK;
    }

    pMyData->ctx = NULL;
    pMyData->uaLen = 0;
    pMyData->statusCode = 0;
    pMyData->respHeaders = NULL;
    pMyData->endRespCalled = 0;
    pMyData->doneCalled = 0;
    pMyData->sBuff = "";
    pMyData->nBuffOffset = 0;
    DetermineUrl(rec->session, pMyData->urlString);
    pMyData->method = (HTTP_METHOD) method;
    pMyData->cfg_s = cfg_s;
    pMyData->userAgent = g_api->get_req_header_by_id(rec->session,
                         LSI_HDR_USERAGENT, &pMyData->uaLen);
    g_api->set_module_data(rec->session, &MNAME, LSI_DATA_HTTP, pMyData);
    RequestRouting::Response response_category =
        RouteRequest(pMyData, rec->session, true);

    int ret;
    g_api->set_req_wait_full_body(rec->session);

    //Disable cache module
    //g_api->set_req_env(rec->session, "cache-control", 13, "no-cache", 8);

    switch (response_category)
    {
    case RequestRouting::kBeacon:
        ret = BeaconHandler(pMyData, rec->session);
        if (ret == 0)
        {
            //statuc_code already set.
            g_api->register_req_handler(rec->session, &MNAME, 0);
            g_api->log(rec->session, LSI_LOG_DEBUG,
                       "[%s]ps_uri_map_filter register_req_handler OK.\n",
                       ModuleName);
        }
        break;

    case RequestRouting::kStaticContent:
    case RequestRouting::kMessages:
        ret = SimpleHandler(pMyData, rec->session, cfg_s->serverContext,
                            response_category);
        if (ret == 0)
        {
            g_api->register_req_handler(rec->session, &MNAME, 0);
            g_api->log(rec->session, LSI_LOG_DEBUG,
                       "[%s]recv_req_header_check register_req_handler OK after call ps_simple_handler.\n",
                       ModuleName);
        }
        break;

    case RequestRouting::kStatistics:
    case RequestRouting::kGlobalStatistics:
    case RequestRouting::kConsole:
    case RequestRouting::kAdmin:
    case RequestRouting::kGlobalAdmin:
    case RequestRouting::kCachePurge:
    case RequestRouting::kResource:
        ret = ResourceHandler(pMyData, rec->session, false,
                              response_category);
        if (ret == 1) //suspended
        {
            g_api->log(rec->session, LSI_LOG_DEBUG,
                       "[%s]recv_req_header_check suspend hook, pData=%p.\n",
                       ModuleName, pMyData);
            return LSI_SUSPEND;
        }
        break;

    default:
        break;
    }

    return LSI_OK;
}


int BaseFetchHandler(PsMData *pMyData, const lsi_session_t *session)
{
    ps_request_ctx_t *ctx = pMyData->ctx;
    int rc = ctx->baseFetch->CollectAccumulatedWrites(session);
    g_api->log(session, LSI_LOG_DEBUG,
               "ps_base_fetch_handler called CollectAccumulatedWrites, ret %d, session=%p\n",
               rc, session);

    if (rc == LSI_OK)
        ctx->fetchDone = true;

    return 0;
}

//This event shoule occur only once!
int EventCb(evtcbhead_s *session_, long, void *)
{
    if (session_ == NULL)
    {
        //session has been closed. PsMData has been released.
        //cleanup pagespeed resouces.
        return -1;
    }
    lsi_session_t *session = (lsi_session_t *) session_;
    //g_api->reset_session_back_ref_ptr(session);
    
    PsMData *pMyData = (PsMData *) g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);
    if (!pMyData)
        return 0;
    
    if (pMyData->ctx->baseFetch)
    {
        if (!pMyData->ctx->fetchDone)
            BaseFetchHandler(pMyData, session);
        else
        {
            CHECK(0);//should NEVER BE HERE since call only once
            pMyData->ctx->baseFetch->CollectAccumulatedWrites(session);
        }
    }

    g_api->log(session, LSI_LOG_DEBUG,
               "[%s]EventCb triggered, session=%p\n",
               ModuleName, session_);

    //For suspended case, use the following to resume
    int status_code =
        pMyData->ctx->baseFetch->response_headers()->status_code();
    bool status_ok = (status_code != 0) && (status_code < 400);
    if (status_ok)
    {
        pMyData->statusCode = status_code;

        //Add below code to avoid register_req_handler when it is only filters.
        if (!pMyData->ctx->htmlRewrite)
        {
            g_api->register_req_handler(session, &MNAME, 0);
            g_api->log(session, LSI_LOG_DEBUG,
                       "[%s]ps_event_cb register_req_handler OK.\n", ModuleName);
        }
    }


    g_api->create_session_resume_event(session, &MNAME);
    g_api->set_handler_write_state(session, 1);
    g_api->log(session, LSI_LOG_DEBUG,
               "[%s]EventCb called, pData=%p.\n", ModuleName, pMyData);
    return 0;
}

static int PsHandlerProcess(const lsi_session_t *session)
{
    PsMData *pMyData = (PsMData *) g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);

    if (!pMyData)
    {
        g_api->log(session, LSI_LOG_ERROR,
                   "[%s]internal error during myhandler_process.\n", ModuleName);
        return 500;
    }

    g_api->set_status_code(session, pMyData->statusCode);

    if (pMyData->respHeaders)
    {
        CopyRespHeadersToServer(session, *pMyData->respHeaders,
                                kDontPreserveHeaders);
    }
    else
    {
        if (pMyData->ctx && pMyData->ctx->baseFetch)
            pMyData->ctx->baseFetch->CollectHeaders(session);
    }
    g_api->remove_resp_header(session, LSI_RSPHDR_CONTENT_LENGTH, NULL, 0);


    AutoStr2 str(MNAME.about);
    str.append("-0", 2); //For handler, make a little difference
    g_api->set_resp_header(session, -1, PAGESPEED_RESP_HEADER,
                           sizeof(PAGESPEED_RESP_HEADER) - 1,
                           str.c_str(), str.len(),
                           LSI_HEADEROP_SET);

    int len;
    while ((len = pMyData->sBuff.size() - pMyData->nBuffOffset) > 0)
    {
        const char *pBuf = pMyData->sBuff.c_str() + pMyData->nBuffOffset;
        int written = g_api->append_resp_body(session, pBuf, len);

        if (written > 0)
            pMyData->nBuffOffset += written;
        else
        {
            g_api->log(session, LSI_LOG_DEBUG,
                       "[%s]internal error during processing.\n", ModuleName);
            return 500;
        }
    }

    pMyData->sBuff.clear();
    pMyData->nBuffOffset = 0;
    g_api->end_resp(session);
    g_api->free_module_data(session, &MNAME, LSI_DATA_HTTP, ReleaseMydata);
    return 0;
}


static lsi_serverhook_t serverHooks[] =
{
    { LSI_HKPT_MAIN_INITED,         PostConfig,         LSI_HOOK_NORMAL,    LSI_FLAG_ENABLED },
    { LSI_HKPT_WORKER_INIT,         ChildInit,          LSI_HOOK_NORMAL,    LSI_FLAG_ENABLED },
    { LSI_HKPT_MAIN_ATEXIT,         TerminateMainConf,  LSI_HOOK_NORMAL,    LSI_FLAG_ENABLED },
    { LSI_HKPT_URI_MAP,             RecvReqHeaderCheck, LSI_HOOK_NORMAL,    LSI_FLAG_ENABLED },
    { LSI_HKPT_HANDLER_RESTART,     EndSession,         LSI_HOOK_NORMAL,    0 },
    { LSI_HKPT_HTTP_END,            EndSession,         LSI_HOOK_NORMAL,    0 },
    { LSI_HKPT_RCVD_RESP_HEADER,    revdRespHeader,     LSI_HOOK_NORMAL,    0 },
    {
        LSI_HKPT_SEND_RESP_BODY,      sendRespBody,       LSI_HOOK_NORMAL,
        LSI_FLAG_TRANSFORM | LSI_FLAG_PROCESS_STATIC | LSI_FLAG_DECOMPRESS_REQUIRED
    },
    LSI_HOOK_END   //Must put this at the end position
};

static int Init(lsi_module_t *pModule)
{
    g_api->init_module_data(pModule, ReleaseMydata, LSI_DATA_HTTP);
    g_api->init_module_data(pModule, ReleaseVhConf, LSI_DATA_VHOST);
    return 0;
}

lsi_confparser_t dealConfig = { ParseConfig, FreeConfig, paramArray };
lsi_reqhdlr_t _handler = { PsHandlerProcess, NULL, NULL, NULL };
lsi_module_t MNAME = { LSI_MODULE_SIGNATURE, Init, &_handler, &dealConfig,
                       MODULE_VERSION_INFO, serverHooks, {0}
                     };

