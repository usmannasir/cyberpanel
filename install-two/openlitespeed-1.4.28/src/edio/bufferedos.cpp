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
#include "bufferedos.h"
#include <util/iovec.h>
//#include <http/httplog.h>

#include <stdio.h>



BufferedOS::BufferedOS(OutputStream *pOS, int initSize)
    : m_pOS(pOS)
    , m_buf(initSize)
{}


BufferedOS::~BufferedOS()
{}


int BufferedOS::write(const char *pBuf, int size)
{
    return writeEx(pBuf, size, 1);
}


int BufferedOS::writev(const struct iovec *vector, int len)
{
    IOVec iov(vector, len);
    return writevEx(iov, 1);
}


int BufferedOS::writeEx(const char *pBuf, int size, int avoidCache)
{
    assert(m_pOS != NULL);
    int ret = 0;
    if (m_buf.empty())
    {
        ret = m_pOS->write(pBuf, size);
        if ((ret < size) && (ret >= avoidCache))
            ret = m_buf.cache(pBuf, size, ret);
//        LS_DBG_H( "bufferedOS::write() return %d, %d bytes in cache\n", ret, m_buf.size());
        return ret;
    }
    else
    {
        IOVec iov(pBuf, size);
        return writevEx(iov, avoidCache);
    }

}


int BufferedOS::cacheWritev(IOVec &vector, int total)
{
    if (m_buf.size() + total < 40960)
    {
        m_buf.cache(vector.get(), vector.len(), 0);
        return total;
    }
    else
        return writevEx(vector, 0);
}


int BufferedOS::writev(IOVec &vec)
{
    return writevEx(vec, 1);
}


int BufferedOS::writevEx(IOVec &vec, int avoidCache)
{
    assert(m_pOS != NULL);
    int ret;
    if (!m_buf.empty())
    {
        int oldLen = vec.len();
        m_buf.iovInsert(vec);
        //TEST: DEBUG Code
        //ret = 0;
        ret = m_pOS->writev(vec.get(), vec.len());
        vec.pop_front(vec.len() - oldLen);
        if (ret > 0)
        {
            int pop = ret;
            if (pop > m_buf.size())
                pop = m_buf.size();
            m_buf.pop_front(pop);
            ret -= pop;
        }
    }
    else
        //TEST: DEBUG Code
        //ret = 0;
        ret = m_pOS->writev(vec.get(), vec.len());
    if (ret >= avoidCache)
        ret = m_buf.cache(vec.get(), vec.len(), ret);
    //LS_DBG_H( "bufferedOS::writev() return %d, %d bytes in cache\n", ret, m_buf.size());
    return ret;
}


int BufferedOS::flush()
{
    assert(m_pOS != NULL);
    int ret = 0;
    if (!m_buf.empty())
    {
        IOVec iov;
        m_buf.getIOvec(iov);
        ret = m_pOS->writev(iov.get(), iov.len());
        if (ret >= 0)
        {
            if (m_buf.size() <= ret)
                m_buf.clear();
            else
                m_buf.pop_front(ret);
//          LS_DBG_H( "bufferedOS::flush() writen %d, %d bytes in cache\n",
//                      ret, m_buf.size());
            ret = m_buf.size();
        }
    }
    return ret;
}


int BufferedOS::close()
{
    assert(m_pOS != NULL);
    flush();
    return m_pOS->close();
}


