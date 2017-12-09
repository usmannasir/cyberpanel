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
#include <util/vmembuf.h>
#include <util/blockbuf.h>

#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <lsr/ls_strtool.h>

#define _RELEASE_MMAP

size_t  VMemBuf::s_iBlockSize = 8192;
size_t  VMemBuf::s_iMinMmapSize = 8192;

int  VMemBuf::s_iMaxAnonMapBlocks = 1024 * 1024 * 10 / 8192;
int  VMemBuf::s_iCurAnonMapBlocks = 0;
int  VMemBuf::s_iKeepOpened = 0;
int  VMemBuf::s_iFdSpare = -1; //open( "/dev/null", O_RDWR );
char VMemBuf::s_aTmpFileTemplate[256] = "/tmp/tmp-XXXXXX";
BufList *s_pAnonPool = NULL;

void VMemBuf::initAnonPool()
{
    s_pAnonPool = new BufList();
}


void VMemBuf::setMaxAnonMapSize(int sz)
{
    if (sz >= 0)
        s_iMaxAnonMapBlocks = sz / s_iBlockSize;
}


void VMemBuf::setTempFileTemplate(const char *pTemp)
{
    if (pTemp != NULL)
    {
        strcpy(s_aTmpFileTemplate, pTemp);
        int len = strlen(pTemp);
        if ((len < 6) ||
            (strcmp(pTemp + len - 6, "XXXXXX") != 0))
            strcat(s_aTmpFileTemplate, "XXXXXX");
    }
}


VMemBuf::VMemBuf(int target_size)
    : m_bufList(4)
{
    reset();
}


VMemBuf::~VMemBuf()
{
    deallocate();
}


void VMemBuf::releaseBlocks()
{
    if (m_iType == VMBUF_ANON_MAP)
    {
        s_iCurAnonMapBlocks -= m_iCurTotalSize / s_iBlockSize;
        if (m_iNoRecycle)
            m_bufList.release_objects();
        else
        {
            s_pAnonPool->push_back(m_bufList);
            m_bufList.clear();
        }
    }
    else
        m_bufList.release_objects();
    memset(&m_curWBlkPos, 0,
           (char *)(&m_pCurRPos + 1) - (char *)&m_curWBlkPos);
    m_iCurTotalSize = 0;
}


void VMemBuf::deallocate()
{
    if (VMBUF_FILE_MAP == m_iType)
    {
        if (m_iFd != -1)
        {
            ::close(m_iFd);
            m_iFd = -1;
        }
        unlink(m_fileName.c_str());
    }
    releaseBlocks();
}


void VMemBuf::recycle(BlockBuf *pBuf)
{
    if (m_iType == VMBUF_ANON_MAP)
    {
        if (pBuf->getBlockSize() == s_iBlockSize)
        {
            if (m_iNoRecycle)
                delete pBuf;
            else
                s_pAnonPool->push_back(pBuf);
            --s_iCurAnonMapBlocks;
            return;
        }
        s_iCurAnonMapBlocks -= pBuf->getBlockSize() / s_iBlockSize;
    }
    delete pBuf;
}


void VMemBuf::rewindWOff(off_t rewind)
{
    while(rewind > 0)
    {
        if (m_pCurWPos - (*m_pCurWBlock)->getBuf() < (int)rewind)
        {
            rewind -= m_pCurWPos - (*m_pCurWBlock)->getBuf();
            m_pCurWPos = (*m_pCurWBlock)->getBuf();
            
            if ( m_pCurWBlock > m_bufList.begin())
            {
                m_curWBlkPos -= (*m_pCurWBlock)->getBlockSize();
                m_pCurWBlock--;
                if (!(*m_pCurWBlock)->getBuf())
                {
                    if ( remapBlock(*m_pCurWBlock, m_curWBlkPos - s_iBlockSize) == 0)
                        m_pCurWPos = (*m_pCurWBlock)->getBufEnd();
                    else
                    {
                        //cannot map previous block, out of memory?
                        assert("failed to map previous block" == NULL);
                    }
                }
                else
                    m_pCurWPos = (*m_pCurWBlock)->getBufEnd();
            }
            else
                return;
            
        }
        else
        {
            m_pCurWPos -= rewind;
            return;
        }
    }
}


int VMemBuf::shrinkBuf(off_t size)
{
    /*
        if ( m_type == VMBUF_FILE_MAP )
        {
            if ( s_iMaxAnonMapBlocks - s_iCurAnonMapBlocks > s_iMaxAnonMapBlocks / 10 )
            {
                deallocate();
                if ( set( VMBUF_ANON_MAP , getBlockSize() ) == -1 )
                    return LS_FAIL;
                return 0;
            }

        }
    */
    if (size < 0)
        size = 0;
    if ((m_iType == VMBUF_FILE_MAP) && (m_iFd != -1))
    {
        if (m_iCurTotalSize > size)
            ftruncate(m_iFd, size);
    }
    BlockBuf *pBuf;
    while (m_iCurTotalSize > size)
    {
        pBuf = m_bufList.pop_back();
        m_iCurTotalSize -= pBuf->getBlockSize();
        recycle(pBuf);
    }
    if (!m_bufList.empty())
        m_pCurWBlock = m_pCurRBlock = m_bufList.begin();
    return 0;
}


void VMemBuf::releaseBlock(BlockBuf *pBlock)
{
    if (pBlock->getBuf())
    {
        munmap(pBlock->getBuf(), pBlock->getBlockSize());
        pBlock->setBlockBuf(NULL, pBlock->getBlockSize());
    }

}


int VMemBuf::remapBlock(BlockBuf *pBlock, off_t pos)
{
    char *pBuf = (char *) mmap(NULL, s_iBlockSize, PROT_READ | PROT_WRITE,
                               MAP_SHARED | MAP_FILE, m_iFd, pos);
    if (pBuf == MAP_FAILED)
    {
        perror("mmap() failed in remapBlock");
        return LS_FAIL;
    }
    pBlock->setBlockBuf(pBuf, s_iBlockSize);
    return 0;
}


int VMemBuf::reinit(off_t TargetSize)
{
    if (m_iType == VMBUF_ANON_MAP)
    {
        if ((TargetSize >=
             (off_t)((s_iMaxAnonMapBlocks - s_iCurAnonMapBlocks) * s_iBlockSize)) ||
            (TargetSize > 1024 * 1024))
        {
            releaseBlocks();
            if (set(VMBUF_FILE_MAP , getBlockSize()) == -1)
                return LS_FAIL;
        }
    }
    else if (m_iType == VMBUF_FILE_MAP)
    {
        if ((TargetSize < 1024 * 1024) &&
            (s_iMaxAnonMapBlocks - s_iCurAnonMapBlocks > s_iMaxAnonMapBlocks / 5) &&
            (TargetSize < (off_t)((s_iMaxAnonMapBlocks - s_iCurAnonMapBlocks) *
                                  s_iBlockSize)))
        {
            deallocate();
            if (set(VMBUF_ANON_MAP , getBlockSize()) == -1)
                return LS_FAIL;
        }

#ifdef _RELEASE_MMAP
        if (!m_bufList.empty())
        {
            if (!(*m_bufList.begin())->getBuf())
            {
                if (remapBlock(*m_bufList.begin(), 0) == -1)
                    return LS_FAIL;
            }
            if ((m_pCurWBlock) &&
                (m_pCurWBlock != m_bufList.begin()) &&
                (m_pCurWBlock != m_pCurRBlock))
                releaseBlock(*m_pCurWBlock);
            if ((m_pCurRBlock) && (m_pCurRBlock != m_bufList.begin()))
                releaseBlock(*m_pCurRBlock);
        }
#endif

    }

    if (!m_bufList.empty())
    {

        m_pCurWBlock = m_pCurRBlock = m_bufList.begin();
        if (*m_pCurWBlock)
        {
            m_curWBlkPos = m_curRBlkPos = (*m_pCurWBlock)->getBlockSize();
            m_pCurRPos = m_pCurWPos = (*m_pCurWBlock)->getBuf();
        }
        else
        {
            m_curWBlkPos = m_curRBlkPos = 0;
            m_pCurRPos = m_pCurWPos = NULL;
        }
    }
    return 0;
}


void VMemBuf::reset()
{
    m_iFd = -1;
    memset(&m_iCurTotalSize, 0,
           (char *)(&m_pCurRPos + 1) - (char *)&m_iCurTotalSize);
    if (m_fileName.buf())
    {
        *m_fileName.buf() = 0;
        m_fileName.setLen(0);
    }
}


BlockBuf *VMemBuf::getAnonMapBlock(size_t size)
{
    BlockBuf *pBlock;
    if (size == s_iBlockSize)
    {
        if (!s_pAnonPool->empty())
        {
            pBlock = s_pAnonPool->pop_back();
            ++s_iCurAnonMapBlocks;
            return pBlock;
        }
    }
    int blocks = (size + s_iBlockSize - 1) / s_iBlockSize;
    size = blocks * s_iBlockSize;
    char *pBuf = (char *) mmap(NULL, size, PROT_READ | PROT_WRITE,
                               MAP_ANON | MAP_SHARED, -1, 0);
    if (pBuf == MAP_FAILED)
    {
        perror("Anonymous mmap() failed");
        return NULL;
    }
    pBlock = new MmapBlockBuf(pBuf, size);
    if (!pBlock)
    {
        perror("new MmapBlockBuf failed in getAnonMapBlock()");
        munmap(pBuf, size);
        return NULL;
    }
    s_iCurAnonMapBlocks += blocks;
    return pBlock;
}


int VMemBuf::set(int type, int size)
{
    if ((type > VMBUF_FILE_MAP) || (type < VMBUF_MALLOC))
        return LS_FAIL;

    char *pBuf;
    BlockBuf *pBlock = NULL;
    m_iType = type;
    switch (type)
    {
    case VMBUF_MALLOC:
        if (size > 0)
        {
            size = ((size + 511) / 512) * 512;
            pBuf = (char *)malloc(size);
            if (!pBuf)
                return LS_FAIL;
            pBlock = new MallocBlockBuf(pBuf, size);
            if (!pBlock)
            {
                free(pBuf);
                return LS_FAIL;
            }
        }
        break;
    case VMBUF_ANON_MAP:
        m_iAutoGrow = 1;
        if (size > 0)
        {
            if ((pBlock = getAnonMapBlock(size)) == NULL)
                return LS_FAIL;
        }
        break;
    case VMBUF_FILE_MAP:
        m_iAutoGrow = 1;
        m_fileName.setStr(s_aTmpFileTemplate);
        m_iFd = mkstemp(m_fileName.buf());
        if (m_iFd == -1)
        {
            char achBuf[1024];
            ls_snprintf(achBuf, 1024,
                        "Failed to create swap file with mkstemp( %s ), please check 'Swap Directory' and permission",
                        m_fileName.c_str());
            perror(achBuf);
            *m_fileName.buf() = 0;
            m_fileName.setLen(0);
            return LS_FAIL;
        }
        fcntl(m_iFd, F_SETFD, FD_CLOEXEC);
        break;
    }
    if (pBlock)
    {
        appendBlock(pBlock);
        m_pCurRPos = m_pCurWPos = pBlock->getBuf();
        m_iCurTotalSize = m_curRBlkPos = m_curWBlkPos = pBlock->getBlockSize();
        m_pCurRBlock = m_pCurWBlock = m_bufList.begin();
    }
    return 0;
}


int VMemBuf::appendBlock(BlockBuf *pBlock)
{
    if (m_bufList.full())
    {
        BlockBuf **pOld = m_bufList.begin();
        m_bufList.push_back(pBlock);
        if (m_pCurWBlock)
            m_pCurWBlock = m_pCurWBlock - pOld + m_bufList.begin();
        if (m_pCurRBlock)
            m_pCurRBlock = m_pCurRBlock - pOld + m_bufList.begin();
        return 0;
    }
    else
    {
        m_bufList.unsafe_push_back(pBlock);
        return 0;
    }

}


int VMemBuf::convertFileBackedToInMemory()
{
    BlockBuf *pBlock;
    if (m_iType != VMBUF_FILE_MAP)
        return LS_FAIL;
    if (m_pCurWPos == (*m_pCurWBlock)->getBuf())
    {
        if (*m_pCurWBlock == m_bufList.back())
        {
            m_bufList.pop_back();
            recycle(*m_pCurWBlock);
            if (!m_bufList.empty())
            {
                m_iNoRecycle = 1;
                s_iCurAnonMapBlocks += m_bufList.size();
                int i = 0;
                while (i < m_bufList.size())
                {
                    pBlock = m_bufList[i];
                    if (!pBlock->getBuf())
                    {
                        if (remapBlock(pBlock, i * s_iBlockSize) == -1)
                            return LS_FAIL;
                    }
                    ++i;
                }
            }
            unlink(m_fileName.c_str());
            ::close(m_iFd);
            m_iFd = -1;
            m_iType = VMBUF_ANON_MAP;
            if (!(pBlock = getAnonMapBlock(s_iBlockSize)))
                return LS_FAIL;
            appendBlock(pBlock);
            if (m_pCurRPos == m_pCurWPos)
                m_pCurRPos = (*m_pCurWBlock)->getBuf();
            m_pCurWPos = (*m_pCurWBlock)->getBuf();
            return 0;
        }

    }
    return LS_FAIL;
}


int VMemBuf::set(BlockBuf *pBlock)
{
    assert(pBlock);
    m_iType = VMBUF_MALLOC;
    appendBlock(pBlock);
    m_pCurRBlock = m_pCurWBlock = m_bufList.begin();
    m_pCurRPos = m_pCurWPos = pBlock->getBuf();
    m_iCurTotalSize = m_curRBlkPos = m_curWBlkPos = pBlock->getBlockSize();
    return 0;
}


int VMemBuf::set(const char *pFileName, int size)
{
    if (size < 0)
        size = s_iMinMmapSize;
    m_iType = VMBUF_FILE_MAP;
    m_iAutoGrow = 1;
    if (pFileName)
    {
        m_fileName = pFileName;
        m_iFd = ::open(pFileName, O_RDWR | O_CREAT | O_TRUNC, 0600);
        if (m_iFd < 0)
        {
            perror("Failed to open temp file for swapping");
            return LS_FAIL;
        }

        fcntl(m_iFd, F_SETFD, FD_CLOEXEC);

    }
    return 0;
}


int VMemBuf::setFd(const char *pFileName, int fd)
{
    if (pFileName)
        m_fileName = pFileName;
    m_iFd = fd;
    fcntl(m_iFd, F_SETFD, FD_CLOEXEC);
    m_iType = VMBUF_FILE_MAP;
    m_iAutoGrow = 1;
    return 0;
}


void VMemBuf::rewindWriteBuf()
{
    if (m_pCurRBlock)
    {
        if (m_pCurWBlock != m_pCurRBlock)
        {
            m_pCurWBlock = m_pCurRBlock;
            m_curWBlkPos = m_curRBlkPos;
        }
        m_pCurWPos = m_pCurRPos;
    }
    else
    {
        m_pCurRBlock = m_pCurWBlock;
        m_curRBlkPos = m_curWBlkPos;
        m_pCurRPos = m_pCurWPos;
    }

}


void VMemBuf::rewindReadBuf()
{
#ifdef _RELEASE_MMAP
    if (m_iType == VMBUF_FILE_MAP)
    {
        if (!(*m_bufList.begin())->getBuf())
        {
            if (remapBlock(*m_bufList.begin(), 0) == -1)
                return;
        }
        if ((m_pCurRBlock) &&
            (m_pCurRBlock != m_bufList.begin()) &&
            (m_pCurRBlock != m_pCurWBlock))
            releaseBlock(*m_pCurRBlock);
    }
#endif
    m_pCurRBlock = m_bufList.begin();
    m_curRBlkPos = (*m_pCurRBlock)->getBlockSize();
    m_pCurRPos = (*m_pCurRBlock)->getBuf();
}


int VMemBuf::setROffset(off_t offset)
{
    if (offset > m_iCurTotalSize)
        return LS_FAIL;
    rewindReadBuf();
    while (offset >= (off_t)(*m_pCurRBlock)->getBlockSize())
    {
        offset -= (*m_pCurRBlock)->getBlockSize();
        mapNextRBlock();
    }
    m_pCurRPos += offset;
    return 0;
}


int VMemBuf::mapNextWBlock()
{
    if (!m_pCurWBlock || m_pCurWBlock + 1 >= m_bufList.end())
    {
        if (!m_iAutoGrow || grow())
            return LS_FAIL;
    }

    if (m_pCurWBlock)
    {
#ifdef _RELEASE_MMAP
        if (m_iType == VMBUF_FILE_MAP)
        {
            if (!(*(m_pCurWBlock + 1))->getBuf())
            {
                if (remapBlock(*(m_pCurWBlock + 1), m_curWBlkPos) == -1)
                    return LS_FAIL;
            }
            if (m_pCurWBlock != m_pCurRBlock)
                releaseBlock(*m_pCurWBlock);
        }
#endif
        ++m_pCurWBlock;
    }
    else
    {
#ifdef _RELEASE_MMAP
        if ((m_iType == VMBUF_FILE_MAP) && (!(*m_bufList.begin())->getBuf()))
        {
            if (remapBlock(*m_bufList.begin(), 0) == -1)
                return LS_FAIL;
        }
#endif
        m_pCurWBlock = m_pCurRBlock = m_bufList.begin();
        m_curWBlkPos = 0;
        m_curRBlkPos = (*m_pCurWBlock)->getBlockSize();
        m_pCurRPos = (*m_pCurWBlock)->getBuf();
    }
    m_curWBlkPos += (*m_pCurWBlock)->getBlockSize();
    m_pCurWPos = (*m_pCurWBlock)->getBuf();
    return 0;
}


int VMemBuf::grow()
{
    char *pBuf;
    BlockBuf *pBlock;
    off_t oldPos = m_iCurTotalSize;
    switch (m_iType)
    {
    case VMBUF_MALLOC:
        pBuf = (char *)malloc(s_iBlockSize);
        if (!pBuf)
            return LS_FAIL;
        pBlock = new MallocBlockBuf(pBuf, s_iBlockSize);
        if (!pBlock)
        {
            perror("new MallocBlockBuf failed in grow()");
            free(pBuf);
            return LS_FAIL;
        }
        break;
    case VMBUF_FILE_MAP:
        if (ftruncate(m_iFd, m_iCurTotalSize + s_iBlockSize) == -1)
        {
            perror("Failed to increase temp file size with ftrancate()");
            return LS_FAIL;
        }
        pBuf = (char *) mmap(NULL, s_iBlockSize, PROT_READ | PROT_WRITE,
                             MAP_SHARED | MAP_FILE, m_iFd, oldPos);
        if (pBuf == MAP_FAILED)
        {
            perror("FS backed mmap() failed");
            return LS_FAIL;
        }
        pBlock = new MmapBlockBuf(pBuf, s_iBlockSize);
        if (!pBlock)
        {
            perror("new MmapBlockBuf failed in grow()");
            munmap(pBuf, s_iBlockSize);
            return LS_FAIL;
        }
        break;
    case VMBUF_ANON_MAP:
        if ((pBlock = getAnonMapBlock(s_iBlockSize)))
            break;
    default:
        return LS_FAIL;
    }
    appendBlock(pBlock);
    m_iCurTotalSize += s_iBlockSize;
    return 0;

}


char *VMemBuf::getReadBuffer(size_t &size)
{
    if ((!m_pCurRBlock) || (m_pCurRPos >= (*m_pCurRBlock)->getBufEnd()))
    {
        size = 0;
        if (mapNextRBlock() != 0)
            return NULL;
    }
    if (m_curRBlkPos == m_curWBlkPos)
        size = m_pCurWPos - m_pCurRPos;
    else
        size = (*m_pCurRBlock)->getBufEnd() - m_pCurRPos;
    return m_pCurRPos;
}


char *VMemBuf::getWriteBuffer(size_t &size)
{
    if ((!m_pCurWBlock) || (m_pCurWPos >= (*m_pCurWBlock)->getBufEnd()))
    {
        if (mapNextWBlock() != 0)
            return NULL;
    }
    size = (*m_pCurWBlock)->getBufEnd() - m_pCurWPos;
    return m_pCurWPos;
}


off_t VMemBuf::getCurROffset() const
{
    return (m_pCurRBlock)
           ? (m_curRBlkPos - ((*m_pCurRBlock)->getBufEnd() - m_pCurRPos))
           : 0;
}


off_t VMemBuf::getCurWOffset() const
{
    return m_pCurWBlock
           ? (m_curWBlkPos - ((*m_pCurWBlock)->getBufEnd() - m_pCurWPos))
           : 0;
}


int VMemBuf::mapNextRBlock()
{
    if (m_curRBlkPos >= m_curWBlkPos)
        return LS_FAIL;
    if (m_pCurRBlock)
    {
#ifdef _RELEASE_MMAP
        if (m_iType == VMBUF_FILE_MAP)
        {
            if (!(*(m_pCurRBlock + 1))->getBuf())
            {
                if (remapBlock(*(m_pCurRBlock + 1), m_curRBlkPos) == -1)
                    return LS_FAIL;
            }
            if (m_pCurWBlock != m_pCurRBlock)
                releaseBlock(*m_pCurRBlock);
        }
#endif
        ++m_pCurRBlock;
    }
    else
        m_pCurRBlock = m_bufList.begin();
    m_curRBlkPos += (*m_pCurRBlock)->getBlockSize();
    m_pCurRPos = (*m_pCurRBlock)->getBuf();
    return 0;

}


off_t  VMemBuf::writeBufSize() const
{
    if (m_pCurWBlock == m_pCurRBlock)
        return m_pCurWPos - m_pCurRPos;
    off_t  diff = m_curWBlkPos - m_curRBlkPos;
    if (m_pCurWBlock)
        diff += m_pCurWPos - (*m_pCurWBlock)->getBuf();
    if (m_pCurRBlock)
        diff -= m_pCurRPos - (*m_pCurRBlock)->getBuf();
    return diff;
}


int VMemBuf::write(const char *pBuf, int size)
{
    const char *pCur = pBuf;
    if (m_pCurWPos)
    {
        int len = (*m_pCurWBlock)->getBufEnd() - m_pCurWPos;
        if (size <= len)
        {
            memmove(m_pCurWPos, pBuf, size);
            m_pCurWPos += size;
            return size;
        }
        else
        {
            memmove(m_pCurWPos, pBuf, len);
            pCur += len;
            size -= len;
        }
    }
    do
    {
        if (mapNextWBlock() != 0)
            return pCur - pBuf;
        int len  = (*m_pCurWBlock)->getBufEnd() - m_pCurWPos;
        if (size <= len)
        {
            memmove(m_pCurWPos, pCur, size);
            m_pCurWPos += size;
            return pCur - pBuf + size;
        }
        else
        {
            memmove(m_pCurWPos, pCur, len);
            pCur += len;
            size -= len;
        }
    }
    while (true);
}


int VMemBuf::exactSize(off_t  *pSize)
{
    off_t  size = m_iCurTotalSize;
    if (m_pCurWBlock)
        size -= (*m_pCurWBlock)->getBufEnd() - m_pCurWPos;
    if (pSize)
        *pSize = size;
    if (m_iFd != -1)
        return  ftruncate(m_iFd, size);
    return 0;
}


int VMemBuf::close()
{
    if (m_iFd != -1)
        ::close(m_iFd);
    releaseBlocks();
    reset();
    return 0;
}


MMapVMemBuf::MMapVMemBuf(int TargetSize)
{
    int type = VMBUF_ANON_MAP;

    if ((lowOnAnonMem()) || (TargetSize > 1024 * 1024) ||
        (TargetSize >=
         (long)((s_iMaxAnonMapBlocks - s_iCurAnonMapBlocks) * s_iBlockSize)))
        type = VMBUF_FILE_MAP;
    if (set(type , getBlockSize()) == -1)
        abort(); //throw -1;
}


// int VMemBuf::setFd( int fd )
// {
//     struct stat st;
//     if ( fstat( fd, &st ) == -1 )
//         return LS_FAIL;
//     m_fd = fd;
//     m_type = VMBUF_FILE_MAP;
//     m_curTotalSize = st.st_size;
//
//     return 0;
// }


char *VMemBuf::mapTmpBlock(int fd, BlockBuf &buf, off_t offset, int write)
{
    off_t blkBegin = offset - offset % s_iBlockSize;
    char *pBuf = (char *) mmap(NULL, s_iBlockSize, PROT_READ | write,
                               MAP_SHARED | MAP_FILE, fd, blkBegin);
    if (pBuf == MAP_FAILED)
    {
        perror("FS backed mmap() failed");
        return NULL;
    }
    buf.setBlockBuf(pBuf, s_iBlockSize);
    return pBuf + offset % s_iBlockSize;
}


int VMemBuf::eof(off_t offset)
{
    int total = getCurWOffset();
    if (offset >= total)
        return 1;
    else
        return 0;
}


const char *VMemBuf::acquireBlockBuf(off_t offset, int *size)
{
    BlockBuf *pSrcBlock = NULL;
    char *pSrcPos;
    int total = getCurWOffset();
    int blk = offset / s_iBlockSize;
    *size = 0;
    if (blk >= m_bufList.size())
        return NULL;
    if (offset >= total)
        return "";

    int len = total - offset;
    pSrcBlock = m_bufList[blk];
    if (!pSrcBlock)
        return NULL;

    if (!pSrcBlock->getBuf())
    {
        if (remapBlock(pSrcBlock, blk * s_iBlockSize) == -1)
            return NULL;
    }
    pSrcPos = pSrcBlock->getBuf() + offset % s_iBlockSize;
    if (len > pSrcBlock->getBufEnd() - pSrcPos)
        *size = pSrcBlock->getBufEnd() - pSrcPos;
    else
        *size = len;
    return pSrcPos;
}


void VMemBuf::releaseBlockBuf(off_t offset)
{
    BlockBuf *pSrcBlock = NULL;
    int blk = offset / s_iBlockSize;
    if ((m_iType != VMBUF_FILE_MAP) ||
        (blk >= m_bufList.size()))
        return;
    pSrcBlock = m_bufList[blk];
    if (pSrcBlock->getBuf() && (pSrcBlock != *m_pCurRBlock)
        && (pSrcBlock != *m_pCurWBlock))
        releaseBlock(pSrcBlock);
}


int VMemBuf::copyToFile(off_t  startOff, off_t  len,
                        int fd, off_t  destStartOff)
{
    BlockBuf *pSrcBlock = NULL;
    char *pSrcPos;
    int mapped = 0;
    int blk = startOff / s_iBlockSize;
    if (blk >= m_bufList.size())
        return LS_FAIL;
    struct stat st;
    if (fstat(fd, &st) == -1)
        return LS_FAIL;
    int destSize = destStartOff + len;
    //destSize -= destSize % s_iBlockSize;
    if (st.st_size < destSize)
    {
        if (ftruncate(fd, destSize) == -1)
            return LS_FAIL;
    }
    BlockBuf destBlock;
    char *pPos = mapTmpBlock(fd, destBlock, destStartOff, PROT_WRITE);
    int ret = 0;
    if (!pPos)
        return LS_FAIL;
    while (!ret && (len > 0))
    {
        if (blk >= m_bufList.size())
            break;
        pSrcBlock = m_bufList[blk];
        if (!pSrcBlock)
        {
            ret = -1;
            break;
        }
        if (!pSrcBlock->getBuf())
        {
            if (remapBlock(pSrcBlock, blk * s_iBlockSize) == -1)
                return LS_FAIL;
            mapped = 1;
        }
        pSrcPos = pSrcBlock->getBuf() + startOff % s_iBlockSize;

        while ((len > 0) && (pSrcPos < pSrcBlock->getBufEnd()))
        {
            if (pPos >= destBlock.getBufEnd())
            {
                msync(destBlock.getBuf(), destBlock.getBlockSize(), MS_SYNC);
                releaseBlock(&destBlock);
                pPos = mapTmpBlock(fd, destBlock, destStartOff, PROT_WRITE);
                if (!pPos)
                {
                    ret = -1;
                    break;
                }
            }
            int sz = len;
            if (sz > pSrcBlock->getBufEnd() - pSrcPos)
                sz = pSrcBlock->getBufEnd() - pSrcPos;
            if (sz > destBlock.getBufEnd() - pPos)
                sz = destBlock.getBufEnd() - pPos;
            memmove(pPos, pSrcPos, sz);
            pSrcPos += sz;
            pPos += sz;
            destStartOff += sz;
            len -= sz;
        }
        startOff = 0;
        if (mapped)
        {
            releaseBlock(pSrcBlock);
            mapped = 0;
        }
        ++blk;
    }
    releaseBlock(&destBlock);
    return ret;

}


