/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#ifndef LSJSENGINE_H
#define LSJSENGINE_H

#include <ls.h>

#include <sys/stat.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


class LsJsUserParam;

//
//  LsJsEngine - the JS dispatcher
//
class LsJsEngine
{
    static int
    s_ready;        // init is good and ready to load scripts
    static int          s_firstTime;
    static char        *s_serverSocket;

public:
    LsJsEngine();
    ~LsJsEngine();

    // only three functions will be used to by handler
    // static int init( TYPE type, const char * pDynLibPath );
    static int init();
    static int isReady(const lsi_session_t
                       *session);                      // setup Session and get ready
    static int runScript(const lsi_session_t *session
                         , LsJsUserParam *pUser
                         , const char *scriptpath
                        );
public:
    // module parameter setup
    static void *parseParam(module_param_info_t *param
                            , int param_count
                            , void *initial_config
                            , int level
                            , const char *name);
    static void removeParam(void *config);

private:
    LsJsEngine(const LsJsEngine &other);
    LsJsEngine &operator=(const LsJsEngine &other);
    bool operator==(const LsJsEngine &other);

    static int tcpDomainSocket(const char *path);
};

//
//  @brief LsJsUserParam
//  @brief run time param for all levels
//
class LsJsUserParam
{
    int         m_level;
    int         m_ready;
    int         m_data;
public:
    LsJsUserParam(int level)
        : m_level(level)
        , m_ready(1)
        , m_data(0)
    { }

    ~LsJsUserParam()
    {
    };

    int isReady() const
    {   return m_ready; }

    void setReady(int flag)
    {   m_ready = flag; }

    void setLevel(int level)
    {   m_level = level; }

    int level() const
    {   return m_level; }

    void setData(int data)
    {   m_data = data; }

    int data() const
    {   return m_data; }

    LsJsUserParam &operator= (const LsJsUserParam &other)
    {
        m_ready = other.m_ready;
        return *this;
    }

private:
    LsJsUserParam(const LsJsUserParam &other);
    bool operator==(const LsJsUserParam &other);
};

#endif // LSJSENGINE_H
