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
#include <util/iovec.h>

//static int addBytes( int initValue, const struct iovec &elem )
//{   return initValue + elem.iov_len;    }

int IOVec::bytes() const
{
    int total = 0;
    const struct iovec *p;
    for (p = begin(); p != end(); ++p)
        total += p->iov_len;
    return total;
}

int IOVec::shrinkTo(unsigned int newSize, unsigned int additional)
{
    iterator iter, iterEnd = end();
    unsigned int all = newSize + additional;
    unsigned int total = 0;
    for (iter = begin(); iter != iterEnd; ++iter)
    {
        if (total + iter->iov_len > all)
        {
            iter->iov_len = newSize - total;
            if (*((char *)iter->iov_base + iter->iov_len) == '\n')
                ++(iter->iov_len);
        }
        total += iter->iov_len;
        if (total >= newSize)
            break;
    }
    if (iter != iterEnd)
    {
        ++iter;
        m_pEnd = iter;
        //erase( iter, iterEnd );
    }
    return total;
}


int IOVec::finish(int &finishedLen)
{
    while (m_pEnd > m_pBegin)
    {
        if ((int)m_pBegin->iov_len > finishedLen)
        {
            m_pBegin->iov_len -= finishedLen;
            m_pBegin->iov_base = (char *)(m_pBegin->iov_base) + finishedLen;
            finishedLen = 0;
            return 1;
        }
        else
        {
            finishedLen -= m_pBegin->iov_len;
            m_pBegin++;
        }
    }
    clear();
    return 0;
}

void IOVec::adjust(const char *pOld, const char *pNew, int len)
{
    iterator iter, iterEnd = end();
    for (iter = begin(); iter != iterEnd; ++iter)
    {
        if (iter->iov_base >= pOld && iter->iov_base < pOld + len)
            iter->iov_base = (char *)iter->iov_base + (pNew - pOld);
    }
}



