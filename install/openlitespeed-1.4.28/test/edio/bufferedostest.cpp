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
#ifdef RUN_TEST

#include "bufferedostest.h"
#include <edio/bufferedos.h>
#include <util/iovec.h>

#include <string>
#include <stdio.h>
#include <sys/uio.h>

#include "unittest-cpp/UnitTest++.h"

class TestBOS : public OutputStream
{
    std::string     m_buf;
    int             m_count;
public:
    TestBOS() : m_count(0) {}
    int write(const char *pBuf, int size)
    {
        m_count = !m_count;
        if (m_count)
        {
            m_buf.append(pBuf, 1);
            return 1;
        }
        else
            return 0;
    }
    int writev(const struct iovec *iov, int count)
    {
        m_count = !m_count;
        if (m_count)
        {
            m_buf.append((char *)iov->iov_base, 1);
            return 1;
        }
        else
            return 0;
    }

    int writev(IOVec &iov)
    {
        m_count = !m_count;
        if (m_count)
        {
            m_buf.append((char *)(iov.begin()->iov_base), 1);
            return 1;
        }
        else
            return 0;
    }
    int writev(IOVec &iov, int total)
    {
        return writev(iov);
    }
    void clearCache()
    {   m_buf.erase(m_buf.begin(), m_buf.end());  }
    int flush()
    {   return 0;}
    int close()
    {   clearCache(); return 0;  }
    const std::string &getBuf() const { return m_buf; }
};


TEST(BufferedOSTest_)
{
    const char *pString[] = { "Hello", " ", "World", "!" };
    IOVec iov;
    TestBOS testOS;
    BufferedOS bufos(&testOS, 256);
    iov.append(pString[0], 5);
    iov.append(pString[1], 1);
    int ret = bufos.cacheWritev(iov);
    CHECK(ret == 6);
    iov.clear();
    iov.append(pString[2], 5);
    iov.append(pString[3], 1);
    ret = bufos.cacheWritev(iov);
    CHECK(ret == 6);
    CHECK(bufos.getBuf()->size() == 11);
    for (int i = 2; i < 23; ++i)
    {
        ret = bufos.flush();
        CHECK(11 - (i >> 1) == ret);
    }
    CHECK(strcmp(testOS.getBuf().c_str(), "Hello World!") == 0);
}

#endif
