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
#include "lsiapihooks.h"

#include <lsiapi/internal.h>
#include <log4cxx/logger.h>
#include <log4cxx/logsession.h>

#include <string.h>

const char *LsiApiHooks::s_pHkptName[LSI_HKPT_TOTAL_COUNT] =
{
    "L4_BEGINSESSION",
    "L4_ENDSESSION",
    "L4_RECVING",
    "L4_SENDING",
    "HTTP_BEGIN",
    "RECV_REQ_HEADER",
    "URI_MAP",
    "HTTP_AUTH",
    "RECV_REQ_BODY",
    "RCVD_REQ_BODY",
    "RECV_RESP_HEADER",
    "RECV_RESP_BODY",
    "RCVD_RESP_BODY",
    "HANDLER_RESTART",
    "SEND_RESP_HEADER",
    "SEND_RESP_BODY",
    "HTTP_END",
    "MAIN_INITED",
    "MAIN_PREFORK",
    "MAIN_POSTFORK",
    "WORKER_POSTFORK",
    "WORKER_ATEXIT",
    "MAIN_ATEXIT"
};

LsiApiHooks LsiApiHooks::s_hooks[LSI_HKPT_TOTAL_COUNT];
ServerSessionHooks *LsiApiHooks::s_pServerSessionHooks = NULL;
static LsiApiHooks *s_releaseDataHooks = NULL;

#define LSI_FLAG_NO_INTERRUPT  1


void LsiApiHooks::initGlobalHooks()
{
    s_pServerSessionHooks = new ServerSessionHooks();
    s_releaseDataHooks = new LsiApiHooks[LSI_DATA_COUNT];

    s_hooks[ LSI_HKPT_L4_BEGINSESSION ].setGlobalFlag(
        LSI_FLAG_NO_INTERRUPT);
    s_hooks[ LSI_HKPT_L4_ENDSESSION ].setGlobalFlag(
        LSI_FLAG_NO_INTERRUPT);

    s_hooks[ LSI_HKPT_HTTP_BEGIN ].setGlobalFlag(LSI_FLAG_NO_INTERRUPT);
    s_hooks[ LSI_HKPT_HTTP_END ].setGlobalFlag(LSI_FLAG_NO_INTERRUPT);
    s_hooks[ LSI_HKPT_HANDLER_RESTART ].setGlobalFlag(
        LSI_FLAG_NO_INTERRUPT);
}


int LsiApiHooks::runForwardCb(lsi_param_t *param)
{
    const lsi_hookinfo_t *hookInfo = param->hook_chain;
    const LsiApiHooks *pHooks = hookInfo->hooks;
    const int8_t *pEnableArray = hookInfo->enable_array;
    int iCount = (lsiapi_hook_t *)param->cur_hook - pHooks->begin();
    int iSize = pHooks->size();
    for (; iCount < iSize; ++iCount)
    {
        if ((pEnableArray[LSIHOOKS_GETINDEX(iCount)]
             & (1 << LSIHOOKS_GETOFFSET(iCount))) != 0)
        {
            param->cur_hook = (void *)pHooks->get(iCount);
            return (*(((lsiapi_hook_t *)param->cur_hook)->cb))(param);

        }
    }

    return hookInfo->term_fn((LsiSession *)param->session,
                             (void *)param->ptr1,
                             param->len1);
}


int LsiApiHooks::runBackwardCb(lsi_param_t *param)
{
    const lsi_hookinfo_t *hookInfo = param->hook_chain;
    const LsiApiHooks *pHooks = hookInfo->hooks;
    int8_t *pEnableArray = hookInfo->enable_array;
    int iCount = (lsiapi_hook_t *)param->cur_hook - pHooks->begin();
    for (; iCount >= 0; --iCount)
    {
        if ((pEnableArray[LSIHOOKS_GETINDEX(iCount)]
             & (1 << LSIHOOKS_GETOFFSET(iCount))) != 0)
        {
            param->cur_hook = (void *)pHooks->get(iCount);
            return (*(((lsiapi_hook_t *)param->cur_hook)->cb))(param);
        }
    }

    return hookInfo->term_fn((LsiSession *)param->session,
                             (void *)param->ptr1,
                             param->len1);
}


LsiApiHooks *LsiApiHooks::getReleaseDataHooks(int index)
{   return &s_releaseDataHooks[index];   }


LsiApiHooks::LsiApiHooks(const LsiApiHooks &other)
    : m_pHooks(NULL)
    , m_iCapacity(0)
    , m_iEnd(0)
    , m_iFlag(0)
{
    if (reallocate(other.size() + 4) != -1)
    {
        memcpy(m_pHooks, other.begin(),
               (char *)other.end() - (char *)other.begin());
        m_iEnd = other.size();
    }
}


int LsiApiHooks::copy(const LsiApiHooks &other)
{
    if (m_iCapacity < other.size())
        if (reallocate(other.size() + 4) == -1)
            return LS_FAIL;
    memcpy(m_pHooks, other.begin(),
           (char *)other.end() - (char *)other.begin());
    m_iEnd = other.size();
    return 0;
}


int LsiApiHooks::reallocate(int capacity)
{
    lsiapi_hook_t *pHooks;
    int size = this->size();
    if (capacity < size)
        capacity = size;
    pHooks = (lsiapi_hook_t *)malloc(capacity * sizeof(lsiapi_hook_t));
    if (!pHooks)
        return LS_FAIL;
    if (m_pHooks)
    {
        memcpy(pHooks, m_pHooks, size * sizeof(lsiapi_hook_t));
        free(m_pHooks);
    }

    m_pHooks = pHooks;
    m_iEnd = size;
    m_iCapacity = capacity;
    return capacity;
}


//For same cb and same priority in same module, it will fail to add, but return 0
short LsiApiHooks::add(const lsi_module_t *pModule, lsi_callback_pf cb,
                       short priority, short flag)
{
    lsiapi_hook_t *pHook;
    if (size() == m_iCapacity)
    {
        if (reallocate(m_iCapacity + 4) == -1)
            return LS_FAIL;

    }
    for (pHook = begin(); pHook < end(); ++pHook)
    {
        if (pHook->priority > priority)
            break;
        else if (pHook->priority == priority && pHook->module == pModule
                 && pHook->cb == cb)
            return 0;  //already added
    }

    memmove(pHook + 1, pHook, (char *)end() - (char *)pHook);
    ++m_iEnd;
    pHook->module = pModule;
    pHook->cb = cb;
    pHook->priority = priority;
    pHook->flag = flag;
    return pHook - begin();
}


lsiapi_hook_t *LsiApiHooks::find(const lsi_module_t *pModule,
                                 lsi_callback_pf cb)
{
    lsiapi_hook_t *pHook;
    for (pHook = begin(); pHook < end(); ++pHook)
    {
        if ((pHook->module == pModule) && (pHook->cb == cb))
            return pHook;
    }
    return NULL;
}


int LsiApiHooks::remove(lsiapi_hook_t *pHook)
{
    if ((pHook < begin()) || (pHook >= end()))
        return LS_FAIL;
    if (pHook != end() - 1)
        memmove(pHook, pHook + 1, (char *)end() - (char *)pHook);
    --m_iEnd;
    return 0;
}


//COMMENT: if one module add more hooks at this level, the return is the first one!!!!
lsiapi_hook_t *LsiApiHooks::find(const lsi_module_t *pModule) const
{
    lsiapi_hook_t *pHook;
    for (pHook = begin(); pHook < end(); ++pHook)
    {
        if (pHook->module == pModule)
            return pHook;
    }
    return NULL;

}


// lsiapi_hook_t *LsiApiHooks::find(const lsi_module_t *pModule,
//                                  int *index) const
// {
//     lsiapi_hook_t *pHook = find(pModule);
//     if (pHook)
//         *index = pHook - begin();
//     return pHook;
// }


//COMMENT: if one module add more hooks at this level, the return of
//LsiApiHooks::find( const lsi_module_t *pModule ) is the first one!!!!
//But the below function will remove all the hooks
int LsiApiHooks::remove(const lsi_module_t *pModule)
{
    lsiapi_hook_t *pHook;
    for (pHook = begin(); pHook < end(); ++pHook)
    {
        if (pHook->module == pModule)
            remove(pHook);
    }

    return 0;
}


//need to check Hook count before call this function
int LsiApiHooks::runCallback(int level, lsi_param_t *param) const
{
    int ret = 0;
    lsi_param_t rec1;
    lsiapi_hook_t *hook;
    int8_t *pEnableArray = param->hook_chain->enable_array;
    int iCount = (lsiapi_hook_t *)param->cur_hook - begin();
    int iSize = size();

    for (; iCount < iSize; ++iCount)
    {
        if ((pEnableArray[LSIHOOKS_GETINDEX(iCount)]
             & (1 << LSIHOOKS_GETOFFSET(iCount))) == 0)
            continue;

        hook = get(iCount);

        rec1 = *param;
        rec1.cur_hook = (void *)hook;

        LogSession *pTracker = NULL;
        if (log4cxx::Level::isEnabled(log4cxx::Level::DBG_MEDIUM))
        {
            if (param->session)
                pTracker = ((LsiSession *)param->session)->getLogSession();
            LS_DBG_M(pTracker, "[%s] run Hook function for [Module:%s] session=%p",
                     s_pHkptName[ level ],
                     MODULE_NAME(hook->module), param->session);
        }

        ret = hook->cb(&rec1);

        if (log4cxx::Level::isEnabled(log4cxx::Level::DBG_MEDIUM))
        {
            LS_DBG_M(pTracker, "[%s] [Module:%s]  session=%p ret %d",
                     s_pHkptName[ level ],
                     MODULE_NAME(hook->module), param->session, ret);
        }
        if ((ret == LSI_SUSPEND)
            || ((ret != 0) && !(m_iFlag & LSI_FLAG_NO_INTERRUPT)))
        {
            param->cur_hook = hook;
            return ret;
        }
    }
    param->cur_hook = end();
    return ret;
}


int LsiApiHooks::runCallback(int level, int8_t *pEnableArray,
                             LsiSession *session,
                             void *param1, int paramLen1, int *flag_out, int flag_in,
                             lsi_module_t *pModule) const
{
    lsiapi_hook_t *pHook = NULL;

    if (pModule)
    {
        ModIndex *pModIndex = MODULE_HOOKINDEX(pModule);
        pHook = begin() + pModIndex->getLevel(level);
//         pHook = find(pModule);
    }

    lsi_hookinfo_t info = { this, pEnableArray, (int8_t)level, NULL };
    lsi_param_t param =
    {
        session,
        &info,
        (pHook ?  pHook + 1 : begin()),
        param1,
        paramLen1,
        flag_out,
        flag_in
    };

    return runCallback(level, &param);
}


int LsiApiHooks::initModuleEnableHooks()
{
    const LsiApiHooks *pLevel;
    lsiapi_hook_t *pBegin, *pEnd;
    int i, iIdx;
    for (i = LSI_HKPT_L4_BEGINSESSION; i < LSI_HKPT_SESSION_COUNT; ++i)
    {
        iIdx = 0;
        pLevel = LsiApiHooks::getGlobalApiHooks(i);
        if (pLevel->size() < 1)
            continue;
        pEnd = pLevel->end();
        for (pBegin = pLevel->begin(); pBegin < pEnd; ++pBegin)
        {
            MODULE_HOOKINDEX(pBegin->module)->setLevel(i, iIdx);
            ++iIdx;
        }
    }
    return LS_OK;
}


ModIndex::ModIndex()
{
    int i;
    for (i = 0; i < LSI_HKPT_TOTAL_COUNT; ++i)
        m_aIndices[i] = -1;
}


ModIndex *ModIndex::getModIndex(const lsi_module_t *pModule)
{
    return MODULE_HOOKINDEX(pModule);
}




