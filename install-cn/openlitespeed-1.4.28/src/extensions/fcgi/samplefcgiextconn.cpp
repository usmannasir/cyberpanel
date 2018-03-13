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
#include "samplefcgiextconn.h"

#include <lsr/ls_strtool.h>

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

SampleFcgiExtConn::SampleFcgiExtConn()
    : HttpExtConnector()
{
    //m_pBodyBuf = //"A";
    //    "this is the body of sample HTTP request!\n"
    //            "second line .............................................\n"
    //            "third line ...............................................\n"
    //            "fourth line **********************************************\n";
    m_iBodySize = 81920; //strlen( m_pBodyBuf );
    m_iBodySent = 0;
    m_env.add("SERVER_PORT", "80");

    m_env.add("SERVER_ADDR", "192.168.0.1");
    m_env.add("ACCEPT",
              "image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, image/png, */*");
    m_env.add("GATEWAY_INTERFACE", "CGI/1.1");
    m_env.add("REQUEST_METHOD", "POST");
    m_env.add("HTTP_USER_AGENT",
              "Mozilla/4.78 [en] (X11; U; Linux 2.4.18-1smp i686)");
    m_env.add("REQUEST_URI", "/fcgi/echo-cpp");
    char achBuf[ 30];
    ls_snprintf(achBuf, 30, "%d", m_iBodySize);
    m_env.add("CONTENT_LENGTH", achBuf);
    m_env.add("CONTENT_TYPE", "text/plain");
}


SampleFcgiExtConn::~SampleFcgiExtConn()
{
}


int SampleFcgiExtConn::processRespData(const char *pBuf, int len)
{
    return processResp(pBuf, len);
}


int SampleFcgiExtConn::processResp(const char *pBuf, int len)
{
    assert(pBuf);
    assert(len >= 0);
    char *pTemp = (char *)malloc(len + 1);
    memmove(pTemp, pBuf, len);
    *(pTemp + len) = 0;
    printf("%s", pTemp);
    free(pTemp);
    return len;
}


int SampleFcgiExtConn::processErrData(const char *pBuf, int len)
{
    assert(pBuf);
    assert(len >= 0);
    char *pTemp = (char *)malloc(len + 1);
    memmove(pTemp, pBuf, len);
    *(pTemp + len) = 0;
    printf("ERROR:%s", pTemp);
    free(pTemp);
    return 0;
}


int SampleFcgiExtConn::endResponse(int endCode, int protocolStatus)
{
    printf("\n\nEndResponse( endCode=%d, protocolStatus=%d )\n",
           endCode, protocolStatus);
    setState(HEC_COMPLETE);
    return 0;
}


int SampleFcgiExtConn::writeReqBody()
{
    return sendReqBody();
}


int SampleFcgiExtConn::sendReqBody()
{
    printf("enter sendReqBody()!\n");
    char achBuf[20480];
    memset(achBuf, 'A', sizeof(achBuf));
    int toSend = sizeof(achBuf);
    if (toSend + m_iBodySent > m_iBodySize)
        toSend = m_iBodySize - m_iBodySent;
    int ret = getProcessor()->sendReqBody(achBuf, toSend);
    if (ret > 0)
        m_iBodySent += ret;
    if (m_iBodySent >= m_iBodySize)
    {
        setState(getState() & (~HEC_FWD_REQ_BODY));
        getProcessor()->endOfReqBody();
        printf("send req body done!\n");
    }
    return 0;
}


//int SampleFcgiExtConn::sendReqHeader()
//{
//    printf( "enter sendReqHeader()!\n" );
//    int size = m_env.size();
//    int ret = getProcessor()->sendSpecial( m_env.get(), size );
//    setState( HEC_REQ_HEADER_DONE );
//    printf( "req header is done.\n" );
//    getProcessor()->beginReqBody();
//    return ret;
//}


int SampleFcgiExtConn::onWrite(HttpSession *pSession)
{
    return 0;
}


int SampleFcgiExtConn::onRead(HttpSession *pSession)
{
    return 0;
}


void SampleFcgiExtConn::extProcessorReady()
{
    setState(HEC_FWD_REQ_HEADER);
    printf("begin to forward request!\n");
}


int SampleFcgiExtConn::process(HttpSession *pSession)
{
    return 0;
}


void SampleFcgiExtConn::extProcessorError(int errCode)
{
    printf("ext processor error: %d!\n", errCode);
    setState(HEC_COMPLETE);
}


int  SampleFcgiExtConn::cleanUp(HttpSession *pSession)
{
    return 0;
}
