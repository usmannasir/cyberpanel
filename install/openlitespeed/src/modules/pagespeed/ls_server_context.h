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
#ifndef LSI_SERVER_CONTEXT_H_
#define LSI_SERVER_CONTEXT_H_

#include "pagespeed.h"
#include <lsdef.h>

#include "ls_message_handler.h"
#include "pagespeed/system/system_server_context.h"


namespace net_instaweb
{
class LsRewriteDriverFactory;
class LsRewriteOptions;
class SystemRequestContext;

class LsServerContext : public SystemServerContext
{
public:
    LsServerContext(
        LsRewriteDriverFactory *factory, StringPiece hostname, int port);
    virtual ~LsServerContext();

    // We expect to use ProxyFetch with HTML.
    virtual bool ProxiesHtml() const
    {
        return true;
    }

    LsRewriteOptions *Config();
    LsRewriteDriverFactory *GetRewriteDriverFactory()
    {
        return m_pRewriteDriverFactory;
    }

    SystemRequestContext *NewRequestContext(lsi_session_t *session);

    LsMessageHandler *MessageHandler()
    {
        return dynamic_cast<LsMessageHandler *>(message_handler());
    }

    virtual GoogleString FormatOption(StringPiece option_name,
                                      StringPiece args);

private:
    LsRewriteDriverFactory *m_pRewriteDriverFactory;


    LS_NO_COPY_ASSIGN(LsServerContext);
};

}  // namespace net_instaweb

#endif  // LSI_SERVER_CONTEXT_H_
