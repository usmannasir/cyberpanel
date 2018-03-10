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
#ifndef ENVMANAGER_H
#define ENVMANAGER_H

#include <lsdef.h>
#include <ls.h>
#include <util/tsingleton.h>
#include <util/tlinklist.h>
#include <util/linkedobj.h>
#include <util/hashstringmap.h>

class LsiSession;

class EnvHandler : public LinkedObj
{
    friend class EnvManager;
private:
    char *m_pName;
    int m_iLen;
    lsi_callback_pf m_cb;

public:
    EnvHandler()    {   m_pName = NULL; m_iLen = 0;   };
    ~EnvHandler()   {   if (m_pName) free(m_pName);  };


    LS_NO_COPY_ASSIGN(EnvHandler);
};

class EnvManager : public TSingleton<EnvManager>
{
    friend class TSingleton<EnvManager>;

public:
    EnvManager();
    ~EnvManager();

    int regEnvHandler(const char *name, unsigned int len, lsi_callback_pf cb);
    int delEnvHandler(const char *name, unsigned int len);

    lsi_callback_pf findHandler(const char *name);
    int execEnvHandler(LsiSession *session, lsi_callback_pf cb, void *val,
                       long valLen);

private:
    HashStringMap<EnvHandler *> *m_pEnvHashT;
    TLinkList<EnvHandler>  m_envList;



    LS_NO_COPY_ASSIGN(EnvManager);
};

#endif // ENVMANAGER_H
