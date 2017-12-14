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
#include <http/staticfilecachedata.h>
#include <main/httpserver.h>
#include <http/httpcontext.h>
#include <http/httpheader.h>
#include <http/httpmime.h>
#include <http/httpreq.h>
#include <http/httpstatuscode.h>
#include <log4cxx/logger.h>
#include <lsiapi/lsiapi.h>
#include <lsr/ls_fileio.h>
#include <lsr/ls_strtool.h>
#include <ssi/ssiscript.h>
#include <util/datetime.h>
#include <util/brotlibuf.h>
#include <util/gzipbuf.h>
#include <util/stringtool.h>
#include <util/vmembuf.h>

#include <openssl/md5.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>
#include <utime.h>

static size_t   s_iMaxInMemCacheSize = 4096;
static size_t   s_iMaxMMapCacheSize = 256 * 1024;



static size_t   s_iMaxTotalInMemCache = DEFAULT_TOTAL_INMEM_CACHE;

static size_t   s_iMaxTotalMMAPCache  = DEFAULT_TOTAL_MMAP_CACHE;
static size_t   s_iCurTotalInMemCache = 0;
static size_t   s_iCurTotalMMAPCache  = 0;

static int      s_iAutoUpdateStaticGzip = 0;
static int      s_iGzipCompressLevel    = 6;
static int      s_iMaxFileSize          = 1024 * 1024;
static int      s_iMinFileSize          = 300;

static int      s_iBrCompressLevel    = 6;

static const char *s_compressCachePath = DEFAULT_TMP_DIR;





void FileCacheDataEx::setTotalInMemCacheSize(size_t max)
{
    s_iMaxTotalInMemCache = max;
}


void FileCacheDataEx::setTotalMMapCacheSize(size_t max)
{
    s_iMaxTotalMMAPCache = max;
}


void FileCacheDataEx::setMaxInMemCacheSize(size_t max)
{
    if (max <= 16384)
        s_iMaxInMemCacheSize = max;
}


void FileCacheDataEx::setMaxMMapCacheSize(size_t max)
{
    s_iMaxMMapCacheSize = max;
}


static int openFile(const char *pPath, int &fd)
{
    fd = ls_fio_open(pPath, O_RDONLY, 0);
    if (fd == -1)
    {
        int err = errno;
        LS_INFO("Failed to open file [%s], error: %s", pPath,
                strerror(err));
        switch (err)
        {
        case EACCES:
            return SC_403;
        case EMFILE:
        case ENFILE:
            return SC_503;
        default:
            return SC_500;
        }
    }
    fcntl(fd, F_SETFD, FD_CLOEXEC);

    return 0;
}


FileCacheDataEx::FileCacheDataEx()
    : m_fd(-1)
{
    memset(&m_iStatus, 0,
           (char *)(&m_pCache + 1) - (char *)&m_iStatus);
}


FileCacheDataEx::~FileCacheDataEx()
{
    release();
    //deallocateCache();
}


void FileCacheDataEx::setFileStat(const struct stat &st)
{
    m_lSize     = st.st_size;
    m_lastMod   = st.st_mtime;
    m_inode     = st.st_ino;
}


int  FileCacheDataEx::allocateCache(size_t size)
{
    assert(m_pCache == NULL);
    int newSize = ((size + 128) >> 7) << 7;
    if (size + s_iCurTotalInMemCache > s_iMaxTotalInMemCache)
        return ENOMEM;
    m_pCache = (char *)malloc(newSize);
    if (!m_pCache)
        return ENOMEM;
    setStatus(CACHED);
    s_iCurTotalInMemCache += size;
    return 0;
}


void FileCacheDataEx::release()
{
    switch (getStatus())
    {
    case MMAPED:
        if (m_pCache)
        {
            LS_DBG_H("[MMAP] Release mapped data at %p", m_pCache);
            munmap(m_pCache, m_lSize);
            s_iCurTotalMMAPCache -= m_lSize;
        }
        break;
    case CACHED:
        if (m_pCache)
        {
            s_iCurTotalInMemCache -= m_lSize;
            free(m_pCache);
        }
        break;
    }
    closefd();
    memset(&m_iStatus, 0,
           (char *)(&m_pCache + 1) - (char *)&m_iStatus);
}


void FileCacheDataEx::closefd()
{
    if (m_fd != -1)
    {
        close(m_fd);
        m_fd = -1;
    }
}


int FileCacheDataEx::readyData(const char *pPath)
{
    int ret;
    if (m_fd == -1)
    {
        ret = openFile(pPath, m_fd);
        if (ret)
            return ret;
    }
    if ((size_t)m_lSize < s_iMaxInMemCacheSize)
    {
        ret = allocateCache(m_lSize);
        if (ret == 0)
        {
            ret = ls_fio_read(m_fd, m_pCache, m_lSize);
            if (ret == m_lSize)
            {
                closefd();
                return 0;
            }
            else
                release();
        }
    }
    else if (((size_t)m_lSize < s_iMaxMMapCacheSize)
             && ((size_t)m_lSize + s_iCurTotalMMAPCache < s_iMaxTotalMMAPCache))
    {
        m_pCache = (char *)mmap(0, m_lSize, PROT_READ,
                                MAP_PRIVATE, m_fd, 0);
        s_iCurTotalMMAPCache += m_lSize;
        LS_DBG_H("[MMAP] Map %p to file:%s", m_pCache, pPath);
        if (m_pCache == MAP_FAILED)
            m_pCache = 0;
        else
        {
            setStatus(MMAPED);
            closefd();
            return 0;
        }
    }
    return 0;
}


const char *FileCacheDataEx::getCacheData(
    off_t offset, off_t &wanted, char *pBuf, long len)
{
    if (isCached())
    {
        if (offset > m_lSize)
        {
            wanted = 0;
            return pBuf;
        }
        if (wanted > m_lSize - offset)
            wanted = m_lSize - offset;
        return m_pCache + offset;
    }
    else
    {
        assert(m_fd != -1);
        off_t off = ls_fio_lseek(m_fd, offset, SEEK_SET);
//        LS_DBG_H( "lseek() return %d", (int)off );
        if (off == offset)
            wanted = ls_fio_read(m_fd, pBuf, len);
        else
            wanted = -1;
        return pBuf;
    }

}


StaticFileCacheData::StaticFileCacheData()
{
    memset(&m_pMimeType, 0,
           (char *)(&m_pBrotli + 1) - (char *)&m_pMimeType);
}


StaticFileCacheData::~StaticFileCacheData()
{
    LsiapiBridge::releaseModuleData(LSI_DATA_FILE, getModuleData());
    if (m_pGzip)
        delete m_pGzip;
    if (m_pBrotli)
        delete m_pBrotli;
    if (m_pSSIScript)
        delete m_pSSIScript;
}


int StaticFileCacheData::testMod(HttpReq *pReq)
{
    const char *pNonMatch;
    if (pReq->isHeaderSet(HttpHeader::H_IF_NO_MATCH))
    {
        pNonMatch = pReq->getHeader(HttpHeader::H_IF_NO_MATCH);
        int len = pReq->getHeaderLen(HttpHeader::H_IF_NO_MATCH);
        if (*pNonMatch == 'W')
        {
            len -= 2;
            pNonMatch += 2;
        }
        if (((m_iETagLen == len)
             && (memcmp(pNonMatch, m_pETag, m_iETagLen) == 0))
            || (*pNonMatch == '*'))
            return SC_304;
    }
    else
    {
        if (pReq->isHeaderSet(HttpHeader::H_IF_MODIFIED_SINCE))
        {
            pNonMatch = pReq->getHeader(HttpHeader::H_IF_MODIFIED_SINCE);
            long IMS = DateTime::parseHttpTime(pNonMatch);
            if (IMS >= m_fileData.getLastMod())
                return SC_304;
        }
    }
    return 0;
}


int StaticFileCacheData::testIfRange(const char *pMatch, int len)
{
    if ((*(pMatch + 1) == '/')
        || (m_fileData.getLastMod() == DateTime::s_curTime))
        return SC_412;
    if (*pMatch == '"')
    {
        if ((m_iETagLen != len)
            || (memcmp(pMatch, m_pETag, m_iETagLen) != 0))
            return SC_412;
    }
    else
    {
        long IUMS = DateTime::parseHttpTime(pMatch);
        if (IUMS < m_fileData.getLastMod())
            return SC_412;
    }
    return 0;
}


int StaticFileCacheData::testUnMod(HttpReq *pReq)
{
    if (m_fileData.getLastMod() == DateTime::s_curTime)
        return SC_412;
    const char *pMatch;
    if (pReq->isHeaderSet(HttpHeader::H_IF_MATCH))
    {
        pMatch = pReq->getHeader(HttpHeader::H_IF_MATCH);
        if (*pMatch != '*')
        {
            int len = pReq->getHeaderLen(HttpHeader::H_IF_MATCH);
            if (*pMatch == 'W')
                return SC_412;
            if ((m_iETagLen != len)
                || (memcmp(pMatch, m_pETag, m_iETagLen) != 0))
                return SC_412;
        }
        return 0;
    }
    if (pReq->isHeaderSet(HttpHeader::H_IF_UNMOD_SINCE))
    {
        pMatch = pReq->getHeader(HttpHeader::H_IF_UNMOD_SINCE);
        long IMS = DateTime::parseHttpTime(pMatch);
        if (IMS < m_fileData.getLastMod())
            return SC_412;
    }
    return 0;
}


static int appendEtagPart(char *p, int maxLen, int &firstPartExist,
                          unsigned long value)
{
    int len = ls_snprintf(p, maxLen, (firstPartExist ? "-%lx" : "%lx"), value);
    firstPartExist = 1;
    return len;
}


int StaticFileCacheData::buildFixedHeaders(int etag)
{
    int size = 6 + 30 + 17 + RFC_1123_TIME_LEN
               + 20 + m_pMimeType->getMIME()->len() + 10 ;
    const char *pCharset;
    if (m_pCharset && HttpMime::needCharset(m_pMimeType->getMIME()->c_str()))
    {
        pCharset = m_pCharset->c_str();
        size += m_pCharset->len();
    }
    else
        pCharset = "";
    if (!m_sHeaders.prealloc(size))
        return SC_500;

    char *pEnd = m_sHeaders.buf() + size;
    char *p = m_sHeaders.buf();
    m_iFileETag = etag;

    if (m_iFileETag & ETAG_ALL)
    {
        memcpy(p, "ETag: \"", 7);
        m_pETag = p + 6;  //Start the etag from the \"

        p += 7;
        int firstPartExist = 0;
        if (m_iFileETag & ETAG_SIZE)
            p += appendEtagPart(p, pEnd - p, firstPartExist,
                                (unsigned long)m_fileData.getFileSize());

        if (m_iFileETag & ETAG_MTIME)
            p += appendEtagPart(p, pEnd - p, firstPartExist, m_fileData.getLastMod());

        if (m_iFileETag & ETAG_INODE)
            p += appendEtagPart(p, pEnd - p, firstPartExist, m_fileData.getINode());

        memcpy(p, "\"\r\n", 3);
        p += 3;
        m_iETagLen = p - m_pETag - 2; //the \r\n not belong to etag
    }
    else
        m_iETagLen = 0;

    memcpy(p, "Last-Modified: ", 15);
    p += 15;
    DateTime::getRFCTime(m_fileData.getLastMod(), p);
    p += RFC_1123_TIME_LEN;

    p += ls_snprintf(p, pEnd - p ,
                     "\r\nContent-Type: %s%s\r\n",
                     m_pMimeType->getMIME()->c_str(), pCharset);

    m_sHeaders.setLen(p - m_sHeaders.buf());
    m_iValidateHeaderLen = (m_iETagLen ? (6 + m_iETagLen + 2) : 0) + 15 + 2 +
                           RFC_1123_TIME_LEN ;
    return 0;
}


int  FileCacheDataEx::buildCLHeader(bool gziped)
{
    int size = 40;
    //if ( gziped )
    //    size += 24;
    if (!m_sCLHeader.prealloc(size))
        return SC_500;
    char *p = m_sCLHeader.buf();
//    if ( gziped )
//    {
//        p += ls_snprintf( p, size,
//            "Content-Encoding: gzip\r\n"
//            "Content-Length: %ld\r\n", getFileSize() );
//    }
//    else
    {
        if (sizeof(off_t) == 8)
        {
            p += ls_snprintf(p, size,
                             "Content-Length: %lld\r\n", (long long)getFileSize());
        }
        else
        {
            p += ls_snprintf(p, size,
                             "Content-Length: %ld\r\n", (long)getFileSize());
        }
    }
    m_sCLHeader.setLen(p - m_sCLHeader.buf());
    return 0;
}


int StaticFileCacheData::buildHeaders(const MimeSetting *pMIME,
                                      const AutoStr2 *pCharset, short etag)
{
    int ret;
    m_pMimeType = pMIME;
    m_pCharset = pCharset;
    ret = buildFixedHeaders(etag);
    if (ret)
        return ret;
    ret = m_fileData.buildCLHeader(false);
    return ret;
}


int StaticFileCacheData::build(int fd, const char   *pPath, int pathLen,
                               const struct stat &fileStat)
{
    m_fileData.setfd(fd);
    m_fileData.setFileStat(fileStat);
    m_real.setStr(pPath, pathLen);
    if (!m_real.c_str())
        return LS_FAIL;
    return 0;
}


static int createLockFile(const char *pReal, char *p)
{
    *p = 'l';       // filename "*.lszl"
    struct stat st;
    int ret = ls_fio_stat(pReal, &st);
    if (ret != -1)    //compression in progress
    {
        //LS_INFO(
        if (DateTime::s_curTime - st.st_mtime > 60)
            unlink(pReal);
        else
        {
            *p = 0;
            return LS_FAIL;
        }
    }
    ret = ::open(pReal, O_RDWR | O_CREAT | O_EXCL, 0600);
    *p = 0;
    return ret;
}


int StaticFileCacheData::tryCreateCompressed(char useBrotli)
{
    AutoStr2 *pPath;
    if (!s_iAutoUpdateStaticGzip)
        return LS_FAIL;
    off_t size = m_fileData.getFileSize();
    if ((size > s_iMaxFileSize) || (size < s_iMinFileSize))
        return LS_FAIL;
    pPath = useBrotli ? &m_bredPath : &m_gzippedPath;
    char *p = pPath->buf() + pPath->len() + 4;
    int fd = createLockFile(pPath->buf(), p);
    if (fd == -1)
        return LS_FAIL;
    close(fd);
    if (size < 409600)
    {

        long ret = compressFile(useBrotli);
        *p = 'l';
        unlink(pPath->buf());
        *p = 0;
        return ret;

    }
    else
    {
        //IMPROVE: move this to a standalone process,
        //          fork() is too expensive.

        LS_DBG_H("To compressed file %s in another process.",
                 m_real.c_str());
        int forkResult;
        forkResult = fork();
        if (forkResult)   //error or parent process
            return LS_FAIL;
        //child process
        setpriority(PRIO_PROCESS, 0, 5);

        long ret = compressFile(useBrotli);
        if (ret == -1)
            LS_WARN("Failed to compress file %s!", m_real.c_str());

        *p = 'l';
        unlink(pPath->buf());
        *p = 0;
        exit(1);
    }
}


int StaticFileCacheData::detectTrancate()
{
    if (!m_fileData.isMapped())
        return 0;
    char ch;
    int fd = m_fileData.getfd();
    if (fd == -1)
    {
        struct stat st;
        int ret = openFile(m_real.c_str(), fd);
        if (ret)
            return LS_FAIL;
        fstat(fd, &st);
        close(fd);
        if (!m_fileData.isDirty(st))
            return 0;

    }
    else
    {
        if (pread(fd, &ch, 1, 0) == 1)
            return 0;
    }
    m_fileData.release();
    return LS_FAIL;

}


int StaticFileCacheData::compressFile(char useBrotli)
{
    int ret;
    AutoStr2 *pPath;

    GzipBuf gzBuf;
    Compressor *pCompressor;
    VMemBuf compressedFile;
    int iCompressLevel;

#ifdef USE_BROTLI
    BrotliBuf brBuf;
    if (useBrotli)
    {
        pCompressor = &brBuf;
        pPath = &m_bredPath;
        iCompressLevel = s_iBrCompressLevel;
    }
    else
    {
#endif
        pCompressor = &gzBuf;
        pPath = &m_gzippedPath;
        iCompressLevel = s_iGzipCompressLevel;
#ifdef USE_BROTLI
    }
#endif

    if (    //detectTrancate() ||
        (0 != pCompressor->init(Compressor::COMPRESSOR_COMPRESS, iCompressLevel)))
        return LS_FAIL;
    if ((!m_fileData.isCached() &&
         (m_fileData.getfd() == -1)))
    {
        if (m_fileData.readyData(m_real.c_str()) != 0)
            return LS_FAIL;
    }

    char achFileName[4096];
    snprintf(achFileName, 4096, "%s.XXXXXX", pPath->c_str());
    int fd = mkstemp(achFileName);
    ret = compressedFile.setFd(achFileName, fd);
    if (ret)
    {
        close(fd);
        return ret;
    }
    pCompressor->setCompressCache(&compressedFile);
    if (pCompressor->beginStream())
        return LS_FAIL;
    off_t offset = 0;
    int len;
    off_t wanted;
    const char *pData;
    char achBuf[8192];
    while (true)
    {
        wanted = getFileSize() - offset;
        if (wanted <= 0)
            break;
        if (wanted < 8192)
            len = wanted;
        else
            len = 8192;
        pData = m_fileData.getCacheData(offset, wanted, achBuf, len);
        if (wanted <= 0)
            return LS_FAIL;
        if (pCompressor->write(pData, wanted) == LS_FAIL)
            return LS_FAIL;
        offset += wanted;

    }
    if (0 == pCompressor->endStream())
    {
        off_t size;
        if (compressedFile.exactSize(&size) == 0)
        {
            compressedFile.close();
            unlink(pPath->buf());
            rename(achFileName, pPath->buf());

            struct utimbuf utmbuf;
            utmbuf.actime = m_fileData.getLastMod();
            utmbuf.modtime = m_fileData.getLastMod();
            utime(pPath->buf(), &utmbuf);

            return size;
        }
    }
    return LS_FAIL;
}


int StaticFileCacheData::buildCompressedCache(FileCacheDataEx *&pData,
                                              const struct stat &st)
{
    if (!pData)
    {
        pData = new FileCacheDataEx();
        if (!pData)
            return LS_FAIL;
    }
    else
        pData->release();

    pData->setFileStat(st);
    if (pData->buildCLHeader(true))
    {
        delete pData;
        pData = NULL;
        return LS_FAIL;
    }
    return 0;
}


int StaticFileCacheData::buildCompressedPaths()
{
    unsigned char achHash[MD5_DIGEST_LENGTH];
    char achPath[4096];
    StringTool::getMd5(m_real.c_str(), m_real.len(), achHash);
    struct stat st;
    int n = snprintf(achPath, 4096, "%s/%x/%x/", s_compressCachePath,
                     achHash[0] >> 4, achHash[0] & 0xf);
    if ((ls_fio_stat(achPath, &st) == -1) && (errno == ENOENT))
    {
        achPath[n - 3] = 0;
        mkdir(achPath, 0700);
        achPath[n - 3] = '/';
        if ((mkdir(achPath, 0700) == -1) && (errno != EEXIST))
            return LS_FAIL;
    }

    StringTool::hexEncode((const char *)&achHash[1], MD5_DIGEST_LENGTH - 1,
                          &achPath[n]);
    n += 30;
    char *pReal = m_gzippedPath.prealloc(n + 6);
    if ((!pReal) || (!m_bredPath.prealloc(n + 6)))
        return LS_FAIL;
    strncpy(pReal, achPath, n);
    m_gzippedPath.setLen(n);
    memmove(pReal + n , ".lsz\0\0", 6);
    if (!m_bredPath.setStr(pReal, n + 6))
        return LS_FAIL;
    char *pBred = m_bredPath.buf();
    pBred[n + 3] = 'b'; // .lsb
    m_bredPath.setLen(n);

    return 0;
}


int StaticFileCacheData::setReadiedCompressData(char compressMode)
{
    if ((compressMode & SFCD_MODE_BROTLI) && (m_pBrotli))
    {
        if ((m_pBrotli->isCached() ||
            (m_pBrotli->getfd() != -1)))
            return 0;
        return m_pBrotli->readyData(m_bredPath.c_str());
    }
    if (m_pGzip)
    {
        if ((m_pGzip->isCached() ||
             (m_pGzip->getfd() != -1)))
            return 0;
        return m_pGzip->readyData(m_gzippedPath.c_str());
    }
    return LS_FAIL;
}


int StaticFileCacheData::compressHelper(AutoStr2 &path, FileCacheDataEx *&pData,
    struct stat &st, int exists, char isBrotli)
{
    int ret;
    if (exists != -1)
        unlink(path.c_str());
    ret = tryCreateCompressed(isBrotli);
    if (ret == -1)
    {
        if (pData)
        {
            delete pData;
            pData = NULL;
        }
        return LS_FAIL;
    }
    else
    {
        ret = ls_fio_stat(path.c_str(), &st);
        if (ret)
            return LS_FAIL;
    }
    return LS_OK;
}


int StaticFileCacheData::readyCompressed(char compressMode)
{
    time_t tm = time(NULL);
    if (tm == getLastMod())
        return LS_FAIL;

    if (tm == m_tmLastCheck)
        return setReadiedCompressData(compressMode);
    int statBr = -1, retGz = -1, statGz = -1;
    struct stat stGzip;
    struct stat stBr;
    m_tmLastCheck = tm;
    // Both paths matter, but bredPath is set last.
    if (!m_bredPath.c_str() || !*m_bredPath.c_str())
    {
        if (buildCompressedPaths() == -1)
            return LS_FAIL;
    }

    if (compressMode & SFCD_MODE_BROTLI)
    {
        statBr = ls_fio_stat(m_bredPath.c_str(), &stBr);
    }
    if (compressMode & SFCD_MODE_GZIP)
    {
        statGz = ls_fio_stat(m_gzippedPath.c_str(), &stGzip);
        retGz = ((statGz == -1)
                || (stGzip.st_mtime != getLastMod()));
    }

    if (compressMode & SFCD_MODE_BROTLI) // brotli active AND not valid
    {
        if ((statBr != -1) && (stBr.st_mtime == getLastMod()))
        {
            // use br

        }
        if (!(compressMode & SFCD_MODE_GZIP) || retGz)
        {
            // update br
            if ((statBr = compressHelper(m_bredPath, m_pBrotli, stBr, statBr, 1)))
                return LS_FAIL;
        }
        else
        {
            compressMode &= ~SFCD_MODE_BROTLI;
        }
    }
    else if ((compressMode & SFCD_MODE_GZIP) && retGz)
    {
        // update gz
        if ((statGz = compressHelper(m_gzippedPath, m_pGzip, stGzip, statGz, 0)))
            return LS_FAIL;
    }
    else if (compressMode & SFCD_MODE_GZIP)
    {
        // use gz

    }
    else
    {
        LS_ERROR("Compress with both Brotli and Gzip turned off.");
        return LS_FAIL;
    }
    if ((compressMode & SFCD_MODE_BROTLI)
        && (statBr != -1) && ((!m_pBrotli) || (m_pBrotli->isDirty(stBr))))
        buildCompressedCache(m_pBrotli, stBr);
    else if ((compressMode & SFCD_MODE_GZIP)
        && (statGz != -1) && ((!m_pGzip) || (m_pGzip->isDirty(stGzip))))
        buildCompressedCache(m_pGzip, stGzip);
    return setReadiedCompressData(compressMode);
}


int StaticFileCacheData::release()
{
    m_fileData.release();
    if (m_pGzip)
        m_pGzip->release();
    if (m_pBrotli)
        m_pBrotli->release();
    return 0;
}


void StaticFileCacheData::setUpdateStaticGzipFile(int enable, int level,
        size_t min, size_t max)
{
    s_iAutoUpdateStaticGzip = enable;
    s_iGzipCompressLevel = level;
    s_iMaxFileSize      = max;
    s_iMinFileSize      = min;
}


void StaticFileCacheData::setCompressCachePath(const char *pPath)
{
    s_compressCachePath = strdup(pPath);
}


const char *StaticFileCacheData::getCompressCachePath()
{
    return s_compressCachePath;
}

void StaticFileCacheData::setStaticBrOptions(int level)
{
    s_iBrCompressLevel = level;
}
