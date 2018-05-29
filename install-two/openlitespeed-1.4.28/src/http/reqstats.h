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
#ifndef REQSTATS_H
#define REQSTATS_H



class ReqStats
{
    int     m_iReqPerSec;
    int     m_iTotalReqs;


    ReqStats(const ReqStats &rhs);
    void operator=(const ReqStats &rhs);
public:
    ReqStats();
    ~ReqStats();
    void incReqProcessed()  {   ++m_iReqPerSec;         }
    int  getRPS() const     {   return m_iReqPerSec;    }
    int  getTotal() const   {   return m_iTotalReqs;    }
    void reset()            {   m_iReqPerSec = 0;       }
    void resetTotal()       {   m_iTotalReqs = 0;       }
    void finalizeRpt();

};

#endif

