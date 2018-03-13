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

#include "ls_base_fetch.h"

#include <lsr/ls_atomic.h>

#include "net/instaweb/rewriter/public/rewrite_stats.h"
#include "pagespeed/kernel/base/google_message_handler.h"
#include "pagespeed/kernel/base/message_handler.h"
#include "pagespeed/kernel/base/posix_timer.h"
#include "pagespeed/kernel/http/response_headers.h"
#include <unistd.h>
#include <errno.h>

//LsiBaseFetch* LsiBaseFetch::event_connection = NULL;
int LsiBaseFetch::active_base_fetches = 0;

LsiBaseFetch::LsiBaseFetch(const lsi_session_t *session,
                           LsServerContext *server_context,
                           const RequestContextPtr &request_ctx,
                           PreserveCachingHeaders preserve_caching_headers,
                           BaseFetchType type)
    : AsyncFetch(request_ctx),
      m_pServerContext(server_context),
      m_bDoneCalled(false),
      m_bLastBufSent(false),
      m_lEventObj(0),
      m_iReferences(2),
      m_iType(type),
      m_bIproLookup(false),
      m_bSuccess(false),
      m_preserveCachingHeaders(preserve_caching_headers)
{
    if (pthread_mutex_init(&m_mutex, NULL))
        CHECK(0);
    __sync_add_and_fetch(&LsiBaseFetch::active_base_fetches, 1);
    m_buffer.clear();
}

LsiBaseFetch::~LsiBaseFetch()
{
    m_buffer.clear();
    pthread_mutex_destroy(&m_mutex);
    __sync_add_and_fetch(&LsiBaseFetch::active_base_fetches, -1);
}

const char* BaseFetchTypeToCStr(BaseFetchType type) {
  switch(type) {
    case kPageSpeedResource:
      return "ps resource";
    case kHtmlTransform:
      return "html transform";
    case kAdminPage:
      return "admin page";
    case kIproLookup:
      return "ipro lookup";
    case kPageSpeedProxy:
      return "pagespeed proxy";
  }
  CHECK(false);
  return "can't get here";
}

void LsiBaseFetch::Lock()
{
    pthread_mutex_lock(&m_mutex);
}

void LsiBaseFetch::Unlock()
{
    pthread_mutex_unlock(&m_mutex);
}

bool LsiBaseFetch::HandleWrite(const StringPiece &sp,
                               MessageHandler *handler)
{
    Lock();
    m_buffer.append(sp.data(), sp.size());
    Unlock();
    return true;
}

int LsiBaseFetch::CopyBufferToLs(const lsi_session_t *session)
{
    CHECK(!(m_bDoneCalled && m_bLastBufSent))
            << "CopyBufferToLs() was called after the last buffer was sent";

    if (!m_bDoneCalled && m_buffer.empty())
        return 1;

    CopyRespBodyToBuf(session, m_buffer, m_bDoneCalled /* send_last_buf */);

    m_buffer.clear();

    if (m_bDoneCalled)
    {
        m_bLastBufSent = true;
        return 0;
    }

    return 1;
}

int LsiBaseFetch::CollectAccumulatedWrites(const lsi_session_t *session)
{
    if (m_bLastBufSent)
        return 0;

    int rc;
    Lock();
    rc = CopyBufferToLs(session);
    Unlock();
    return rc;
}

int LsiBaseFetch::CollectHeaders(const lsi_session_t *session)
{
    const ResponseHeaders *pagespeed_headers = response_headers();

    if (content_length_known())
        g_api->set_resp_content_length(session, content_length());

    return CopyRespHeadersToServer(session, *pagespeed_headers,
                                   m_preserveCachingHeaders);
}

void LsiBaseFetch::RequestCollection()
{
    long tmp = AtomicSetEventObj(NULL);
    if (tmp == 0)
        return ;

    IncrementRefCount();
    g_api->schedule_event(tmp, 1);

}

void LsiBaseFetch::HandleHeadersComplete()
{
    int statusCode = response_headers()->status_code();
    bool statusOk = (statusCode != 0 && statusCode < 400);

    if ((m_iType != kIproLookup) || statusOk)
    {
        // If this is a 404 response we need to count it in the stats.
        if (response_headers()->status_code() == HttpStatus::kNotFound)
            m_pServerContext->rewrite_stats()->resource_404_count()->Add(1);
    }

    if (!m_bIproLookup)
    {
        //RequestCollection();  // Headers available.
    }
}

bool LsiBaseFetch::HandleFlush(MessageHandler *handler)
{
    //RequestCollection();
    return true;
}


int LsiBaseFetch::DecrementRefCount() {
  return DecrefAndDeleteIfUnreferenced();
}

int LsiBaseFetch::IncrementRefCount() {
  return __sync_add_and_fetch(&m_iReferences, 1);
}

int LsiBaseFetch::DecrefAndDeleteIfUnreferenced()
{
    // Creates a full memory barrier.
    int r = __sync_add_and_fetch(&m_iReferences, -1);
    if (r == 0)
        delete this;
    return r;
}

void LsiBaseFetch::HandleDone(bool success)
{
    m_bSuccess = success;
//     g_api->log(m_session, LSI_LOG_DEBUG,
//                "[Module:modpagespeed]HandleDone called, success=%d, m_bDoneCalled=%d!\n",
//                success, m_bDoneCalled);

    Lock();
    m_bDoneCalled = true;
    Unlock();
    RequestCollection();
    DecrefAndDeleteIfUnreferenced();
}
