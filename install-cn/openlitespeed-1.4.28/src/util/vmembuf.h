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
#ifndef VMEMBUF_H
#define VMEMBUF_H



#include <util/autostr.h>
#include <util/gpointerlist.h>

#include <stddef.h>

#define VMBUF_MALLOC    0
#define VMBUF_ANON_MAP  1
#define VMBUF_FILE_MAP  2

class BlockBuf;
typedef TPointerList<BlockBuf> BufList;

class VMemBuf
{
protected:
    static size_t   s_iBlockSize;
    static size_t   s_iMinMmapSize;
    static int      s_iKeepOpened;
    static int      s_iFdSpare;
    static char     s_aTmpFileTemplate[256];
    static int      s_iMaxAnonMapBlocks;
    static int      s_iCurAnonMapBlocks;

private:
    BufList         m_bufList;
    AutoStr2        m_fileName;
    int             m_iFd;
    off_t           m_iCurTotalSize;

    short           m_iType;
    unsigned char   m_iAutoGrow;
    unsigned char   m_iNoRecycle;
    off_t           m_curWBlkPos;
    BlockBuf      **m_pCurWBlock;
    char           *m_pCurWPos;

    off_t           m_curRBlkPos;
    BlockBuf      **m_pCurRBlock;
    char           *m_pCurRPos;


    VMemBuf(const VMemBuf &rhs);
    void operator=(const VMemBuf &rhs);

    int mapNextWBlock();
    int mapNextRBlock();
    int appendBlock(BlockBuf *pBlock);
    int grow();
    void releaseBlocks();
    void reset();
    BlockBuf *getAnonMapBlock(size_t size);
    void recycle(BlockBuf *pBuf);

    int  remapBlock(BlockBuf *pBlock, off_t pos);

public:
    void deallocate();

    static int getBlockSize()    {   return s_iBlockSize;    }
    static int lowOnAnonMem()
    {   return s_iMaxAnonMapBlocks - s_iCurAnonMapBlocks < s_iMaxAnonMapBlocks / 4; }
    static int  getMinMmapSize()  {   return s_iMinMmapSize;  }
    static void setMaxAnonMapSize(int sz);
    static void setTempFileTemplate(const char *pTemp);
    static char *mapTmpBlock(int fd, BlockBuf &buf, off_t  offset,
                             int write = 0);
    static void releaseBlock(BlockBuf *pBlock);

    explicit VMemBuf(int TargetSize = 0);
    ~VMemBuf();
    int set(int type, int size);
    int set(BlockBuf *pBlock);
    int set(const char *pFileName, int size);
    int setFd(const char *pFileName, int fd);
    char *getReadBuffer(size_t  &size);
    char *getWriteBuffer(size_t  &size);

    void readUsed(off_t  len)     {   m_pCurRPos += len;      }
    void writeUsed(off_t  len)    {   m_pCurWPos += len;      }
    char *getCurRPos() const       {   return m_pCurRPos;      }
    off_t  getCurROffset() const;
    char *getCurWPos() const       {   return m_pCurWPos;      }
    off_t  getCurWOffset() const;
    int write(const char *pBuf, int size);
    bool isMmaped() const {   return m_iType >= VMBUF_ANON_MAP;  }
    //int  seekRPos( size_t pos );
    //int  seekWPos( size_t pos );
    void rewindWriteBuf();
    void rewindReadBuf();
    void rewindWOff(off_t rewind);
    int setROffset(off_t  offset);
    int getFd() const               {   return m_iFd;            }
    off_t  getCurFileSize() const   {   return m_iCurTotalSize;  }
    off_t  getCurRBlkPos() const    {   return m_curRBlkPos;    }
    off_t  getCurWBlkPos() const    {   return m_curWBlkPos;    }
    int empty() const
    {
        if (m_curRBlkPos < m_curWBlkPos)
            return 0;
        if (!m_pCurWBlock)
            return 1;
        return (m_pCurRPos >= m_pCurWPos);
    }
    off_t writeBufSize() const;
    int  reinit(off_t TargetSize = -1);
    int  exactSize(off_t  *pSize = NULL);
    int  shrinkBuf(off_t size);
    int  close();
    int  copyToFile(off_t  startOff, off_t  len,
                    int fd, off_t  destStartOff);
    const char *getTempFileName()  {    return m_fileName.c_str();    }

    int convertInMemoryToFileBacked();

    int convertFileBackedToInMemory();
    static void initAnonPool();
    int eof(off_t offset);
    const char *acquireBlockBuf(off_t offset, int *size);
    void releaseBlockBuf(off_t offset);


};

class MMapVMemBuf : public VMemBuf
{
public:
    explicit MMapVMemBuf(int TargetSize = 0);
};


#endif
