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
#ifndef BLOCKBUF_H
#define BLOCKBUF_H


#include <stddef.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/mman.h>

#include <lsdef.h>
//#include <util/linkedobj.h>

#ifndef MAP_FILE
#define MAP_FILE 0
#endif //MAP_FILE

class BlockBuf //: public LinkedObj
{
    char   *m_pBuf;
    char   *m_pBufEnd;
public:
    BlockBuf()
        : m_pBuf(NULL)
        , m_pBufEnd(NULL)
    {}

    BlockBuf(char *pBuf, size_t size)
        : m_pBuf(pBuf)
        , m_pBufEnd(pBuf + size)
    {}
    virtual ~BlockBuf() {}
    virtual void deallocate()
    {}
    void setBlockBuf(char *pBuf, size_t size)
    {   m_pBuf = pBuf; m_pBufEnd = pBuf + size;       }

    char *getBuf() const           {   return m_pBuf;              }
    char *getBufEnd() const        {   return m_pBufEnd;           }
    size_t  getBlockSize() const    {   return m_pBufEnd - m_pBuf;  }



    LS_NO_COPY_ASSIGN(BlockBuf);
};

class MallocBlockBuf : public BlockBuf
{
public:
    MallocBlockBuf() {}
    MallocBlockBuf(char *pBuf, size_t size)
        : BlockBuf(pBuf, size)
    {}
    ~MallocBlockBuf()   {   if (getBuf()) free(getBuf());    }
    void deallocate()
    {   free(getBuf());     }
};

class MmapBlockBuf : public BlockBuf
{
public:
    MmapBlockBuf() {}
    MmapBlockBuf(char *pBuf, size_t size)
        : BlockBuf(pBuf, size)
    {}
    ~MmapBlockBuf()     {   if (getBuf()) munmap(getBuf(), getBlockSize()); }
    void deallocate()
    {
        munmap(getBuf(), getBlockSize());
        setBlockBuf(NULL, getBlockSize());
    }
};


#endif
