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
#ifndef LOOPBUF_H
#define LOOPBUF_H

#include <lsr/ls_loopbuf.h>

#include <string.h>
#include <stdlib.h>

#define LOOPBUFUNIT 64

class IOVec;

class LoopBuf : private ls_loopbuf_t
{
private:
    LoopBuf(const LoopBuf &rhs);
    void operator=(const LoopBuf &rhs);
public:
    explicit LoopBuf(int size = LOOPBUFUNIT)
    {   ls_loopbuf(this, size);  }

    //NOTICE: Any buf allocated by xpool must be destroyed by xDestroy.
    explicit LoopBuf(ls_xpool_t *pool, int size = LOOPBUFUNIT)
    {   ls_loopbuf_x(this, size, pool);  }

    ~LoopBuf()
    {   ls_loopbuf_d(this);  }

    // return the size of free memory block, could be smaller than available()
    //   as it will start use the free space at the beginning once
    //   reach the end.
    char   *begin() const                               {   return phead; }
    char   *end()   const                               {   return pend;  }
    int     capacity() const                            {   return sizemax; }
    bool    empty() const                               {   return (phead == pend);   }
    bool    full() const                                {   return  size() == sizemax - 1;  }

    void    clear()                                     {   phead = pend = pbuf;  }
    void    swap(LoopBuf &rhs)                        {   ls_loopbuf_swap(this, &rhs); }
    int     contiguous()                                {   return ls_loopbuf_contiguous(this);  }
    void    used(int size)                            {   return ls_loopbuf_used(this, size);  }

    int     reserve(int size)                         {   return ls_loopbuf_reserve(this, size);   }
    int     xReserve(int size, ls_xpool_t *pool)     {   return ls_loopbuf_xreserve(this, size, pool);}
    int     guarantee(int size)                       {   return ls_loopbuf_guarantee(this, size); }
    int     xGuarantee(int size, ls_xpool_t *pool)   {   return ls_loopbuf_xguarantee(this, size, pool);  }
    void    straight()                                  {   ls_loopbuf_straight(this);   }
    void    xStraight(ls_xpool_t *pool)              {   ls_loopbuf_xstraight(this, pool);    }
    int     moveTo(char *pBuf, int size)              {   return ls_loopbuf_moveto(this, pBuf, size); }
    int     pop_front(int size)                       {   return ls_loopbuf_popfront(this, size); }
    int     pop_back(int size)                        {   return ls_loopbuf_popback(this, size);  }
    int     append(const char *pBuf, int size)        {   return ls_loopbuf_append(this, pBuf, size);  }

    int xAppend(const char *pBuf, int size, ls_xpool_t *pool)
    {
        return ls_loopbuf_xappend(this, pBuf, size, pool);
    }

    // NOTICE: no boundary check for maximum performance, should make sure
    //         buffer has available space before calling this function.
    void append(char ch)
    {
        *pend++ = ch;
        if (pend == pbufend)
            pend = pbuf;
    }

    int size() const
    {
        int ret = pend - phead;
        if (ret >= 0)
            return ret;
        return ret + sizemax;
    }

    int available() const
    {
        int ret = phead - pend - 1;
        if (ret >= 0)
            return ret;
        return ret + sizemax;
    }

    // return the size of memory block, could be smaller than size()
    //   as it will start use the free space at the beginning once
    //   reach the end.
    int blockSize() const
    {
        return (phead > pend) ? pbufend - phead
               : pend - phead;
    }

    char *getPointer(int size) const
    {
        return pbuf + (phead - pbuf + size) % sizemax;
    }

    int getOffset(const char *p) const
    {
        return ((p < pbuf || p >= pbufend) ? -1 :
                (p - phead + sizemax) % sizemax);
    }

    char *inc(char *&pPos) const
    {
        if (++pPos == pbufend)
            pPos = pbuf;
        return pPos;
    }

    void update(int offset, const char *pBuf, int size)
    {
        ls_loopbuf_update(this, offset, pBuf, size);
    }

    char *search(int offset, const char *accept, int acceptLen)
    {
        return ls_loopbuf_search(this, offset, accept, acceptLen);
    }

    void getIOvec(IOVec &vect) const  {   iovAppend(vect);    }

    void iovInsert(IOVec &vect) const;
    void iovAppend(IOVec &vect) const;


    static void xDestroy(LoopBuf *p, ls_xpool_t *pool)
    {
        ls_loopbuf_xd(p, pool);
    }
};

class XLoopBuf : private ls_xloopbuf_t
{
private:
    XLoopBuf(const XLoopBuf &rhs);
    void operator=(const XLoopBuf &rhs);
public:
    explicit XLoopBuf(ls_xpool_t *pPool, int size = LOOPBUFUNIT)
    {   ls_xloopbuf(this, size, pPool);  }

    ~XLoopBuf()
    {   ls_xloopbuf_d(this);  }

    // return the size of free memory block, could be smaller than available()
    //   as it will start use the free space at the beginning once
    //   reach the end.

    char   *begin() const                           {   return loopbuf.phead;   }
    char   *end()   const                           {   return loopbuf.pend;    }
    int     capacity() const                        {   return loopbuf.sizemax;   }
    bool    empty() const                           {   return (loopbuf.phead == loopbuf.pend); }
    bool    full() const                            {   return size() == loopbuf.sizemax - 1; }

    void    clear()                                 {   ls_xloopbuf_clear(this);    }
    void    swap(XLoopBuf &rhs)                   {   ls_xloopbuf_swap(this, &rhs); }
    int     contiguous()                            {   return ls_xloopbuf_contiguous(this);  }
    void    used(int size)                        {   return ls_xloopbuf_used(this, size);  }

    int     reserve(int size)                     {    return ls_xloopbuf_reserve(this, size);    }
    int     guarantee(int size)                   {   return ls_xloopbuf_guarantee(this, size); }
    void    straight()                              {   ls_xloopbuf_straight(this);   }
    int     moveTo(char *pBuf, int size)          {   return ls_xloopbuf_moveto(this, pBuf, size); }
    int     pop_front(int size)                   {   return ls_xloopbuf_popfront(this, size); }
    int     pop_back(int size)                    {   return ls_xloopbuf_popback(this, size);  }
    int     append(const char *pBuf, int size)    {   return ls_xloopbuf_append(this, pBuf, size);    }

    // NOTICE: no boundary check for maximum performance, should make sure
    //         buffer has available space before calling this function.
    void    append(char ch)                       {   ls_xloopbuf_unsafeapp(this, ch); }

    int size() const
    {
        int ret = loopbuf.pend - loopbuf.phead;
        if (ret >= 0)
            return ret;
        return ret + loopbuf.sizemax;
    }

    int available() const
    {
        int ret = loopbuf.phead - loopbuf.pend - 1;
        if (ret >= 0)
            return ret;
        return ret + loopbuf.sizemax;
    }

    // return the size of memory block, could be smaller than size()
    //   as it will start use the free space at the beginning once
    //   reach the end.
    int blockSize() const
    {
        return (loopbuf.phead > loopbuf.pend) ? loopbuf.pbufend - loopbuf.phead
               : loopbuf.pend - loopbuf.phead;
    }

    char *getPointer(int size) const
    {
        return loopbuf.pbuf + (loopbuf.phead - loopbuf.pbuf + size) %
               loopbuf.sizemax;
    }

    int getOffset(const char *p) const
    {
        return ((p < loopbuf.pbuf || p >= loopbuf.pbufend) ? -1 :
                (p - loopbuf.phead + loopbuf.sizemax) % loopbuf.sizemax);
    }

    char *inc(char *&pPos) const
    {
        if (++pPos == loopbuf.pbufend)
            pPos = loopbuf.pbuf;
        return pPos;
    }

    void update(int offset, const char *pBuf, int size)
    {
        ls_xloopbuf_update(this, offset, pBuf, size);
    }

    char *search(int offset, const char *accept, int acceptLen)
    {
        return ls_xloopbuf_search(this, offset, accept, acceptLen);
    }

    void getIOvec(IOVec &vect) const      {   iovAppend(vect);    }

    void iovInsert(IOVec &vect) const;
    void iovAppend(IOVec &vect) const;
};
#endif


