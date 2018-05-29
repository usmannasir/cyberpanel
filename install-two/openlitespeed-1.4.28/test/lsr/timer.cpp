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
#include <iostream>
#include <sstream>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <math.h>

class Timer
{
    timeval    m_start;
    timeval    m_end;
    char      *m_tag;
    int        stopped;
    int        counter;
public:
    Timer(const char *tag = "TEST")
    {
        counter = 0;
        stopped = 0;
        if (tag)
            m_tag = strdup(tag);
        else
            m_tag = strdup("");
        m_end.tv_sec = 0;
        m_end.tv_usec = 0;
        start();
    }
    ~Timer()
    {
        if (!stopped)
            show();
        if (m_tag)
        {
            free(m_tag);
            m_tag = 0;
        }
    }
    std::string msStr()
    {
        std::ostringstream out;
        if (counter)
        {
            uint32_t x = ms();
            out << m_tag << " " << x << " usec [" << (int)(x / counter) << "]" ;
        }
        else
            out << m_tag << " " << ms() << " usec" ;
        return out.str();
    }
    uint32_t ms()
    {
        if (!stopped)
            stop();

        return ((m_end.tv_sec - m_start.tv_sec) * 1000000)
               + (m_end.tv_usec - m_start.tv_usec);
    }
    void show()
    {
        if (!stopped)
            stop();
        std::cout << msStr() << "\n";
    }
    inline void start()
    {
        stopped = 0;
        gettimeofday(&m_start, NULL);
    }
    inline void stop()
    {
        gettimeofday(&m_end, NULL);
        stopped = 1;
    }
    inline void setCount(int c)
    { counter = c; };

    friend std::ostream &operator<< (std::ostream &os, Timer &);
};

std::ostream &operator<< (std::ostream &os, Timer &o)
{
    os << o.msStr();
    return  os;
}

