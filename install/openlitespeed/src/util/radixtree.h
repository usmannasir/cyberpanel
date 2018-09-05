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
#ifndef STRINGTREE_H
#define STRINGTREE_H

#include <lsr/ls_str.h>
#include <lsr/ls_xpool.h>


#define RTMODE_CONTIGUOUS 0
#define RTMODE_POINTER    1

#define RTFLAG_NOCONTEXT  (1 << 1)
#define RTFLAG_GLOBALPOOL (1 << 2)
#define RTFLAG_BESTMATCH  (1 << 3)
#define RTFLAG_UPDATE     (1 << 4)
#define RTFLAG_CICMP      (1 << 5)
#define RTFLAG_WILDCARD   (1 << 6) // When inserting, may have wildcards.
#define RTFLAG_MERGE      (1 << 7) // When inserting, merge similar

typedef struct rnheader_s rnheader_t;
typedef struct rnprint_s rnprint_t;
typedef struct rnwchelp_s rnwchelp_t;
class GHash;

//NOTICE: Should this pass in the key as well?
// Should return 0 for success.
typedef int (*rn_foreach)(void *pObj, const char *pKey, int iKeyLen);
typedef int (*rn_foreach2)(void *pObj, void *pUData, const char *pKey,
                           int iKeyLen);

typedef struct rnwc_s
{
    int m_iNumWild;
    int m_iState;
    union
    {
        rnheader_t  *m_pC;
        rnheader_t **m_pP;
    };
} rnwc_t;


class RadixNode
{
public:
    ~RadixNode()
    {
        ls_str_set(&m_label, NULL, 0);
    }

    int hasChildren()
    {
        if (m_iNumExact > 0)
            return 1;
        else if (m_pWC != NULL && m_pWC->m_iNumWild > 0)
            return 1;
        return 0;
    }

    int getNumChildren()
    {
        int iWild = 0;
        if (m_pWC != NULL)
            iWild = m_pWC->m_iNumWild;
        return m_iNumExact + iWild;
    }
    int getNumExact()               {   return m_iNumExact;                 }
    void incrNumExact()             {   ++m_iNumExact;                      }
    int getNumWild()
    {
        if (m_pWC == NULL)
            return 0;
        return m_pWC->m_iNumWild;
    }
    void incrNumWild()
    {
        if (m_pWC != NULL)
            ++m_pWC->m_iNumWild;
    }

    RadixNode *getParent() const    {   return m_pParent;                   }
    void setParent(RadixNode *p)    {   m_pParent = p;                      }

    ls_str_t *getLabel()            {   return &m_label;                    }
    void setLabel(char *pLabel, int iLabelLen)
    {   ls_str_set(&m_label, pLabel, iLabelLen);    }

    void *getObj()
    {   return (m_iOrig == 0 ? *m_pOrig : m_pObj);  }
    void setObj(void *pObj)
    {
        m_pObj = pObj;
        if (m_iOrig == 0)
            m_iOrig = 1;
    }
    void *getParentObj();


    // NOTICE: iFlags should be an |= of any flags needed, listed above.
    RadixNode *insert(ls_xpool_t *pool, const char *pLabel, int iLabelLen,
                      void *pObj, int iFlags = 0, int iMode = RTMODE_CONTIGUOUS);
    void *erase(const char *pLabel, int iLabelLen, int iFlags = 0);
    void *update(const char *pLabel, int iLabelLen, void *pObj,
                 int iFlags = 0);
    void *find(const char *pLabel, int iLabelLen, int iFlags = 0);
    void *bestMatch(const char *pLabel, int iLabelLen, int iFlags = 0);
    RadixNode *findChild(const char *pLabel, int iLabelLen, int iFlags = 0);
    int for_each(rn_foreach fun, const char *pKey = NULL, int iKeyLen = 0);
    int for_each2(rn_foreach2 fun, void *pUData, const char *pKey = NULL,
                  int iKeyLen = 0);
    int for_each_child(rn_foreach fun);
    int for_each_child2(rn_foreach2 fun, void *pUData);


    static RadixNode *newBranch(ls_xpool_t *pool, const char *pLabel,
                                int iLabelLen, void *pObj,
                                RadixNode *pParent, RadixNode *&pDest,
                                int iFlags = 0, int iMode = RTMODE_CONTIGUOUS);
    static RadixNode *newNode(ls_xpool_t *pool, RadixNode *pParent,
                              void *pObj);

    void printChildren(rnprint_t *pHelper);

private:

    RadixNode(RadixNode *pParent, void *pObj = NULL);
    RadixNode(const RadixNode &rhs);
    void *operator=(const RadixNode &rhs);

    int getState()                  {   return m_iState;                    }
    void setState(int iState)       {   m_iState = iState;                  }
    int getWCState()                {   return m_pWC->m_iState;             }
    void setWCState(int iState)     {   m_pWC->m_iState = iState;           }

    void **getObjPtr()              {   return &m_pObj;                     }

    int getHeader(int iFlags, ls_xpool_t *pool, const char *pLabel,
                  int iLabelLen, rnheader_t *&pHeader);
    int setHeader(int iFlags, int iMode, ls_xpool_t *pool,
                  rnheader_t *pHeader);
    int getWCHeader(int iFlags, ls_xpool_t *pool, const char *pLabel,
                    int iLabelLen, rnheader_t *&pHeader, rnwchelp_t *pHelp);

    int setWCHeader(int iFlags, int iMode, ls_xpool_t *pool,
                    rnheader_t *pHeader, rnwchelp_t *pHelp);
    void mergeSelf(void **pOrig);
    int merge(ls_xpool_t *pool, const char *pMatch, int iMatchLen,
              int iFlags, int iMode, void **pOrig, rnheader_t *pHeaderAdded);

    RadixNode *searchExact(const char *pLabel, int iLabelLen, int iFlags);

    RadixNode *searchWild(const char *pLabel, int iLabelLen, int iFlags);
    RadixNode *findChildData(const char *pLabel, int iLabelLen,
                             RadixNode *pNode, int iHasChildren, int iFlags);

    static int printHash(const void *key, void *data, void *extra);

    int              m_iNumExact;
    int              m_iState;
    RadixNode       *m_pParent;
    ls_str_t         m_label;
    int              m_iOrig;
    union
    {
        void        *m_pObj;
        void       **m_pOrig;
    };
    union
    {
        rnheader_t  *m_pCHeaders;
        rnheader_t **m_pPHeaders;
        GHash       *m_pHash;
    };
    rnwc_t          *m_pWC;
};

class RadixTree
{
public:

    RadixTree(int iMode = RTMODE_CONTIGUOUS)
        : m_iMode(iMode)
        , m_iFlags(0)
        , m_pRoot(NULL)
    {   m_pool = ls_xpool_new();             }

    ~RadixTree()
    {   ls_xpool_delete(m_pool);          }

    // NOTICE: If any of these are to be used, they should be set immediately.
    int setRootLabel(const char *pLabel, int iLabelLen);
    int getNoContext()              {   return m_iFlags & RTFLAG_NOCONTEXT; }
    void setNoContext();
    int getUseGlobalPool()          {   return m_iFlags & RTFLAG_GLOBALPOOL;}
    void setUseGlobalPool()         {   m_iFlags |= RTFLAG_GLOBALPOOL;      }
    int getCiCmp()                  {   return m_iFlags & RTFLAG_CICMP;     }
    void setCiCmp()                 {   m_iFlags |= RTFLAG_CICMP;           }
    int getUseWildCard()            {   return m_iFlags & RTFLAG_WILDCARD;  }
    void setUseWildCard()           {   m_iFlags |= RTFLAG_WILDCARD;        }
    int getUseMerge()               {   return m_iFlags & RTFLAG_MERGE;     }
    void setUseMerge()              {   m_iFlags |= RTFLAG_MERGE;           }

    RadixNode *insert(const char *pLabel, int iLabelLen, void *pObj);
    void *erase(const char *pLabel, int iLabelLen) const;
    void *update(const char *pLabel, int iLabelLen, void *pObj) const;
    void *find(const char *pLabel, int iLabelLen) const;
    void *bestMatch(const char *pLabel, int iLabelLen) const;

    int for_each(rn_foreach fun);
    int for_each2(rn_foreach2 fun, void *pUData);

    void printTree();

private:
    RadixTree(const RadixTree &rhs);
    void *operator=(const RadixTree &rhs);
    int checkPrefix(const char *pLabel, int iLabelLen) const;


    ls_xpool_t *m_pool;
    int         m_iMode;
    int         m_iFlags;
    rnheader_t *m_pRoot;
};


#endif


