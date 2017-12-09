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
#include "staticfilehandler.h"

#include <http/expiresctrl.h>
#include <http/handlertype.h>
#include <http/httpmethod.h>
#include <http/httpmime.h>
#include <http/httprange.h>
#include <http/httpreq.h>
#include <http/httpresp.h>
#include <http/httpserverconfig.h>
#include <http/httpsession.h>
#include <http/httpstatuscode.h>
#include <http/moov.h>
#include <http/sendfileinfo.h>
#include <http/staticfilecachedata.h>
#include "httpvhost.h"
#include <log4cxx/logger.h>
#include <lsr/ls_strtool.h>
#include <lsr/ls_xpool.h>
#include <util/datetime.h>
#include <util/gzipbuf.h>
#include <util/stringtool.h>

#include <arpa/inet.h>
#include <fcntl.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>


RedirectHandler::RedirectHandler()
    : HttpHandler(HandlerType::HT_REDIRECT)
{
}


RedirectHandler::~RedirectHandler()
{}


const char *RedirectHandler::getName() const
{
    return "redirect";
}


StaticFileHandler::StaticFileHandler()
    : HttpHandler(HandlerType::HT_STATIC)
{
}


const char *StaticFileHandler::getName() const
{
    return "static";
}


StaticFileHandler::~StaticFileHandler()
{}


inline int buildStaticFileHeaders(HttpResp *pResp, HttpReq *pReq,
                                  SendFileInfo *pSendfileInfo)
{
    pResp->setContentLen(pSendfileInfo->getECache()->getFileSize());

    StaticFileCacheData *pData = pSendfileInfo->getFileData();
    const char *p = pData->getHeaderBuf();
    int iETagLen = pData->getETagHeaderLen() - 8;
    if (iETagLen > 0)
    {
        pResp->getRespHeaders().add(HttpRespHeaders::H_ETAG, p + 6, iETagLen);
        p += 6 + iETagLen + 2; //include "\r\n"
    }

    //last modify
    pResp->getRespHeaders().add(HttpRespHeaders::H_LAST_MODIFIED,
                                p + 15, RFC_1123_TIME_LEN);
    p += 15 + RFC_1123_TIME_LEN + 2;

    if (pResp->getRespHeaders().getHeader(HttpRespHeaders::H_CONTENT_TYPE, 
                                          &iETagLen) == NULL)
        pResp->getRespHeaders().add(HttpRespHeaders::H_CONTENT_TYPE,
                                    p + 14, pData->getHeaderLen() -
                                    (p - pData->getHeaderBuf()) - 14 - 2);

    p = pSendfileInfo->getECache()->getCLHeader().c_str();
    pResp->getRespHeaders().add(HttpRespHeaders::H_CONTENT_LENGTH, p + 16,
                                pSendfileInfo->getECache()->getCLHeader().len() - 18);

    pResp->getRespHeaders().appendAcceptRange();

    return 0;
}


static int addExpiresHeader(HttpResp *pResp, StaticFileCacheData *pData,
                            const ExpiresCtrl *pExpires)
{
    time_t expire;
    int    age;
    switch (pExpires->getBase())
    {
    case EXPIRES_ACCESS:
        age = pExpires->getAge();
        expire = DateTime::s_curTime + age;
        break;
    case EXPIRES_MODIFY:
        expire = pData->getLastMod() + pExpires->getAge();
        age = (int)expire - (int)DateTime::s_curTime;
        break;
    default:
        return 0;
    }

    char sTemp[RFC_1123_TIME_LEN + 1] = {0};
    HttpRespHeaders &buf = pResp->getRespHeaders();
    buf.add(HttpRespHeaders::H_CACHE_CTRL, "public, max-age=", 16);
    int n = ls_snprintf(sTemp, RFC_1123_TIME_LEN, "%d", age);
    buf.appendLastVal(sTemp, n);

    DateTime::getRFCTime(expire, sTemp);
    buf.add(HttpRespHeaders::H_EXPIRES, sTemp, RFC_1123_TIME_LEN);
    return 0;
}


#define FLV_MIME "video/x-flv"
#define FLV_HEADER "FLV\x1\x1\0\0\0\x9\0\0\0\x9"
#define FLV_HEADER_LEN (sizeof(FLV_HEADER)-1)

#define MP4_MIME "video/mp4"

static int processFlvStream(HttpSession *pSession, off_t start)
{
    //HttpReq * pReq = pSession->getReq();
    SendFileInfo *pData = pSession->getSendFileInfo();
    int ret = pData->readyCacheData(0);
    if (!ret)
    {
        HttpResp *pResp = pSession->getResp();
        pSession->resetResp();

        pResp->parseAdd(pData->getFileData()->getHeaderBuf(),
                        pData->getFileData()->getHeaderLen());

        pResp->setContentLen(pData->getECache()->getFileSize() -
                             start + FLV_HEADER_LEN);
        //TODO: must be sent out first. would like to avoid using dyn body.
        // just append it to stream level buffer.
        pSession->appendDynBody(FLV_HEADER, FLV_HEADER_LEN);
        pSession->setSendFileBeginEnd(start , pData->getECache()->getFileSize());
        ret = pSession->flush();
    }
    return ret;
}


int calcMoovContentLen(HttpSession *pSession, off_t &contentLen)
{
    int ret = 0;
    SendFileInfo *pData = pSession->getSendFileInfo();

    FileCacheDataEx *pECache = pData->getECache();

    unsigned char *mini_moov = NULL;
    uint32_t mini_moov_size;
    mini_moov = pData->getFileData()->getMiniMoov();
    mini_moov_size = pData->getFileData()->getMiniMoovSize();

    contentLen = 0;

    moov_data_t *moov_data = (moov_data_t *)pData->getParam();
    if (!moov_data)
        return LS_FAIL;

    while (moov_data->remaining_bytes > 0)
    {
        ret = get_moov(
                  pECache->getfd(),
                  moov_data->start_time,
                  0.0,
                  moov_data,
                  mini_moov,
                  mini_moov_size);
        if (ret == -1)
            return LS_FAIL;
        if (moov_data->is_mem == 1)
        {
            contentLen += moov_data->mem.buf_size;
            free(moov_data->mem.buffer);
            moov_data->mem.buffer = NULL;
        }
        else
            contentLen += moov_data->file.data_size;
    }

    //static char mdat_header64[16] = { 0, 0, 0, 1, 'm', 'd', 'a', 't' };
    uint64_t mdat_start;
    uint64_t mdat_size;
    int      mdat_64bit;

    ret = get_mdat(
              pECache->getfd(),
              moov_data->start_time,
              0.0,
              & mdat_start,
              & mdat_size,
              & mdat_64bit,
              mini_moov,
              mini_moov_size);
    if (ret == -1)
        return LS_FAIL;
    if (mdat_64bit)
        contentLen += 16;
    else
        contentLen += 8;
    contentLen += mdat_size;
    return 1;

}


int buildMoov(HttpSession *pSession)
{
    int ret = 0;
    HttpReq *pReq = pSession->getReq();
    SendFileInfo *pData = pSession->getSendFileInfo();

    unsigned char *mini_moov = NULL;
    uint32_t mini_moov_size;
    mini_moov = pData->getFileData()->getMiniMoov();
    mini_moov_size = pData->getFileData()->getMiniMoovSize();

    moov_data_t *moov_data = (moov_data_t *)pData->getParam();
    if (!moov_data)
        return LS_FAIL;

    FileCacheDataEx *pECache = pData->getECache();
    while (moov_data->remaining_bytes > 0)
    {
        ret = get_moov(
                  pECache->getfd(),
                  moov_data->start_time,
                  0.0,
                  moov_data,
                  mini_moov,
                  mini_moov_size);
        if (ret == -1)
            return LS_FAIL;
        if (moov_data->is_mem == 1)
        {
            LS_DBG_L(pReq->getLogSession(), "is_mem, buf_size=%u, remaining=%d",
                     moov_data->mem.buf_size, moov_data->remaining_bytes);
            pSession->appendDynBody((char *)moov_data->mem.buffer,
                                    moov_data->mem.buf_size);
            free(moov_data->mem.buffer);
            moov_data->mem.buffer = NULL;
        }
        else
        {
            //pSession->flushDynBodyChunk();
            LS_DBG_L(pReq->getLogSession(),
                     "Send from file, start=%u, buf_size=%u, remaining=%d",
                     (uint32_t)moov_data->file.start_offset,
                     moov_data->file.data_size,
                     moov_data->remaining_bytes);
            pSession->setSendFileBeginEnd(moov_data->file.start_offset,
                                          moov_data->file.start_offset + moov_data->file.data_size);
            return 1;
            //sendfile( pECache->getfd(), moov_data.file.start_offset,
            //            moov_data.file.data_size );
            //fseek(infile, moov_data.file.start_offset, SEEK_SET);
            //copy_data(infile, outfile, moov_data.file.data_size);
        }
    }

    pSession->getReq()->clearContextState(MP4_SEEK);

    static char mdat_header64[16] = { 0, 0, 0, 1, 'm', 'd', 'a', 't' };
    uint64_t mdat_start;
    uint64_t mdat_size;
    int      mdat_64bit;
    uint32_t *pLen32;

    ret = get_mdat(
              pECache->getfd(),
              moov_data->start_time,
              0.0,
              & mdat_start,
              & mdat_size,
              & mdat_64bit,
              mini_moov,
              mini_moov_size);
    free(moov_data);
    pData->setParam(NULL);
    if (ret == -1)
        return LS_FAIL;
    LS_DBG_L(pReq->getLogSession(),
             "mdat_start=%u, mdat_size=%u, mdat_64bit=%d",
             (uint32_t)mdat_start, (uint32_t)mdat_size, mdat_64bit);
    pLen32 = (uint32_t *)(&mdat_header64[8]);
    if (mdat_64bit)
    {
        *pLen32++ = htonl((uint32_t)((mdat_size + 16) >> 32));
        *pLen32 = htonl((uint32_t)((mdat_size + 16) & 0xffffffff));
        pSession->appendDynBody(mdat_header64, 16);
    }
    else
    {
        *pLen32 = htonl((uint32_t)((mdat_size + 8) & 0xffffffff));
        memmove(&mdat_header64[12], "mdat", 4);
        pSession->appendDynBody(&mdat_header64[8], 8);
    }
    //pSession->flushDynBodyChunk();
    pSession->setSendFileBeginEnd(mdat_start , mdat_start + mdat_size);
    return 1;

}


int processH264Stream(HttpSession *pSession, double start)
{
    HttpReq *pReq = pSession->getReq();
    SendFileInfo *pData = pSession->getSendFileInfo();

    int ret = pData->readyCacheData(0);
    if (ret)
        return ret;
    unsigned char *mini_moov = NULL;
    uint32_t mini_moov_size;
    mini_moov = pData->getFileData()->getMiniMoov();
    FileCacheDataEx *pECache = pData->getECache();
    if (!mini_moov)
    {
        if (get_mini_moov(pECache->getfd(),     //in - video file descriptor
                          &mini_moov,                     //out
                          &mini_moov_size                 //out
                         ) == 1)
            pData->getFileData()->setMiniMoov(mini_moov, mini_moov_size);
        else
        {
            LS_NOTICE(pReq->getLogSession(),
                      "Failed to parse moov header from MP4/H.264 video file [%s].",
                      pReq->getRealPath()->c_str());
            return SC_500;
        }
    }

    moov_data_t *moov_data;
    moov_data = (moov_data_t *)malloc(sizeof(moov_data_t));
    if (!moov_data)
        return SC_500;
    pSession->getReq()->orContextState(MP4_SEEK);
    pData->setParam(moov_data);
    moov_data->remaining_bytes = 1;  //first call
    moov_data->start_time = start;

    pSession->resetResp();

    off_t contentLen = 0;
    if (calcMoovContentLen(pSession, contentLen) == -1)
    {
        LS_NOTICE(pReq->getLogSession(),
                  "Failed to calculate content length for seek request for MP4/H.264 video file [%s].",
                  pReq->getRealPath()->c_str());
        return SC_500;
    }
    pSession->getResp()->setContentLen(contentLen);

//    pSession->setupRespCache();
    //pSession->getReq()->setVersion( HTTP_1_0 );
    pSession->getReq()->keepAlive(0);
    pSession->getResp()->getRespHeaders().add(HttpRespHeaders::H_CONTENT_TYPE,
            "video/mp4", 9);


    moov_data->remaining_bytes = 1;  //first call
    ret = buildMoov(pSession);
    if (ret <= 1)
        ret = pSession->flush();
    return ret;
}


static int processRange(HttpSession *pSession, HttpReq *pReq,
                        const char *pRange);


////////////////////////////////////////////////////////////
//      Internal functions end
////////////////////////////////////////////////////////////

int StaticFileHandler::process(HttpSession *pSession,
                               const HttpHandler *pHandler)
{
    int ret;
    HttpReq *pReq = pSession->getReq();
    HttpResp *pResp = pSession->getResp();
    struct stat &st = pReq->getFileStat();
    int code = pReq->getStatusCode();

    int isSSI = (pReq->getSSIRuntime() != NULL);

//     if (pReq->getMethod() >= HttpMethod::HTTP_POST)
//         return SC_405;
    SendFileInfo *pInfo = pSession->getSendFileInfo();
    const AutoStr2 *pPath = pReq->getRealPath();

    if (pPath)
    {
        ret = pSession->setUpdateStaticFileCache(pPath->c_str(),
                pPath->len(),
                pReq->transferReqFileFd(), pReq->getFileStat());
        if (ret)
            return ret;
    }
    StaticFileCacheData *pCache = pInfo->getFileData();

    if (pSession->getFlag(HSF_STX_FILE_CACHE_READY))
        pReq->setMimeType(pCache->getMimeType());

    if (pCache->needUpdateHeaders(pReq->getMimeType(),
                                  pReq->getDefaultCharset(), pReq->getETagFlags()))
    {
        pCache->buildHeaders(pReq->getMimeType(),
                             pReq->getDefaultCharset(), pReq->getETagFlags());
    }
    unsigned int bitReq =
        HttpServerConfig::getInstance().getRequiredBits();
    if (((st.st_mode & bitReq) != bitReq) ||
        ((st.st_mode & HttpServerConfig::getInstance().getForbiddenBits())))
    {
        if (!pReq->getMimeType()->getExpires()->isImage())
        {
            LS_INFO(pReq->getLogSession(), "Permission of file [%s] does not "
                    "meet the requirements of 'Required bits' or "
                    "'Restricted bits', access denied.",
                    pReq->getRealPath()->c_str());
            return SC_403;
        }
    }

    //if ( code == SC_200 )
    if ((!isSSI) && (code == SC_200))
    {
        if ((pReq->getQueryStringLen() >= 7) &&
            (strcmp(pCache->getMimeType()->getMIME()->c_str(),
                    FLV_MIME) == 0))
        {
            const char *pQS = pReq->getQueryString();
            const char *p = pQS - 1;
            if ((strncmp(pQS, "start=", 6) == 0) ||
                ((p = strstr(pQS, "&start="))))
            {
                p += 7;
                off_t start = strtoll(p, NULL, 10);
                if ((start > 0) && (start < st.st_size))
                    return processFlvStream(pSession, start);
            }
        }
        if ((pReq->getQueryStringLen() >= 7) &&
            (strcmp(pCache->getMimeType()->getMIME()->c_str(),
                    MP4_MIME) == 0))
        {
            const char *pQS = pReq->getQueryString();
            const char *p = pQS - 1;
            if ((strncmp(pQS, "start=", 6) == 0) ||
                ((p = strstr(pQS, "&start="))))
            {
                p += 7;
                double start = strtod(p, NULL);
                if (start > 0.0)
                {
                    ret = processH264Stream(pSession, start);
                    if (ret >= 0)
                        return ret;
                }
            }
        }
        if (pReq->isHeaderSet(HttpHeader::H_RANGE))
        {
            const char *pRange = pReq->getHeader(HttpHeader::H_RANGE);
            if (pReq->isHeaderSet(HttpHeader::H_IF_RANGE))
            {
                const char *pIR = pReq->getHeader(HttpHeader::H_IF_RANGE);
                ret = pCache->testIfRange(pIR
                                          , pReq->getHeaderLen(HttpHeader::H_IF_RANGE));
            }
            else
            {
                ret = pCache->testUnMod(pReq);
                if (ret)
                    return ret;
            }
            if (!ret && pInfo->getFileData()->getFileSize() > 0)
                return processRange(pSession, pReq, pRange);
        }
        else
        {
            if (pCache->testMod(pReq))
            {
                pReq->setStatusCode(SC_304);
                pReq->setNoRespBody();
                code = SC_304;
            }
        }
    }

    char compressed = (((pReq->gzipAcceptable() == GZIP_REQUIRED)
                        || (pReq->brAcceptable() == BR_REQUIRED)) &&
                       ((pSession->getSessionHooks()->getFlag(LSI_HKPT_RECV_RESP_BODY)
                         | pSession->getSessionHooks()->getFlag(LSI_HKPT_SEND_RESP_BODY))
                        & LSI_FLAG_DECOMPRESS_REQUIRED) == 0);
    char mode = (pReq->gzipAcceptable() == GZIP_REQUIRED); // MODE_GZIP = 1
    if (pReq->brAcceptable() == BR_REQUIRED
        && !(pReq->gzipAcceptable() & (GZIP_ADD_ENCODING | GZIP_OFF)))
        mode |= SFCD_MODE_BROTLI;
    ret = pInfo->readyCacheData(compressed, mode);
    LS_DBG_L(pReq->getLogSession(), "readyCacheData() return %d", ret);
    FileCacheDataEx *pECache = pInfo->getECache();
    
    
    if (!ret)
    {
        if (pReq->isKeepAlive())
            pReq->smartKeepAlive(pCache->getMimeType()->getMIME()->c_str());
        if (!isSSI)
        {
            pSession->resetResp();
//            pResp->prepareHeaders( pReq, 1 );
            switch (code)
            {
            case SC_304:
                pResp->parseAdd(pCache->getHeaderBuf(),
                                pCache->getETagHeaderLen());
                break;
            case SC_200:
                {
                    const ExpiresCtrl *pExpireDefault = pReq->shouldAddExpires();
                    if (pExpireDefault)
                    {
                        ret = addExpiresHeader(pResp, pCache, pExpireDefault);
                        if (ret)
                            return ret;
                    }
                    if (pReq->getRedirHdrs())
                    {
                        pResp->parseAdd(pReq->getRedirHdrs(),
                                        pReq->getRedirHdrsLen());
                    }
                }
            //fall through
            default:

                buildStaticFileHeaders(pResp, pReq, pInfo);
                if (pECache == pCache->getBrotli())
                {
                    pResp->addBrotliEncodingHeader();
                    pReq->orBr(UPSTREAM_BR);
                }
                if (pECache == pCache->getGzip())
                {
                    pResp->addGzipEncodingHeader();
                    pReq->orGzip(UPSTREAM_GZIP);
                }
                pSession->setSendFileBeginEnd(0, pInfo->getECache()->getFileSize());
            }
        } //Xuedong Add for SSI Start
        else
        {
            //pSession->flushDynBody( 1 );
            if (pSession->getGzipBuf() &&
                (pECache != pCache->getGzip()))
            {
                if (!pSession->getGzipBuf()->isStreamStarted())
                    pSession->getGzipBuf()->reinit();
            }
            else
                pSession->flushDynBodyChunk();

            pSession->setSendFileBeginEnd(0, pInfo->getECache()->getFileSize());
        }
        //ret = pSession->flush();
        ret = pSession->endResponse(1);
    }
    if (ret == 0 && !pSession->getFlag(HSF_STX_FILE_CACHE_READY))
    {
        HttpVHost *host = (HttpVHost *)pSession->getReq()->getVHost();
        host->addUrlStaticFileMatch(pInfo->getFileData(),
                                    pReq->getOrgReqURL(), pReq->getOrgReqURLLen());
        LS_DBG_L( pSession->getLogSession(), "[static file cache] create cache." );
    }
    return ret;

}


int StaticFileHandler::cleanUp(HttpSession *pSession)
{
    return 0;
}


static int sendMultipart(HttpSession *pSession, HttpRange &range);


int StaticFileHandler::onWrite(HttpSession *pSession)
{
    int ret = 0;
    HttpRange *range = pSession->getReq()->getRange();
    if ((range) && (range->count() > 1))
        return sendMultipart(pSession, *range);
    else
    {
        if (pSession->getReq()->getContextState(MP4_SEEK))
            return buildMoov(pSession);
    }
    pSession->setRespBodyDone();
    return ret;
}


bool StaticFileHandler::notAllowed(int Method) const
{
    return (Method >= HttpMethod::HTTP_POST);
}


static int buildRangeHeaders(HttpSession *pSession, HttpRange &range)
{
    HttpResp *pResp = pSession->getResp();
    SendFileInfo *pData1 = pSession->getSendFileInfo();
    StaticFileCacheData *pData = pData1->getFileData();
    off_t bodyLen;
    HttpRespHeaders &buf = pResp->getRespHeaders();

    if (range.count() == 1)
    {
        const char *p = pData->getHeaderBuf();
        //pResp->parseAdd(pData->getHeaderBuf(), pData->getHeaderLen());
        int iETagLen = pData->getETagHeaderLen() - 8;
        if (iETagLen > 0)
        {
            pResp->getRespHeaders().add(HttpRespHeaders::H_ETAG,
                                        p + 6, iETagLen);
            p += 6 + iETagLen + 2; //include "\r\n"
        }

        //last modify
        pResp->getRespHeaders().add(HttpRespHeaders::H_LAST_MODIFIED,
                                    p + 15, RFC_1123_TIME_LEN);
        p += 15 + RFC_1123_TIME_LEN + 2;

        pResp->getRespHeaders().add(HttpRespHeaders::H_CONTENT_TYPE,
                                    p + 14, pData->getHeaderLen() -
                                    (p - pData->getHeaderBuf()) - 14 - 2);

        off_t begin, end;
        int ret = range.getContentOffset(0, begin, end);
        if (ret)
            return SC_500;

        char sTemp[8192];
        ret = range.getContentRangeString(0, sTemp, 8191);
        if (ret == -1)
            return SC_500;
        buf.parseAdd(sTemp, ret);

        bodyLen = end - begin;
        pResp->setContentLen(bodyLen);

        //TODO: simplify logic with sendMultipart()
        pSession->setSendFileBeginEnd(begin, end);
        pSession->endResponse(1);
    }
    else
    {
        pResp->parseAdd(pData->getHeaderBuf(), pData->getValidateHeaderLen());
        range.beginMultipart();
        buf.add(HttpRespHeaders::H_CONTENT_TYPE,
                "multipart/byteranges; boundary=", 31);
        buf.appendLastVal(range.getBoundary(), strlen(range.getBoundary()));
        bodyLen = range.getMultipartBodyLen(pData->getMimeType()->getMIME());
        pResp->setContentLen(bodyLen);
        pSession->sendRespHeaders();
        return sendMultipart(pSession, range);

    }
    return 0;
}


static int sendMultipart(HttpSession *pSession, HttpRange &range)
{
    off_t iRemain;
    int  ret = 0;
    SendFileInfo *pData = pSession->getSendFileInfo();
    int headerLen;
    while (true)
    {
        headerLen = range.getPartHeaderLen();
        iRemain = pData->getRemain();
        if (!iRemain && headerLen == 0)
        {
            if (range.more())
            {
                range.next();
                range.buildPartHeader(
                    pData->getFileData()->getMimeType()->getMIME()->c_str());
                headerLen = range.getPartHeaderLen();
            }
        }
        if (headerLen)
        {
            ret = pSession->writeRespBody(range.getPartHeader(), headerLen);
            LS_DBG_L(pSession->getLogger(), "[%s] send part header %d bytes",
                     pSession->getLogId(), ret);

            if (ret > 0)
            {
                int r = ret;
                range.partHeaderSent(ret);
                if (r < headerLen)
                    return 1;
            }
            else if (ret == -1)
                return -1;
            else if (!ret)
                return 1;
        }
        if (range.more())
        {
            off_t begin, end;
            range.getContentOffset(begin, end);
            pSession->setSendFileBeginEnd(begin, end);
            iRemain = pData->getRemain();
            assert(iRemain > 0);
            ret = pSession->flush();
            if (ret)
                return ret;
        }
        else
        {
            pSession->endResponse(1);
            break;
        }
    }
    return 0;

}


static int processRange(HttpSession *pSession, HttpReq *pReq,
                        const char *pRange)
{
    SendFileInfo *pData = pSession->getSendFileInfo();
    StaticFileCacheData *pCache = pData->getFileData();
    ls_xpool_t *pPool = pSession->getReq()->getPool();
    HttpRange *range = new(ls_xpool_alloc(pPool,
                                          sizeof(HttpRange)))HttpRange(pCache->getFileSize());

    LS_DBG_L(pReq->getLogger(), "[%s] Range: %.*s",
             pReq->getLogId(), pReq->getHeaderLen(HttpHeader::H_RANGE), pRange);

    int ret = range->parse(pRange, pPool);
    if (ret)
    {
        pReq->setContentLength(pCache->getFileSize());
        ls_xpool_free(pPool, range);
        if (ret == SC_416)    //Range unsatisfiable
        {
            HttpRespHeaders &buf = pSession->getResp()->getRespHeaders();
            buf.add(HttpRespHeaders::H_CONTENT_RANGE, "bytes */", 8);

            int n;
            char sTemp[32] = {0};
            n = StringTool::offsetToStr(sTemp, 30, pCache->getFileSize());
            buf.appendLastVal(sTemp, n);
        }
    }
    else
    {
        pReq->setStatusCode(SC_206);
        pReq->setRange(range);
        ret = pData->readyCacheData(0);
        if (!ret)
        {
            //HttpResp * pResp = pSession->getResp();
            pSession->resetResp();
            ret = buildRangeHeaders(pSession, *range);
            if (!ret)
                ret = pSession->flush();
        }
    }
    return ret;
}

