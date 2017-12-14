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
#ifndef LSIAPIHOOKS_H
#define LSIAPIHOOKS_H

#include <ls.h>
#include <lsdef.h>

#include <stdlib.h>

class LsiSession;
class LsiApiHooks;

class IolinkSessionHooks;
class HttpSessionHooks;
class ServerSessionHooks;

typedef int (* filter_term_fn)(LsiSession *, void *, int);

#define LSI_HKPT_L4_COUNT       (LSI_HKPT_HTTP_BEGIN - LSI_HKPT_L4_BEGINSESSION)
#define LSI_HKPT_HTTP_COUNT     (LSI_HKPT_HTTP_END - LSI_HKPT_HTTP_BEGIN + 1)
#define LSI_HKPT_SESSION_COUNT  (LSI_HKPT_HTTP_COUNT + LSI_HKPT_L4_COUNT)
#define LSI_HKPT_SERVER_COUNT   (LSI_HKPT_TOTAL_COUNT - LSI_HKPT_L4_COUNT - LSI_HKPT_HTTP_COUNT)


typedef struct lsiapi_hook_s
{
    const lsi_module_t *module;
    lsi_callback_pf     cb;
    short               priority;
    short               flag;
} lsiapi_hook_t;


typedef struct lsi_hookinfo_s
{
    const LsiApiHooks  *hooks;
    int8_t             *enable_array;
    int8_t              hook_level;
    filter_term_fn      term_fn;
} lsi_hookinfo_t;


class LsiApiHooks
{
public:
    explicit LsiApiHooks(int capacity = 4)
        : m_pHooks(NULL)
        , m_iCapacity(0)
        , m_iEnd(0)
        , m_iFlag(0)
    {
        reallocate(capacity);
    }

    ~LsiApiHooks()
    {
        if (m_pHooks)
            free(m_pHooks);
    }

    LsiApiHooks(const LsiApiHooks &other);

    short size() const                      {   return m_iEnd;              }
    short capacity() const                  {   return m_iCapacity;         }

    short getGlobalFlag() const             {   return m_iFlag;             }
    void  setGlobalFlag(short f)            {   m_iFlag |= f;               }

    short add(const lsi_module_t *pModule, lsi_callback_pf cb, short priority,
              short flag = 0);

    int remove(lsiapi_hook_t *pHook);
    int remove(const lsi_module_t *pModule);

    lsiapi_hook_t *find(const lsi_module_t *pModule, lsi_callback_pf cb);
    lsiapi_hook_t *find(const lsi_module_t *pModule) const;
    //lsiapi_hook_t *find(const lsi_module_t *pModule, int *index) const;


    lsiapi_hook_t *get(int index) const     {   return m_pHooks + index;    }
    lsiapi_hook_t *begin() const            {   return m_pHooks;            }
    lsiapi_hook_t *end() const              {   return m_pHooks + m_iEnd;   }
    LsiApiHooks *dup() const
    {   return new LsiApiHooks(*this);    }

    int copy(const LsiApiHooks &other);


    int runCallback(int level, lsi_param_t *param) const;
    int runCallback(int level, int8_t *pEnableArray, LsiSession *session,
                    void *param1, int paramLen1, int *flag_out, int flag_in,
                    lsi_module_t *pModule = NULL) const;

    int runCallbackNoParam(int level, int8_t *pEnableArray,
                           LsiSession *session,
                           lsi_module_t *pModule = NULL) const
    {
        return runCallback(level, pEnableArray, session, NULL,
                           0, NULL, 0, pModule);
    }


    static int runForwardCb(lsi_param_t *param);
    static int runBackwardCb(lsi_param_t *param);



    static ServerSessionHooks *s_pServerSessionHooks;
    static ServerSessionHooks *getServerSessionHooks()
    {   return s_pServerSessionHooks;   }

    static int initModuleEnableHooks();



    static const LsiApiHooks *getGlobalApiHooks(int index)
    {   return &s_hooks[index];         }
    static LsiApiHooks *getReleaseDataHooks(int index);
    static inline const char *getHkptName(int index)
    {   return s_pHkptName[ index ];    }
    static void initGlobalHooks();


private:

    LsiApiHooks &operator=(const LsiApiHooks &other);
    bool operator==(const LsiApiHooks &other) const;

    int reallocate(int capacity);

private:
    lsiapi_hook_t   *m_pHooks;
    short            m_iCapacity;
    short            m_iEnd;
    short            m_iFlag;

public:
    static const char  *s_pHkptName[LSI_HKPT_TOTAL_COUNT];
    static LsiApiHooks  s_hooks[LSI_HKPT_TOTAL_COUNT];
};


class ModIndex
{
    int16_t  m_aIndices[LSI_HKPT_TOTAL_COUNT];

    void operator=(const ModIndex &rhs);
    ModIndex(const ModIndex &rhs);

public:
    ModIndex();
    ~ModIndex();

    void setLevel(int level, int16_t value) {   m_aIndices[level] = value;  }
    int getLevel(int level)                 {   return m_aIndices[level];   }

    static ModIndex *getModIndex(const lsi_module_t *pModule);
};

#define LSIHOOKS_BITS 8
#define LSIHOOKS_POWER 3
#define LSIHOOKS_GETINDEX(levelSize) ((levelSize) >> LSIHOOKS_POWER)
#define LSIHOOKS_GETOFFSET(levelSize) ((levelSize) & (LSIHOOKS_BITS - 1))

template< int B, int S >
class SessionHooks
{
    enum
    {
        UNINIT = 0,
        INITED,
        HASOWN,
    };



private:
    int8_t *m_pEnableArray[S];
    short   m_iFlag[S];
    short   m_iStatus;

    static int getLevelSize(int iNumMods)
    {
        return ((iNumMods + (LSIHOOKS_BITS - 1))
                & ~(LSIHOOKS_BITS - 1)) >> LSIHOOKS_POWER;
    }

    void inheritFromParent(SessionHooks<B, S> *parentSessionHooks)
    {
        int i, level, iLevelSize;
        assert(m_iStatus != UNINIT);
        if (m_iStatus == HASOWN)
            return;

        for (i = 0; i < S; ++i)
        {
            level = B + i;
            iLevelSize = getLevelSize(
                             LsiApiHooks::getGlobalApiHooks(level)->size());
            memcpy(m_pEnableArray[i],
                   parentSessionHooks->getEnableArray(level),
                   iLevelSize * sizeof(int8_t));
        }
        memcpy(m_iFlag, parentSessionHooks->m_iFlag, S * sizeof(short));
    }


    void updateFlag(int level)
    {
        int i;
        int index = level - B;
        m_iFlag[index] = 0;
        const LsiApiHooks *pLevel = LsiApiHooks::getGlobalApiHooks(level);
        int iLevelSize = pLevel->size();
        int8_t *pEnableArray = m_pEnableArray[index];

        for (i = 0; i < iLevelSize; ++i)
        {
            if (pEnableArray[LSIHOOKS_GETINDEX(i)]
                & (1 << LSIHOOKS_GETOFFSET(i)))
                m_iFlag[index] |= pLevel->get(i)->flag | LSI_FLAG_ENABLED;
        }
    }


    void updateFlag()
    {
        for (int i = 0; i < S; ++i)
            updateFlag(B + i);
    }


    void inheritFromGlobal()
    {
        int iLevelSize, i, j;
        lsiapi_hook_t *pHook;
        int8_t *pEnableArray;
        assert(m_iStatus != UNINIT);
        if (m_iStatus == HASOWN)
            return;

        for (i = 0; i < S; ++i)
        {
            iLevelSize = LsiApiHooks::getGlobalApiHooks(B + i)->size();
            pHook = LsiApiHooks::getGlobalApiHooks(B + i)->begin();
            pEnableArray = m_pEnableArray[i];
            for (j = 0; j < iLevelSize; ++j)
            {
                if (pHook->flag & LSI_FLAG_ENABLED)
                {
                    pEnableArray[LSIHOOKS_GETINDEX(j)]
                    |= 1 << LSIHOOKS_GETOFFSET(j);
                }
                ++pHook;
            }
        }
        updateFlag();
    }


    //init and set the disable array from the global(in the LsiApiHook flag)
    int initSessionHooks()
    {
        int iSize;
        if (m_iStatus != UNINIT)
            return 1;

        for (int i = 0; i < S; ++i)
        {
            iSize = getLevelSize(
                        LsiApiHooks::getGlobalApiHooks(B + i)->size());
            m_pEnableArray[i] = new int8_t[iSize];
            memset(m_pEnableArray[i], 0, iSize);
        }
        m_iStatus = INITED;

        return 0;
    }


    SessionHooks(const SessionHooks &rhs);
    void operator=(const SessionHooks &rhs);
public:
    //with the globalHooks for determine the base and size
    SessionHooks() : m_iStatus(UNINIT)  {}

    ~SessionHooks()
    {
        if (m_iStatus != UNINIT)
        {
            for (int i = 0; i < S; ++i)
                delete []m_pEnableArray[i];
        }
    }


    void disableAll()
    {
        int iLevelSize;
        if (m_iStatus > UNINIT)
        {
            for (int i = 0; i < S; ++i)
            {
                iLevelSize = getLevelSize(
                                 LsiApiHooks::getGlobalApiHooks(B + i)->size());
                memset(m_pEnableArray[i], 0, iLevelSize * sizeof(int8_t));
                m_iFlag[i] = 0;
            }
            m_iStatus = INITED;
        }
    }


    void inherit(SessionHooks<B, S> *parentRt, int isGlobal)
    {
        switch (m_iStatus)
        {
        case UNINIT:
            initSessionHooks();
        //No break, follow with the next
        case INITED:
            if (parentRt && !parentRt->isAllDisabled())
                inheritFromParent(parentRt);
            else if (isGlobal)
                inheritFromGlobal();
            else
                disableAll();
            break;
        case HASOWN:
        default:
            break;
        }
    }


    int8_t *getEnableArray(int level)
    {   return m_pEnableArray[level - B]; }


    int setEnable(const lsi_module_t *pModule, int enable,
                  int *aEnableHkpts, int iEnableCount)
    {
        if (m_iStatus < INITED)
            return LS_FAIL;
        int i, iModIdx;
        ModIndex *p;
        lsiapi_hook_t *pHook;

        p = ModIndex::getModIndex(pModule);
        if (p == NULL)
            return LS_FAIL;

        for (i = 0; i < iEnableCount; ++i)
        {
            if ((iModIdx = p->getLevel(aEnableHkpts[i])) == -1)
                return LS_FAIL;
            pHook =
                LsiApiHooks::getGlobalApiHooks(aEnableHkpts[i])->get(iModIdx);
            if (enable)
            {
                m_pEnableArray[aEnableHkpts[i] - B][LSIHOOKS_GETINDEX(iModIdx)]
                |= (1 << LSIHOOKS_GETOFFSET(iModIdx));
                m_iFlag[aEnableHkpts[i] - B] |= (pHook->flag
                                                 | LSI_FLAG_ENABLED);
            }
            else
            {
                m_pEnableArray[aEnableHkpts[i] - B][LSIHOOKS_GETINDEX(iModIdx)]
                &= ~(1 << LSIHOOKS_GETOFFSET(iModIdx));
                updateFlag(aEnableHkpts[i]);
            }
        }
        m_iStatus = HASOWN;
        return LS_OK;
    }


    void setModuleEnable(const lsi_module_t *pModule, int enable)
    {
        int i, levels[S], count = 0;
        ModIndex *pIndex = ModIndex::getModIndex(pModule);
        if (pIndex == NULL)
            return;
        for (i = B; i < B + S; ++i)
        {
            if (pIndex->getLevel(i) != -1)
                levels[count++] = i;
        }
        setEnable(pModule, enable, levels, count);
    }


    void reset()
    {
        if (m_iStatus >= INITED)
            m_iStatus = INITED;
    };


    int getBase()   { return B;  }
    int getSize()   { return S;  }


    short getFlag(int hookLevel)        { return m_iFlag[hookLevel - B];    }
//     void  setFlag( int hookLevel, short f )
//     {   m_iFlag[hookLevel - B] |= f;               }


    int isNotInited() const             {   return (m_iStatus == UNINIT);   }
    int isAllDisabled() const           {   return isNotInited();           }

    int isDisabled(int hookLevel) const
    {
        if (isAllDisabled())
            return 1;
        return ((m_iFlag[hookLevel - B] & LSI_FLAG_ENABLED) == 0);
    }

    int isEnabled(int hookLevel) const  {  return !isDisabled(hookLevel);   }


//     int runCallback( int level, LsiSession *session, void *param1,
//                      int paramLen1, int *param2, int paramLen2) const
//     {
//         return LsiApiHooks::getGlobalApiHooks(level)->runCallback( level,
//                 m_pEnableArray[level - B], session, param1, paramLen1,
//                 param2, paramLen2 );
//     }

    int runCallbackNoParam(int level, LsiSession *session,
                           lsi_module_t *pModule = NULL) const
    {
        return LsiApiHooks::getGlobalApiHooks(level)->runCallbackNoParam(level,
                m_pEnableArray[level - B], session, pModule);
    }

};

class IolinkSessionHooks : public SessionHooks<0, LSI_HKPT_L4_COUNT>
{
    IolinkSessionHooks(const IolinkSessionHooks &rhs);
    IolinkSessionHooks(const SessionHooks<0, LSI_HKPT_L4_COUNT> &rhs);
    void operator=(const IolinkSessionHooks &rhs);
public:
    IolinkSessionHooks()
        : SessionHooks<0, LSI_HKPT_L4_COUNT>()
    {}
    ~IolinkSessionHooks() {}
};

class HttpSessionHooks
    : public SessionHooks<LSI_HKPT_HTTP_BEGIN, LSI_HKPT_HTTP_COUNT>
{
    HttpSessionHooks(const HttpSessionHooks &rhs);
    HttpSessionHooks(const SessionHooks<LSI_HKPT_HTTP_BEGIN,
                     LSI_HKPT_HTTP_COUNT> &rhs);
    void operator=(const HttpSessionHooks &rhs);
public:
    HttpSessionHooks()
        : SessionHooks<LSI_HKPT_HTTP_BEGIN, LSI_HKPT_HTTP_COUNT>()
    {}
    ~HttpSessionHooks() {}
};

class ServerSessionHooks
    : public SessionHooks<LSI_HKPT_MAIN_INITED, LSI_HKPT_SERVER_COUNT>
{
    ServerSessionHooks(const ServerSessionHooks &rhs);
    ServerSessionHooks(const SessionHooks<LSI_HKPT_MAIN_INITED,
                       LSI_HKPT_SERVER_COUNT> &rhs);
    void operator=(const ServerSessionHooks &rhs);
public:
    ServerSessionHooks()
        : SessionHooks<LSI_HKPT_MAIN_INITED, LSI_HKPT_SERVER_COUNT>()
    {}
    ~ServerSessionHooks() {}
};




#endif // LSIAPIHOOKS_H
