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
#ifndef AIOSENDFILE_H
#define AIOSENDFILE_H

#include <edio/eventnotifier.h>
#include <lsr/ls_node.h>
#include <thread/workcrew.h>
#include <util/linkedobj.h>

#include <unistd.h>

#define LS_AIOSENDFILE_NUMWORKERS 1

#define AIOSFCB_FLAG_CANCEL       (1<<0)
#define AIOSFCB_FLAG_TRYAGAIN     (1<<1)

typedef struct ls_lfqueue_s ls_lfqueue_t;

class Aiosfcb : public DLinkedObj
{
private:
    ls_lfnodei_t    m_node;
    int             m_iSendFd;
    int             m_iReadFd;
    off_t           m_iOffset;
    size_t          m_iSize;
    int32_t         m_iFlag;
    int             m_iRet;
    void           *m_pUData;

    Aiosfcb(const Aiosfcb &rhs);
    void operator=(const Aiosfcb &rhs);

public:
    Aiosfcb()
        : DLinkedObj()
        , m_iSendFd(0)
        , m_iReadFd(0)
        , m_iOffset(0)
        , m_iSize(0)
        , m_iFlag(0)
        , m_iRet(0)
        , m_pUData(NULL)
    {
        m_node.next = NULL;
    }

    ~Aiosfcb()
    {}

    void reset()
    {
        memset(&m_iSendFd, 0, (char *)(&m_iRet + 1) - (char *)&m_iSendFd);
        m_pUData = NULL;
        setPrev(NULL);
        setNext(NULL);
        m_node.next = NULL;
    }

    void setSendFd(int iFd)       {   m_iSendFd = iFd;        }
    void setReadFd(int iFd)       {   m_iReadFd = iFd;        }
    void setOffset(off_t iOff)    {   m_iOffset = iOff;       }
    void setSize(size_t iSize)    {   m_iSize = iSize;        }
    void setFlag(int f)           {   m_iFlag |= f;           }
    void setRet(int iRet)         {   m_iRet = iRet;          }
    void setUData(void *pUData)   {   m_pUData = pUData;      }

    int     getSendFd() const       {   return m_iSendFd;       }
    int     getReadFd() const       {   return m_iReadFd;       }
    off_t   getOffset() const       {   return m_iOffset;       }
    size_t  getSize() const         {   return m_iSize;         }
    int32_t getFlag(int mask) const     {   return m_iFlag & mask;  }
    int     getRet() const          {   return m_iRet;          }
    void   *getUData() const        {   return m_pUData;        }
    ls_lfnodei_t *getNodePtr()      {   return &m_node;         }

    void    clearFlag(int f)      {   m_iFlag &= ~f;           }

    static Aiosfcb *getCbPtr(ls_lfnodei_t *pNode);
};

class AioSendFile : public EventNotifier
{
    ls_lfqueue_t *m_pFinishedQueue;
    WorkCrew     m_wc;

    static void *aioSendFile(ls_lfnodei_t *item);

private:
    AioSendFile(const AioSendFile &rhs);
    void operator=(const AioSendFile &rhs);

public:

    AioSendFile();

    ~AioSendFile();

    int startProcessor()
    {
#if !defined( NO_SENDFILE )
        return m_wc.startJobProcessor(LS_AIOSENDFILE_NUMWORKERS,
                                      m_pFinishedQueue,
                                      aioSendFile);
#else
        return LS_FAIL;
#endif
    }

    int addJob(Aiosfcb *item)
    {   return m_wc.addJob(item->getNodePtr()); }

    int onNotified(int count);

    virtual int processEvent(Aiosfcb *event) = 0;
};



#endif //AIOSENDFILE_H


