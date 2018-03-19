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
#ifndef CONNLIMITCTRL_H
#define CONNLIMITCTRL_H

#include <lsdef.h>
#include <util/tsingleton.h>

#include <inttypes.h>
#include <sys/types.h>


class HttpListenerList;

class ConnLimitCtrl : public TSingleton<ConnLimitCtrl>
{
    friend class TSingleton<ConnLimitCtrl>;

    int32_t    m_iMaxConns;
    int32_t    m_iMaxSSLConns;
    int32_t    m_iAvailConns;
    int32_t    m_iAvailSSLConns;
    int32_t    m_iLowWaterMark;
    int32_t    m_iConnOverflow;
    HttpListenerList   *m_pListeners;

    void testLimit();
    void testSSLLimit();
    void tryResume();
    void tryResumeSSL();
    void resumeSSL();
    void resumeAll();
    void resumeAllButSSL();

    ConnLimitCtrl();
public:
    ~ConnLimitCtrl();

    void incConn()
    {   --m_iAvailConns;        }
    void incSSLConn()
    {   --m_iAvailSSLConns;     }
    void incConn(int n)
    {   m_iAvailConns -= n;     }
    void incSSLConn(int n)
    {   m_iAvailSSLConns -= n;   }
    void decConn()
    {
        if (!(m_iAvailConns++))
            tryResume();
    }
    void decSSLConn()
    {
        if (!(m_iAvailSSLConns++))
            tryResumeSSL();
    }

    int  availConn() const
    {   return m_iAvailConns;     }

    int  availSSLConn() const
    {   return m_iAvailSSLConns;  }

    bool allowConn() const
    {   return m_iAvailConns > 0 ;  }

    bool allowSSLConn() const
    {   return m_iAvailSSLConns > 0 ;   }

    const int32_t *getAvailSSLConnAddr() const
    {   return &m_iAvailSSLConns;   }

    const int32_t *getAvailConnAddr() const
    {   return &m_iAvailConns;      }

    void suspendAll();
    void suspendSSL();

    void setListeners(HttpListenerList *pListeners)
    {   m_pListeners = pListeners;  }
    HttpListenerList *getListeners() const
    {   return m_pListeners;        }

    void setMaxConns(int32_t conns)
    {
        if (conns > 0)
        {
            m_iAvailConns += conns - m_iMaxConns;
            m_iMaxConns = conns;
            m_iLowWaterMark = m_iMaxConns / 5;
        }
    }
    void setMaxSSLConns(int32_t conns)
    {
        if (conns > 0)
        {
            m_iAvailSSLConns += conns - m_iMaxSSLConns;
            m_iMaxSSLConns = conns;
        }
    }

    int32_t getMaxConns() const
    {   return m_iMaxConns;                     }
    int32_t getMaxSSLConns() const
    {   return m_iMaxSSLConns;                  }
    void setConnOverflow(int over)
    {   m_iConnOverflow = over;                 }
    int32_t getConnOverflow() const
    {   return m_iConnOverflow;                 }

    void checkWaterMark();

    bool lowOnConnection() const
    {   return m_iAvailConns < m_iLowWaterMark;        }

    void tryAcceptNewConn();

    int32_t getSslAvailRatio() const
    {   return m_iAvailSSLConns * 100 / m_iMaxSSLConns;   }


    LS_NO_COPY_ASSIGN(ConnLimitCtrl);
};

#endif

