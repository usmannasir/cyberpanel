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

#include "chunkistest.h"
#include <http/chunkinputstream.h>

#include <string.h>

#include <string>
#include <vector>

#include <sys/uio.h>
#include "unittest-cpp/UnitTest++.h"

class TestIS : public CacheableIS
{
    std::vector< std::string> m_data;
    std::string               m_lineBuf;
public:
    void addData(const char *pData, int len)
    {
        std::string str(pData, len);
        m_data.push_back(str);
    }
    void addArrayData(const char *const *pData, int len)
    {
        for (int i = 0; i < len; ++i)
            addData(*(pData + i), strlen(*(pData + i)));
    }
    int read(char *pBuf, int size)
    {
        if (m_data.empty())
            return LS_FAIL;
        if (m_data[0].size() == 0)
        {
            m_data.erase(m_data.begin());
            return 0;
        }
        int len = size;
        if ((int)m_data[0].size() < len)
            len = m_data[0].size();
        memmove(pBuf, m_data[0].c_str(), len);
        m_data[0].erase(0, len);
        return len;
    }
    int readv(struct iovec *vector, size_t count)
    {
        const struct iovec *pEnd = vector + count;
        int total = 0;
        int ret;
        while (vector < pEnd)
        {
            if (vector->iov_len > 0)
            {
                ret = read((char *)vector->iov_base, vector->iov_len);
                if (ret > 0)
                    total += ret;
                if (ret == (int)vector->iov_len)
                {
                    ++vector;
                    continue;
                }
                if (total)
                    return total;
                return ret;
            }
            else
                ++vector;
        }
        return total;
    }

    int readLine(char *pBuf, int size)
    {
        if (m_data.empty())
            return LS_FAIL;
        if (m_data[0].size() == 0)
        {
            m_data.erase(m_data.begin());
            return 0;
        }

        const char *p = strchr(m_data[0].c_str(), '\n');
        int len;
        if (p)
            len = p - m_data[0].c_str() + 1;
        else
            len = m_data[0].size();
        if ((int)(len + m_lineBuf.size()) > size)
            return LS_FAIL;
        m_lineBuf += m_data[0].substr(0, len);
        m_data[0].erase(0, len);
        if (p)
        {
            len = m_lineBuf.size();
            memmove(pBuf, m_lineBuf.c_str(), len);
            m_lineBuf.erase(0, len);
            return len;
        }
        else
            return 0;

    }

    int cacheInput(int iPreferredLen)
    {
        return 0;
    }
};

static void readTillFail(ChunkInputStream &is, char *pBuf, int &len)
{
    int total = 0;
    int ret;
    do
    {
        ret = is.read(pBuf + total, len - total);
        if (ret > 0)
            total += ret;
        if (is.eos())
            break;
    }
    while (ret >= 0);
    len = total;
}

static void shouldSuccess(const char *const *data, int array_len)
{

    TestIS           testIS;
    ChunkInputStream chunkIS;
    char achBuf[100];
    testIS.addArrayData(data, array_len);
    chunkIS.setStream(&testIS);
    chunkIS.open();
    int total = 100;
    readTillFail(chunkIS, achBuf, total);
    CHECK(true == chunkIS.eos());
    CHECK(total == 11);
    CHECK(strncmp(achBuf, "Hello World", total) == 0);
    total = chunkIS.read(achBuf, 100);
    CHECK(total == 0);
    chunkIS.close();
    memset(achBuf, 0, sizeof(achBuf));
    testIS.addArrayData(data, array_len);
    chunkIS.open();
    char *p = achBuf;
    total = 0;
    int len = 1;
    while (len >= 0)
    {
        len = chunkIS.read(p, 1);
        if (len > 0)
        {
            total += len ;
            p += len ;
        }
        if (chunkIS.eos())
            break;
    }
    CHECK(true == chunkIS.eos());
    CHECK(total == 11);
    CHECK(strncmp(achBuf, "Hello World", total) == 0);
}

static void shouldInvalidChunkNum(const char *const *data, int array_len)
{
    TestIS           testIS;
    ChunkInputStream chunkIS;
    char achBuf[100];
    testIS.addArrayData(data, array_len);
    chunkIS.setStream(&testIS);
    chunkIS.open();
    int total = 100;
    readTillFail(chunkIS, achBuf, total);
    CHECK(total == 0);
}

static void testInvalidChunkSize()
{
    const char *test1[] =
    {
        "\r\nqrqwerg\r\n"
    };
    const char *test2[] =
    {
        "2\r23\r\n"
    };
    const char *test3[] =
    {
        "x3\naaa\r\n"
    };
    const char *test4[] =
    {
        "4\r 5\nwwww\r\n"
    };

    const char *test5[] =
    {
        "4g\r\nqqqq\r\n"
    };
    shouldInvalidChunkNum(test1, sizeof(test1) / sizeof(char *));
    shouldInvalidChunkNum(test2, sizeof(test2) / sizeof(char *));
    shouldInvalidChunkNum(test3, sizeof(test3) / sizeof(char *));
    shouldInvalidChunkNum(test4, sizeof(test4) / sizeof(char *));
    shouldInvalidChunkNum(test5, sizeof(test5) / sizeof(char *));
}

static void shouldInvalidChunkLen(const char *const *data, int array_len,
                                  int numShouldRead)
{
    TestIS           testIS;
    ChunkInputStream chunkIS;
    char achBuf[100];
    testIS.addArrayData(data, array_len);
    chunkIS.setStream(&testIS);
    chunkIS.open();
    int total = 100;
    readTillFail(chunkIS, achBuf, total);
    CHECK(total == numShouldRead);
}

static void testInvalidChunkLen()
{
    const char *test1[] =
    {
        "3\r\nqrqwerg\r\n"
    };
    const char *test2[] =
    {
        "5\r\n23\r\n"
    };
    shouldInvalidChunkLen(test1, sizeof(test1) / sizeof(char *), 3);
    shouldInvalidChunkLen(test2, sizeof(test2) / sizeof(char *), 4);
}

static void testSuccess()
{

    const char *test1[] =
    {
        "b; a=b; c=d\r\n"
        "Hello World\r\n"
        "0 ; e=\"f\"\r\ntrailer1=value1\r\ntrailer2=value2\r\n"
        "trailer3=value3\r\n\r\n"
    };

    const char *test2[] =
    {
        "b ; a=b; c=d\r\n",
        "Hello World\r\n",
        "0\r\ntrailer1=value1\r\ntrailer2=value2\r\n",
        "trailer3=value3\r",
        "\n\r", "\n"
    };

    const char *test3[] =
    {
        "5", "\r", "\n",
        "H", "e", "l", "l", "o", "\r", "\n",
        "6\r", "\n", " W", "or", "ld", "\r\n",
        "  0  \r\n\r\n"
    };

    const char *test4[] =
    {
        "1", "\r", "\n",
        "H\r\n",
        "1\r\n",
        "e\r\n",
        "2 \r\n",
        "ll\r\n",
        "1\r\n",
        "o", "\r", "\n",
        "6\r", "\n",
        " W", "or", "ld", "\r\n",
        "0", "\r", "\n\r", "\n"
    };
    shouldSuccess(test1, sizeof(test1) / sizeof(char *));
    shouldSuccess(test2, sizeof(test2) / sizeof(char *));
    shouldSuccess(test3, sizeof(test3) / sizeof(char *));
    shouldSuccess(test4, sizeof(test4) / sizeof(char *));
}

TEST(ChunkISTesttest)
{
    testSuccess();
    testInvalidChunkSize();
    testInvalidChunkLen();
}

#endif

