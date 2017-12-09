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
#include "hashdatacache.h"

#include <lsr/ls_fileio.h>
#include <util/keydata.h>
#include <util/pool.h>

#include <errno.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>


HashDataCache::~HashDataCache()
{
}


const KeyData *HashDataCache::getData(const char *pKey)
{
    const_iterator iter;
    iter = find(pKey);
    if (iter != end())
        return iter.second();
    return NULL;
}


DataStore::~DataStore()
{
    if (m_pDataStoreUri)
        Pool::deallocate2(m_pDataStoreUri);
}


void DataStore::setDataStoreURI(const char *pURI)
{
    if (m_pDataStoreUri)
        Pool::deallocate2(m_pDataStoreUri);
    m_pDataStoreUri = Pool::dupstr(pURI);
}


int FileStore::isStoreChanged(long time)
{
    long curTime = ::time(NULL);
    if (curTime != m_lastCheckTime)
    {
        struct stat st;
        m_lastCheckTime = curTime;
        if (ls_fio_stat(getDataStoreURI(), &st) == -1)
            return LS_FAIL;
        if (m_modifiedTime != st.st_mtime)
            return 1;
    }
    if (time < m_modifiedTime)
        return 1;
    return 0;
}


int FileStore::open()
{
    if (m_pFile == NULL)
    {
        struct stat st;
        if (ls_fio_stat(getDataStoreURI(), &st) == -1)
            return errno;
        if (S_ISDIR(st.st_mode))
            return EINVAL;
        m_pFile = fopen(getDataStoreURI(), "r");
        if (m_pFile == NULL)
            return errno;
        m_modifiedTime = st.st_mtime;
    }
    return 0;
}


void FileStore::close()
{
    if (m_pFile)
    {
        fclose(m_pFile);
        m_pFile = NULL;
    }
}


#define TEMP_BUF_LEN 4096


KeyData *FileStore::getNext()
{
    char pBuf[TEMP_BUF_LEN + 1];
    if (!m_pFile)
        return NULL;
    while (!feof(m_pFile))
    {
        if (fgets(pBuf, TEMP_BUF_LEN, m_pFile))
        {
            KeyData *pData = parseLine(pBuf, &pBuf[strlen(pBuf)]);
            if (pData)
                return pData;
        }
    }
    return NULL;
}


KeyData *FileStore::getDataFromStore(const char *pKey, int keyLen)
{

    char *pPos;
    char pBuf[TEMP_BUF_LEN + 1];
    KeyData *pData = NULL;
    if (open())
        return NULL;
    fseeko(m_pFile, 0, SEEK_SET);
    while (!feof(m_pFile))
    {
        if ((fgets(pBuf, TEMP_BUF_LEN, m_pFile) == NULL)
            || (strncmp(pBuf, pKey, keyLen) != 0))
            continue;
        char ch;
        pPos = pBuf + keyLen;
        while (((ch = *pPos) == ' ') || (ch == '\t'))
            ++pPos;
        if (*pPos++ == ':')
        {
            char *pLineEnd = strlen(pPos) + pPos;
            while (((ch = pLineEnd[-1]) == '\n') || (ch == '\r'))
                * (--pLineEnd) = 0;
            pData = parseLine(pKey, keyLen, pPos, pLineEnd);
            if (pData)
                break;
        }
    }
    close();
    return pData;
}



