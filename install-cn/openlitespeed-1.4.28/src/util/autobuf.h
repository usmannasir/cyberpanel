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
#ifndef AUTOBUF_H
#define AUTOBUF_H


#include <lsr/ls_buf.h>

#include <string.h>

class AutoBuf : private ls_buf_t
{
private:
    AutoBuf(const AutoBuf &rhs);
    void operator=(const AutoBuf &rhs);
public:
    explicit AutoBuf(int size = 1024)
    {   ls_buf(this, size);  }
    //NOTICE: Any buf allocated by xpool must be destroyed by xDestroy.
    explicit AutoBuf(ls_xpool_t *pool, int size = 1024)
    {   ls_buf_x(this, size, pool);  }
    ~AutoBuf()
    {   ls_buf_d(this);  }

    int     available() const       {   return pbufend - pend;  }

    char   *begin() const           {   return pbuf;  }
    char   *end() const             {   return pend;  }

    void    used(int size)          {   pend += size;  }
    void    clear()                 {   pend = pbuf;  }

    int     capacity() const        {   return pbufend - pbuf;  }
    int     size() const            {   return pend - pbuf;  }

    int     reserve(int size)       {   return ls_buf_reserve(this, size);  }
    int     xReserve(int size, ls_xpool_t *pool)
    {   return ls_buf_xreserve(this, size, pool);  }

    void    resize(int size)        {   ls_buf_resize(this, size);  }
    int     grow(int size)          {   return ls_buf_grow(this, size);  }
    int     xGrow(int size, ls_xpool_t *pool)
    {   return ls_buf_xgrow(this, size, pool);  }

    bool    empty() const           {   return (pbuf == pend);  }
    bool    full() const            {   return (pend == pbufend);  }

    int     getOffset(const char *p) const        {   return p - pbuf;  }
    char   *getp(int offset) const                  {   return pbuf + offset;  }
    void    swap(AutoBuf &rhs)      {   ls_buf_swap(this, &rhs);  }

    int     pop_front_to(char *pBuf, int size)
    {   return ls_buf_popfrontto(this, pBuf, size);  }

    int     pop_front(int size)     {   return ls_buf_popfront(this, size);  }
    int     pop_end(int size)       {   return ls_buf_popend(this, size);  }
    void    pop_back()              {   ls_buf_popend(this, 1);          }

    int     append(const char *pBuf, int size)
    {   return ls_buf_append2(this, pBuf, size);  }

    int     append(const char *pBuf)
    {   return ls_buf_append(this, pBuf);  }

    void    appendUnsafe(char ch)  {   *pend++ = ch;  }

    int appendUnsafe(const char *pBuf, int size)
    {
        memmove(end(), pBuf, size);
        used(size);
        return size;
    }

    int appendAllocOnly(int size)
    {
        if (size == 0)
            return 0;
        if (size > available())
        {
            if (grow(size - available()) == -1)
                return -1;
        }
        used(size);
        return size;
    }

    int xAppend(const char *pBuf, int size, ls_xpool_t *pool)
    {   return ls_buf_xappend2(this, pBuf, size, pool);  }

    int xAppend(const char *pBuf, ls_xpool_t *pool)
    {   return ls_buf_xappend(this, pBuf, pool);  }

    static void xDestroy(AutoBuf *p, ls_xpool_t *pool)
    {   ls_buf_xd(p, pool);  }
};

class XAutoBuf : private ls_xbuf_t
{
private:
    XAutoBuf(const XAutoBuf &rhs);
    void operator=(const XAutoBuf &rhs);
public:
    explicit XAutoBuf(ls_xpool_t *pPool, int size = 1024)
    {   ls_xbuf(this, size, pPool);  }
    ~XAutoBuf()
    {   ls_xbuf_d(this);  }

    int     available() const       {   return buf.pbufend - buf.pend;  }

    char   *begin() const           {   return buf.pbuf;  }
    char   *end() const             {   return buf.pend;  }

    void    used(int size)          {   buf.pend += size;  }
    void    clear()                 {   buf.pend = buf.pbuf;  }

    int     capacity() const        {   return buf.pbufend - buf.pbuf;  }
    int     size() const            {   return buf.pend - buf.pbuf;  }

    int     reserve(int size)       {   return ls_xbuf_reserve(this, size);  }
    void    resize(int size)        {   ls_xbuf_resize(this, size);  }
    int     grow(int size)          {   return ls_xbuf_grow(this, size);  }

    bool    empty() const           {   return (buf.pbuf == buf.pend);  }
    bool    full() const            {   return (buf.pend == buf.pbufend);  }
    int     getOffset(const char *p) const    {   return p - buf.pbuf;  }
    char   *getp(int offset) const              {   return buf.pbuf + offset;  }
    void    swap(XAutoBuf &rhs)                 {   ls_xbuf_swap(this, &rhs);  }

    int     pop_front_to(char *pBuf, int size)
    {   return ls_xbuf_popfrontto(this, pBuf, size);  }

    int     pop_front(int size)     {   return ls_xbuf_popfront(this, size);  }
    int     pop_end(int size)       {   return ls_xbuf_popend(this, size);  }
    void    pop_back()              {   ls_xbuf_popend(this, 1);          }

    int     append(const char *pBuf, int size)
    {   return ls_xbuf_append2(this, pBuf, size);  }

    int     append(const char *pBuf)
    {   return ls_xbuf_append(this, pBuf);  }

    void    appendUnsafe(char ch)  {   *buf.pend++ = ch;  }

    int appendUnsafe(const char *pBuf, int size)
    {
        memmove(end(), pBuf, size);
        used(size);
        return size;
    }
};

#endif

