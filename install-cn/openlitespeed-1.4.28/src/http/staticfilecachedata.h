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
#ifndef STATICFILECACHEDATA_H
#define STATICFILECACHEDATA_H



#include <http/cacheelement.h>
#include <util/autostr.h>
#include <lsiapi/lsimoduledata.h>

#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>


#define  DEFAULT_TOTAL_INMEM_CACHE (1024 * 1024 * 20)     // 20M
#define  DEFAULT_TOTAL_MMAP_CACHE  (1024 * 1024 * 20)     // 20M

class HttpReq;
class StaticFileCacheData;
class MimeSetting;
class SSIScript;

class FileCacheDataEx : public RefCounter
{
    friend class StaticFileCacheData;

    AutoStr2        m_sCLHeader;
    off_t           m_lSize;
    ino_t           m_inode;
    time_t          m_lastMod;
    int             m_fd;
    int             m_iStatus;
    char           *m_pCache;

    FileCacheDataEx(const FileCacheDataEx &rhs);
    void operator=(const FileCacheDataEx &rhs);
protected:
    FileCacheDataEx();
    ~FileCacheDataEx();
    int  allocateCache(size_t size);

    void setCache(char *pCache)  {   m_pCache = pCache;  }
    const char *getCache() const   {   return m_pCache;    }
    void setFileSize(off_t size)   {   m_lSize = size;     }
    int  buildCLHeader(bool gziped);
    time_t getLastMod() const       {   return m_lastMod;   }
    ino_t getINode() const          {   return m_inode;     }
    void setFileStat(const struct stat &st);

public:
    enum
    {
        NONE,
        MMAPED,
        CACHED

    };

    const AutoStr2 &getCLHeader() const  {   return m_sCLHeader; }

    void setStatus(int status)    {   m_iStatus = status; }
    int  getStatus()  const         {   return m_iStatus;   }

    int  isCached() const           {   return m_iStatus;  }
    int  isMapped() const
    {   return (m_iStatus == MMAPED);     }

    bool isDirty(const struct stat &fileStat) const
    {
        return ((getFileSize() != fileStat.st_size)
                || (m_inode != fileStat.st_ino)
                || (m_lastMod != fileStat.st_mtime));
    }

    void setfd(int fd)            {   m_fd = fd;          }
    int  getfd() const              {   return m_fd;        }
    void closefd();

    off_t getFileSize() const       {   return m_lSize;     }

    const char *getCacheData(off_t offset, off_t &wanted, char *pBuf,
                             long len);

    int readyData(const char *pPath);

    void release();

    static void setMaxInMemCacheSize(size_t max);
    static void setMaxMMapCacheSize(size_t max);

    static void setTotalInMemCacheSize(size_t max);
    static void setTotalMMapCacheSize(size_t max);


};

#define SFCD_MODE_GZIP      (1<<0)
#define SFCD_MODE_BROTLI    (1<<1)

class StaticFileCacheData : public CacheElement
{
    AutoStr2        m_real;
    AutoStr2        m_gzippedPath;
    AutoStr2        m_bredPath;
    AutoStr2        m_sHeaders;

    const MimeSetting *m_pMimeType;
    const AutoStr2     *m_pCharset;

    char           *m_pETag;
    int             m_iETagLen;
    short           m_iFileETag;
    int             m_iValidateHeaderLen;
    SSIScript      *m_pSSIScript;


    unsigned char  *m_pMiniMoov;
    int             m_iMiniMoovSize;

    LsiModuleData   m_moduleData;

    time_t          m_tmLastCheck;
    FileCacheDataEx *m_pGzip;
    FileCacheDataEx *m_pBrotli;
    FileCacheDataEx m_fileData;

    StaticFileCacheData(const StaticFileCacheData &rhs);
    void operator=(const StaticFileCacheData &rhs);

    int buildFixedHeaders(int etag);
    int buildCompressedCache(FileCacheDataEx *&pData, const struct stat &st);
    int tryCreateCompressed(char useBrotli);
    
    int buildCompressedPaths();
    int detectTrancate();

    int setReadiedCompressData(char compressMode);
    int compressHelper(AutoStr2 &path, FileCacheDataEx *&pData,
        struct stat &st, int exists, char isBrotli);
public:

    int readyCompressed(char compressMode);
    const AutoStr2 * getRealPath() { return  &m_real; }
    off_t getFileSize() const   {   return m_fileData.getFileSize();    }

    void setMimeType(const MimeSetting *pType) {  m_pMimeType = pType;  }
    const MimeSetting *getMimeType() const    {   return m_pMimeType;   }

    void setCharset(const AutoStr2 *p)  {   m_pCharset = p;             }

    int  getHeaderLen() const           {   return m_sHeaders.len();    }
    const char *getHeaderBuf() const    {   return m_sHeaders.c_str();  }
    int  getValidateHeaderLen() const   {   return m_iValidateHeaderLen;}
    int  getETagHeaderLen() const       {   return m_iETagLen + 8;      }

    StaticFileCacheData();
    ~StaticFileCacheData();
    virtual const char *getKey() const  {   return m_real.c_str();      }
    int build(int fd, const char   *pPath, int pathLen,
              const struct stat &fileStat);
    FileCacheDataEx *getGzip() const    {   return m_pGzip;             }
    FileCacheDataEx *getBrotli() const  {   return m_pBrotli;           }
    const FileCacheDataEx *getFileData() const {   return &m_fileData;  }
    FileCacheDataEx *getFileData()      {   return &m_fileData;         }

    SSIScript *getSSIScript() const     {   return m_pSSIScript;        }
    void setSSIScript(SSIScript *p)     {   m_pSSIScript = p;           }

    void setMiniMoov(unsigned char *p, int size)
    {   m_pMiniMoov = p;  m_iMiniMoovSize = size;      }
    unsigned char *getMiniMoov() const  {   return m_pMiniMoov;         }
    int getMiniMoovSize() const         {   return m_iMiniMoovSize;     }

    int testMod(HttpReq *pReq);
    int testUnMod(HttpReq *pReq);
    int testIfRange(const char *pIR, int len);
    int release();
    time_t getLastMod() const       {   return m_fileData.getLastMod();   }
    ino_t getINode() const          {   return m_fileData.getINode();     }
    
    bool isDirty(const struct stat &fileStat) const
    {   return m_fileData.isDirty(fileStat);      }
    int needUpdateHeaders(const MimeSetting *pMIME,
                          const AutoStr2 *pCharset, short etag) const
    {
        return (pMIME != m_pMimeType) || (pCharset != m_pCharset)
               || (m_iFileETag != etag);
    }
    int compressFile(char useBrotli);

    int buildHeaders(const MimeSetting *pMIME,
                     const AutoStr2 *pCharset, short etag);
    int isSamePath(const char *arg1, int arg2)
    {  return strcmp(m_real.c_str(), arg1) == 0;   }

    LsiModuleData *getModuleData()      {   return &m_moduleData;    }


    static void setUpdateStaticGzipFile(int enable, int level,
                                        size_t min, size_t max);
    static void setCompressCachePath(const char *pPath);
    static const char *getCompressCachePath();

    static void setStaticBrOptions(int level);
};

#endif
