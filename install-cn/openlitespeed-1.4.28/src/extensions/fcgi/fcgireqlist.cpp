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
#include "fcgireqlist.h"
#include "fcgirequest.h"

#include <util/gpointerlist.h>

#include <assert.h>


typedef TPointerList<FcgiRequest>   RequestList;
class FcgiReqListData : public RequestList
{
};


FcgiReqList::FcgiReqList()
    : m_iActiveReqs(0)
    , m_pData(NULL)
{
    m_pData = new FcgiReqListData();
}


FcgiReqList::~FcgiReqList()
{
    if (m_pData != NULL)
        delete m_pData;
}


int FcgiReqList::regist(FcgiRequest *pReq)
{
    assert(pReq != NULL);
    int size = m_pData->size();
    int i;
    for (i = 0; i < size; i++)
    {
        if ((*m_pData)[i] != NULL)
        {
            (*m_pData)[i] = pReq;
            break;
        }
    }
    if (i == size)
        m_pData->push_back(pReq);
    pReq->setId(i + 1);
    ++m_iActiveReqs;
    return i + 1;
}


void FcgiReqList::unregist(FcgiRequest *pReq)
{
    assert(pReq);
    int size = m_pData->size();
    if (size <= pReq->getId())
    {
        assert(pReq->getId() > 0);
        assert(pReq == (*m_pData)[pReq->getId() - 1]);
        (*m_pData)[pReq->getId() - 1] = NULL;
        --m_iActiveReqs;
    }

}


FcgiRequest *FcgiReqList::get(int iId)
{
    if ((iId < 1) || (iId > (int)m_pData->size()))
        return NULL;
    FcgiRequest *pRet = (*m_pData)[iId - 1];
    return pRet;
}


FcgiRequest *FcgiReqList::first()
{
    return next(0);
}


FcgiRequest *FcgiReqList::next(int id)
{
    int size = m_pData->size();
    int i;
    FcgiRequest *pRet = NULL;
    for (i = id ; i < size; ++i)
    {
        pRet = (*m_pData)[i];
        if (pRet)
            break;
    }
    return pRet;
}


