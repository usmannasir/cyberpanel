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
#include "sendfileinfo.h"
#include <http/staticfilecachedata.h>
#include <http/httpmime.h>
#include <util/datetime.h>
#include <assert.h>



SendFileInfo::SendFileInfo()
    : m_pFileData(NULL)
    , m_pECache(NULL)
    , m_pAioBuf(NULL)
    , m_lCurPos(0)
    , m_lCurEnd(0)
    , m_lAioLen(0)
{
}

SendFileInfo::~SendFileInfo()
{}

int SendFileInfo::getfd()
{
    if (!m_pECache)
        return (long)m_pParam;
    else
        return m_pECache->getfd();
}

void SendFileInfo::setFileData(StaticFileCacheData *pData)
{   
    if (m_pFileData == pData)
        return;
    if (m_pFileData)
        m_pFileData->decRef();
    m_pFileData = pData; 
    if (m_pFileData)
        m_pFileData->incRef();
}


void SendFileInfo::setECache(FileCacheDataEx *pCache) 
{
    if (m_pECache == pCache)
        return;
    if (m_pECache)
        m_pECache->decRef();
    m_pECache = pCache;   
    if (m_pECache)
        m_pECache->incRef();
}


void SendFileInfo::release()
{
    if (m_pFileData)
    {
        if (m_pFileData->decRef() == 0)
            m_pFileData->setLastAccess(DateTime::s_curTime);
        //m_pFileData->keepOrigFileClosed();
    }
    if (m_pECache && m_pECache->decRef() == 0)
    {
        if (m_pECache->getfd() != -1)
            m_pECache->closefd();
    }
    memset(this, 0, sizeof(SendFileInfo));

}

int SendFileInfo::readyCacheData(char compress, char mode)
{
    int ret;
    
    if ((compress) && (m_pFileData->getMimeType()->getExpires()->compressible()))
    {
        ret = m_pFileData->readyCompressed(mode);
        if (ret == 0)
        {
            if ((mode & SFCD_MODE_BROTLI) && (m_pFileData->getBrotli() != NULL))
                setECache(m_pFileData->getBrotli());
            else
                setECache(m_pFileData->getGzip());
            return 0;
        }
    }
    
    const char *pFileName = m_pFileData->getRealPath()->c_str();
    assert(pFileName && *pFileName);
    ret = 0;
    if ((!m_pFileData->getFileData()->isCached() &&
        (m_pFileData->getFileData()->getfd() == -1)))
        ret = m_pFileData->getFileData()->readyData(pFileName);
    if (ret == 0)
        setECache(m_pFileData->getFileData());
    return ret;
}
