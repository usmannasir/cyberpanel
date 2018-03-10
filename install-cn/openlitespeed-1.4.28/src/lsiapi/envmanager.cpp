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
#include "envmanager.h"
#include <lsiapi/internal.h>

#include <unistd.h>
#include <fnmatch.h>

EnvManager::EnvManager()
{
    m_pEnvHashT = new HashStringMap<EnvHandler *>(29, 
                                                  GHash::hfCiString,
                                                  GHash::cmpCiString);
}


EnvManager::~EnvManager()
{
    m_pEnvHashT->release_objects();
    delete m_pEnvHashT;
    m_envList.release_objects();
}


int EnvManager::regEnvHandler(const char *name, unsigned int len,
                              lsi_callback_pf cb)
{
    EnvHandler *pEnvHandler = new EnvHandler;
    pEnvHandler->m_pName = strndup(name, len);
    pEnvHandler->m_iLen = len;
    pEnvHandler->m_cb = cb;
    if (strpbrk(pEnvHandler->m_pName, "*?") == NULL)
        m_pEnvHashT->insert(pEnvHandler->m_pName, pEnvHandler);
    else
        m_envList.append(pEnvHandler);
    return 0;
}


int EnvManager::delEnvHandler(const char *name, unsigned int len)
{
    return 0;
}


lsi_callback_pf EnvManager::findHandler(const char *name)
{
    HashStringMap<EnvHandler *>::iterator iter = m_pEnvHashT->find(name);
    if (iter != m_pEnvHashT->end())
        return iter.second()->m_cb;
    else
    {
        EnvHandler *pEnvHandler = m_envList.begin();
        while (pEnvHandler) // ; pEnvHandler != m_envList.tail(); pEnvHandler = (EnvHandler *)(pEnvHandler->next()))
        {
            if (fnmatch(pEnvHandler->m_pName, name, FNM_PATHNAME) == 0)
                return pEnvHandler->m_cb;
            else
                pEnvHandler = (EnvHandler *)(pEnvHandler->next());
        }
    }

    return NULL;
}


int EnvManager::execEnvHandler(LsiSession *session, lsi_callback_pf cb,
                               void *val, long valLen)
{
    lsi_param_t param;
    memset(&param, 0, sizeof(lsi_param_t));
    param.session = session;
    param.ptr1 = val;
    param.len1 = valLen;
    return cb(&param);
}


