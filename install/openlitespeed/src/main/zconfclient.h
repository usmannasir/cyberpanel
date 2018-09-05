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
#ifndef ZCONFCLIENT_H
#define ZCONFCLIENT_H

#include <util/autostr.h>
#include <util/httpfetch.h>
#include <util/linkedobj.h>


class ZConfClient : public LinkedObj
{
public:
    ZConfClient();
    ~ZConfClient();

    enum
    {
        ZCUP = 0,
        ZCSSL,
        ZCDOWN,
        ZCQUERY,
        ZCRESUME,
        ZCSUSPEND,
        ZCUNKNOWN
    };

    void init(const char *pAdc, int iAdcLen);

    int initFetch(const char *pAuth, int iAuthLen);

    const char *getAdcAddr() const              {   return m_adc.c_str();   }

    /**
     * Send the HttpFetch request.
     *
     * This should be done after the client is initialized.
     *
     * @param[in] reqType The ZConf Request Type enumerated above.
     * @param[in] pConfName The identifying configuration name for this server.
     * @param[in] pReqBody The request body containing the configurations.
     * @return LS_OK on success, LS_FAIL on failure.
     */
    int sendReq(int reqType, const char *pConfName, AutoBuf *pReqBody);

private:

    /**
     * HttpFetch callback. Processes the response status and responds accordingly.
     *
     * If fetch succeeds, nothing more needs to be done.
     * If fetch fails, may need to try to re-send.
     *
     * @param[in] pArg Callback Argument, this class object.
     * @param[in] pFetch The fetch object.
     * @return unused.
     */
    static int processFetch(void *pArg, HttpFetch *pFetch);


    AutoStr2    m_adc;
    HttpFetch   m_fetch;
    int         m_iReqType;

    LS_NO_COPY_ASSIGN(ZConfClient);
};


#endif // ZCONFCLIENT_H
