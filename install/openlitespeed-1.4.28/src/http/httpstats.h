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
#ifndef HTTPSTATS_H
#define HTTPSTATS_H

class ReqStats;
class HttpStats
{
    static int      s_i503AutoFix;
    static int      s_i503Errors;
    static long     s_iBytesRead;
    static long     s_iBytesWritten;
    static long     s_iSSLBytesRead;
    static long     s_iSSLBytesWritten;
    static int      s_iIdleConns;
    static ReqStats s_reqStats;

    HttpStats() {};
    ~HttpStats() {};
    HttpStats(const HttpStats &rhs);
    void operator=(const HttpStats &rhs);
public:
    static int  get503AutoFix()                 {   return s_i503AutoFix;     }
    static void set503AutoFix(int val)          {   s_i503AutoFix = val;      }

    static int  get503Errors()                  {   return s_i503Errors;      }
    static void set503Errors(int val)           {   s_i503Errors = val;       }
    static void inc503Errors(int val = 1)       {   s_i503Errors += val;      }

    static long getBytesRead()                  {   return s_iBytesRead;      }
    static void setBytesRead(long val)          {   s_iBytesRead = val;       }
    static void incBytesRead(long val = 1)      {   s_iBytesRead += val;      }

    static long getBytesWritten()               {   return s_iBytesWritten;   }
    static void setBytesWritten(long val)       {   s_iBytesWritten = val;    }
    static void incBytesWritten(long val = 1)   {   s_iBytesWritten += val;   }

    static long getSSLBytesRead()               {   return s_iSSLBytesRead;   }
    static void setSSLBytesRead(long val)       {   s_iSSLBytesRead = val;    }
    static void incSSLBytesRead(long val = 1)   {   s_iSSLBytesRead += val;   }

    static long getSSLBytesWritten()            {   return s_iSSLBytesWritten;}
    static void setSSLBytesWritten(long val)    {   s_iSSLBytesWritten = val; }
    static void incSSLBytesWritten(long val = 1) {   s_iSSLBytesWritten += val;}

    static int  getIdleConns()                  {   return s_iIdleConns;      }
    static void setIdleConns(int val)           {   s_iIdleConns = val;       }
    static void incIdleConns(int val = 1)       {   s_iIdleConns += val;      }
    static void decIdleConns(int val = 1)       {   s_iIdleConns -= val;      }

    static ReqStats *getReqStats()              {   return &s_reqStats;       }

};

#endif // HTTPSTATS_H

