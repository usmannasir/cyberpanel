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
#ifndef LSI_REWRITE_DRIVER_FACTORY_H_
#define LSI_REWRITE_DRIVER_FACTORY_H_

#include <lsdef.h>

#include <set>

#include "pagespeed/kernel/base/md5_hasher.h"
#include "pagespeed/kernel/base/scoped_ptr.h"
#include "pagespeed/system/system_rewrite_driver_factory.h"


// TODO(oschaaf): We should reparent ApacheRewriteDriverFactory and
// LsiRewriteDriverFactory to a new class OriginRewriteDriverFactory and factor
// out as much as possible.

namespace net_instaweb
{
class LsMessageHandler;
class LsRewriteOptions;
class LsServerContext;
class BlockingFetcher;
class SharedCircularBuffer;
class SharedMemRefererStatistics;
class SlowWorker;
class Statistics;
class SystemThreadSystem;

class LsRewriteDriverFactory : public SystemRewriteDriverFactory
{
public:
    explicit LsRewriteDriverFactory(
        const ProcessContext &process_context,
        SystemThreadSystem *system_thread_system, StringPiece hostname, int port);
    virtual ~LsRewriteDriverFactory();
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
    LsServerContext *MakeLsServerContext(StringPiece hostname, int port, 
                                         int uninitialized);
    virtual ServerContext *NewServerContext();

    void StartThreads();

    void SetServerContextMessageHandler(ServerContext *server_context);

    LsMessageHandler *GetLsiMessageHandler()
    {
        return m_pLsMessageHandler;
    }

    virtual void NonStaticInitStats(Statistics *statistics)
    {
        InitStats(statistics);
    }

    void LoggingInit();

    virtual void ShutDownMessageHandlers();

    virtual void SetCircularBuffer(SharedCircularBuffer *buffer);

private:
    Timer *m_timer;

    bool m_bThreadsStarted;
    LsMessageHandler *m_pLsMessageHandler;
    LsMessageHandler *m_pHtmlParseLsiMessageHandler;

    typedef std::set<LsMessageHandler *> LsMessageHandlerSet;
    LsMessageHandlerSet m_serverContextMessageHandlers;

    SharedCircularBuffer *m_pSharedCircularBuffer;

    GoogleString m_sHostname;
    int m_iPort;

    LS_NO_COPY_ASSIGN(LsRewriteDriverFactory);
};

}  // namespace net_instaweb

#endif  // LSI_REWRITE_DRIVER_FACTORY_H_

