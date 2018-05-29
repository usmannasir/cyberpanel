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
#ifndef LSI_REWRITE_DRIVER_FACTORY_H_
#define LSI_REWRITE_DRIVER_FACTORY_H_

#include <lsdef.h>
#include <set>

#include "pagespeed/kernel/base/md5_hasher.h"
#include "pagespeed/kernel/base/scoped_ptr.h"
#include "pagespeed/system/system_rewrite_driver_factory.h"

namespace net_instaweb
{
class LsiMessageHandler;
class LsiRewriteOptions;
class LsServerContext;
class BlockingFetcher;
class SharedCircularBuffer;
class SharedMemRefererStatistics;
class SlowWorker;
class Statistics;
class SystemThreadSystem;

class LsiRewriteDriverFactory : public SystemRewriteDriverFactory
{
public:
    explicit LsiRewriteDriverFactory(
        const ProcessContext &process_context,
        SystemThreadSystem *system_thread_system, StringPiece hostname, int port);
    virtual ~LsiRewriteDriverFactory();
    virtual Hasher *NewHasher();
    virtual UrlAsyncFetcher *AllocateFetcher(SystemRewriteOptions *config);
    virtual MessageHandler *DefaultHtmlParseMessageHandler();
    virtual MessageHandler *DefaultMessageHandler();
    virtual FileSystem *DefaultFileSystem();
    virtual Timer *DefaultTimer();
    virtual NamedLockManager *DefaultLockManager();
    virtual RewriteOptions *NewRewriteOptions();
    virtual ServerContext *NewDecodingServerContext();
    bool InitLsiUrlAsyncFetchers();

    static void InitStats(Statistics *statistics);
    LsServerContext *MakeLsiServerContext(StringPiece hostname, int port);
    virtual ServerContext *NewServerContext();
    virtual void ShutDown();

    void StartThreads();

    void SetServerContextMessageHandler(ServerContext *server_context);

    LsiMessageHandler *GetLsiMessageHandler()
    {
        return m_pLsiMessageHandler;
    }

    virtual void NonStaticInitStats(Statistics *statistics)
    {
        InitStats(statistics);
    }

    void SetMainConf(LsiRewriteOptions *main_conf)
    {
        m_mainConf = main_conf;
    }

    void LoggingInit();

    virtual void ShutDownMessageHandlers();

    virtual void SetCircularBuffer(SharedCircularBuffer *buffer);

private:
    Timer *m_timer;

    LsiRewriteOptions *m_mainConf;

    bool m_bThreadsStarted;
    LsiMessageHandler *m_pLsiMessageHandler;
    LsiMessageHandler *m_pHtmlParseLsiMessageHandler;

    typedef std::set<LsiMessageHandler *> LsiMessageHandlerSet;
    LsiMessageHandlerSet m_serverContextMessageHandlers;

    SharedCircularBuffer *m_pSharedCircularBuffer;

    GoogleString m_sHostname;
    int m_iPort;
    bool m_bShutDown;

    LS_NO_COPY_ASSIGN(LsiRewriteDriverFactory);
};

}  // namespace net_instaweb

#endif  // LSI_REWRITE_DRIVER_FACTORY_H_

