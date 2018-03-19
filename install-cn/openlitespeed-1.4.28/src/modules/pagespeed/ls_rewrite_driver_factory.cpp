/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2016  LiteSpeed Technologies, Inc.                 *
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
#include "ls_rewrite_driver_factory.h"

#include <cstdio>

#include "log_message_handler.h"
#include "ls_message_handler.h"
#include "ls_rewrite_options.h"
#include "ls_server_context.h"

#include "net/instaweb/http/public/rate_controller.h"
#include "net/instaweb/http/public/rate_controlling_url_async_fetcher.h"
#include "net/instaweb/http/public/wget_url_fetcher.h"
#include "net/instaweb/rewriter/public/rewrite_driver.h"
#include "net/instaweb/rewriter/public/rewrite_driver_factory.h"
#include "net/instaweb/rewriter/public/server_context.h"
#include "net/instaweb/util/public/property_cache.h"
#include "pagespeed/kernel/base/google_message_handler.h"
#include "pagespeed/kernel/base/null_shared_mem.h"
#include "pagespeed/kernel/base/posix_timer.h"
#include "pagespeed/kernel/base/stdio_file_system.h"
#include "pagespeed/kernel/base/string.h"
#include "pagespeed/kernel/base/string_util.h"
#include "pagespeed/kernel/base/thread_system.h"
#include "pagespeed/kernel/http/content_type.h"
#include "pagespeed/kernel/sharedmem/shared_circular_buffer.h"
#include "pagespeed/kernel/sharedmem/shared_mem_statistics.h"
#include "pagespeed/kernel/thread/pthread_shared_mem.h"
#include "pagespeed/kernel/thread/scheduler_thread.h"
#include "pagespeed/kernel/thread/slow_worker.h"
#include "pagespeed/system/in_place_resource_recorder.h"
#include "pagespeed/system/serf_url_async_fetcher.h"
#include "pagespeed/system/system_caches.h"
#include "pagespeed/system/system_rewrite_options.h"

namespace net_instaweb
{
class FileSystem;
class Hasher;
class MessageHandler;
class Statistics;
class Timer;
class UrlAsyncFetcher;
class UrlFetcher;
class Writer;

class SharedCircularBuffer;

LsiRewriteDriverFactory::LsiRewriteDriverFactory(
    const ProcessContext &process_context,
    SystemThreadSystem *system_thread_system, StringPiece hostname, int port)
    : SystemRewriteDriverFactory(process_context, system_thread_system,
                                 NULL, hostname, port),
      m_mainConf(NULL),
      m_bThreadsStarted(false),
      m_pLsiMessageHandler(new LsiMessageHandler(timer(),
                           thread_system()->NewMutex())),
      m_pHtmlParseLsiMessageHandler(
          new LsiMessageHandler(timer(), thread_system()->NewMutex())),
      m_pSharedCircularBuffer(NULL),
      m_sHostname(hostname.as_string()),
      m_iPort(port),
      m_bShutDown(false)
{
    InitializeDefaultOptions();
    default_options()->set_beacon_url("/ls_pagespeed_beacon");
    SystemRewriteOptions *system_options =
        dynamic_cast<SystemRewriteOptions *>(default_options());
    system_options->set_file_cache_clean_inode_limit(500000);
    system_options->set_avoid_renaming_introspective_javascript(true);
    set_message_handler(m_pLsiMessageHandler);
    set_html_parse_message_handler(m_pHtmlParseLsiMessageHandler);
}

LsiRewriteDriverFactory::~LsiRewriteDriverFactory()
{
    ShutDown();
    m_pSharedCircularBuffer = NULL;
    STLDeleteElements(&uninitialized_server_contexts_);
}

Hasher *LsiRewriteDriverFactory::NewHasher()
{
    return new MD5Hasher;
}

UrlAsyncFetcher *LsiRewriteDriverFactory::AllocateFetcher(
    SystemRewriteOptions *config)
{
    return SystemRewriteDriverFactory::AllocateFetcher(config);
}

MessageHandler *LsiRewriteDriverFactory::DefaultHtmlParseMessageHandler()
{
    return m_pHtmlParseLsiMessageHandler;
}

MessageHandler *LsiRewriteDriverFactory::DefaultMessageHandler()
{
    return m_pLsiMessageHandler;
}

FileSystem *LsiRewriteDriverFactory::DefaultFileSystem()
{
    return new StdioFileSystem();
}

Timer *LsiRewriteDriverFactory::DefaultTimer()
{
    return new PosixTimer;
}

NamedLockManager *LsiRewriteDriverFactory::DefaultLockManager()
{
    CHECK(false);
    return NULL;
}

RewriteOptions *LsiRewriteDriverFactory::NewRewriteOptions()
{
    LsiRewriteOptions *options = new LsiRewriteOptions(thread_system());
    options->SetRewriteLevel(RewriteOptions::kCoreFilters);
    return options;
}

bool LsiRewriteDriverFactory::InitLsiUrlAsyncFetchers()
{
    return true;
}


LsServerContext *LsiRewriteDriverFactory::MakeLsiServerContext(
    StringPiece hostname, int port)
{
    LsServerContext *server_context = new LsServerContext(this, hostname, port);
    uninitialized_server_contexts_.insert(server_context);
    return server_context;
}

ServerContext *LsiRewriteDriverFactory::NewDecodingServerContext()
{
    ServerContext *sc = new LsServerContext(this, m_sHostname, m_iPort);
    InitStubDecodingServerContext(sc);
    return sc;
}

ServerContext *LsiRewriteDriverFactory::NewServerContext()
{
    LOG(DFATAL) << "MakeLsiServerContext should be used instead";
    return NULL;
}

void LsiRewriteDriverFactory::ShutDown()
{
    if (!m_bShutDown)
    {
        m_bShutDown = true;
        SystemRewriteDriverFactory::ShutDown();
    }
}

void LsiRewriteDriverFactory::ShutDownMessageHandlers()
{
    m_pLsiMessageHandler->set_buffer(NULL);
    m_pHtmlParseLsiMessageHandler->set_buffer(NULL);

    for (LsiMessageHandlerSet::iterator p =
             m_serverContextMessageHandlers.begin();
         p != m_serverContextMessageHandlers.end(); ++p)
        (*p)->set_buffer(NULL);

    m_serverContextMessageHandlers.clear();
}

void LsiRewriteDriverFactory::StartThreads()
{
    if (m_bThreadsStarted)
        return;

    SchedulerThread *thread = new SchedulerThread(thread_system(),
            scheduler());
    bool ok = thread->Start();
    CHECK(ok) << "Unable to start scheduler thread";
    defer_cleanup(thread->MakeDeleter());
    m_bThreadsStarted = true;
}

void LsiRewriteDriverFactory::LoggingInit()
{
    InstallLogMessageHandler();

    if (install_crash_handler())
        LsiMessageHandler::InstallCrashHandler();
}

void LsiRewriteDriverFactory::SetCircularBuffer(
    SharedCircularBuffer *buffer)
{
    m_pSharedCircularBuffer = buffer;
    m_pLsiMessageHandler->set_buffer(buffer);
    m_pHtmlParseLsiMessageHandler->set_buffer(buffer);
}

void LsiRewriteDriverFactory::SetServerContextMessageHandler(
    ServerContext *server_context)
{
    LsiMessageHandler *handler = new LsiMessageHandler(
        timer(), thread_system()->NewMutex());
    // The lsi_shared_circular_buffer_ will be NULL if MessageBufferSize hasn't
    // been raised from its default of 0.
    handler->set_buffer(m_pSharedCircularBuffer);
    m_serverContextMessageHandlers.insert(handler);
    defer_cleanup(new Deleter<LsiMessageHandler> (handler));
    server_context->set_message_handler(handler);
}

void LsiRewriteDriverFactory::InitStats(Statistics *statistics)
{
    // Init standard PSOL stats.
    SystemRewriteDriverFactory::InitStats(statistics);
    RewriteDriverFactory::InitStats(statistics);
    RateController::InitStats(statistics);

    // Init Lsi-specific stats.
    LsServerContext::InitStats(statistics);
    InPlaceResourceRecorder::InitStats(statistics);
}

}  // namespace net_instaweb
