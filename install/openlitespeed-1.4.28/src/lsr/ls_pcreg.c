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

#include <lsdef.h>
#include <lsr/ls_hash.h>
#include <lsr/ls_lock.h>
#include <lsr/ls_pcreg.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_str.h>
#include <assert.h>
#include <ctype.h>
#include <string.h>
#include <pthread.h>

#ifndef PCRE_STUDY_JIT_COMPILE
#define PCRE_STUDY_JIT_COMPILE 0
#endif

#ifdef USE_THRSAFE_POOL
static ls_atom_spinlock_t s_store_lock = 0;
#endif
static ls_hash_t *s_pcre_store = NULL;


ls_pcre_t *ls_pcre_new()
{
    ls_pcre_t *pThis = (ls_pcre_t *)ls_palloc(sizeof(ls_pcre_t));
    return ls_pcre(pThis);
}


ls_pcre_t *ls_pcre(ls_pcre_t *pThis)
{
    if (pThis == NULL)
        return NULL;
    pThis->regex = NULL;
    pThis->extra = NULL;
    pThis->substr = 0;
    pThis->pattern = NULL;
    return pThis;
}


void ls_pcre_d(ls_pcre_t *pThis)
{
    ls_pcre_release(pThis);
    pThis->substr = 0;
    if (pThis->pattern != NULL)
        ls_pfree(pThis->pattern);
}


void ls_pcre_delete(ls_pcre_t *pThis)
{
    ls_pcre_d(pThis);
    ls_pfree(pThis);
}


ls_pcre_t *ls_pcre_load(const char *pRegex, unsigned long iFlags)
{
    ls_hash_iter pNode;
    ls_hash_t *pInnerHash = NULL;
    ls_pcre_t *pcre = NULL;

#ifdef USE_THRSAFE_POOL
    ls_atomic_spin_lock(&s_store_lock);
#endif
    /** Check for:
     * 1. Existance of hash table
     * 2. Existance of inner hash table with given flags.
     * 3. Able to get inner table from node.
     * 4. Existance of pcre structure with given regex.
     * NOTICE: pNode is used for multiple nodes.
     */
    if ((s_pcre_store != NULL)
        && ((pNode = ls_hash_find(s_pcre_store, (void *)iFlags)) != NULL)
        && ((pInnerHash = (ls_hash_t *)ls_hash_getdata(pNode)) != NULL)
        && ((pNode = ls_hash_find(pInnerHash, pRegex)) != NULL))
    {
        pcre = (ls_pcre_t *)ls_hash_getdata(pNode);
        ls_hash_erase(pInnerHash, pNode);
    }
#ifdef USE_THRSAFE_POOL
    ls_atomic_spin_unlock(&s_store_lock);
#endif
    return pcre;
}


int ls_pcre_store(ls_pcre_t *pThis, unsigned long iFlags)
{
    ls_hash_iter pNode;
    ls_hash_t *pInnerHash = NULL;

#ifdef USE_THRSAFE_POOL
    ls_atomic_spin_lock(&s_store_lock);
#endif
    if (s_pcre_store == NULL)
        s_pcre_store = ls_hash_new(50, NULL, NULL, NULL);
    else if ((pNode = ls_hash_find(s_pcre_store,
                                   (void *)iFlags)) != NULL)
        pInnerHash = (ls_hash_t *)ls_hash_getdata(pNode);

    if (pInnerHash == NULL)
    {
        pInnerHash = ls_hash_new(10, ls_hash_hfstring,
                                 ls_hash_cmpstring, NULL);
        ls_hash_insert(s_pcre_store, (void *)iFlags, pInnerHash);
    }
    int ret = (ls_hash_insert(pInnerHash, pThis->pattern, pThis) != NULL);
#ifdef USE_THRSAFE_POOL
    ls_atomic_spin_unlock(&s_store_lock);
#endif
    return ret;
}


ls_pcreres_t *ls_pcre_result(ls_pcreres_t *pThis)
{
    if (pThis == NULL)
        return NULL;
    pThis->pbuf = NULL;
    pThis->matches = 0;
    return pThis;
}


ls_pcresub_t *ls_pcre_sub(ls_pcresub_t *pThis)
{
    if (pThis == NULL)
        return NULL;
    pThis->parsed = NULL;
    pThis->plist = NULL;
    pThis->plistend = NULL;
    return pThis;
}


ls_pcreres_t *ls_pcreres_new()
{
    ls_pcreres_t *pThis = (ls_pcreres_t *)ls_palloc(sizeof(ls_pcreres_t));
    return ls_pcre_result(pThis);
}


void ls_pcreres_d(ls_pcreres_t *pThis)
{
    memset(pThis, 0, sizeof(ls_pcreres_t));
    //Since I did not allocate the buffer, I will not deallocate the buffer.
    pThis->pbuf = NULL;
}


void ls_pcreres_delete(ls_pcreres_t *pThis)
{
    ls_pcreres_d(pThis);
    ls_pfree(pThis);
}


ls_pcresub_t *ls_pcresub_new()
{
    ls_pcresub_t *pThis = (ls_pcresub_t *)ls_palloc(sizeof(ls_pcresub_t));
    return ls_pcre_sub(pThis);
}


ls_pcresub_t *ls_pcresub_copy(ls_pcresub_t *dest, const ls_pcresub_t *src)
{
    assert(dest && src);
    char *p = ls_pdupstr2(src->parsed, (char *)src->plistend - src->parsed);
    if (p == NULL)
        return NULL;
    dest->parsed = p;
    dest->plist = (ls_pcresubent_t *)(p + ((char *)src->plist - src->parsed));
    dest->plistend = dest->plist + (src->plistend - src->plist);

    return dest;
}


void ls_pcresub_d(ls_pcresub_t *pThis)
{
    ls_pfree(pThis->parsed);
    pThis->plist = NULL;
    pThis->plistend = NULL;
}


void ls_pcresub_delete(ls_pcresub_t *pThis)
{
    ls_pcresub_d(pThis);
    ls_pfree(pThis);
}


int ls_pcreres_getsubstr(const ls_pcreres_t *pThis, int i, char **pValue)
{
    assert(pValue);
    if (i < pThis->matches)
    {
        const int *pParam = &pThis->ovector[ i << 1 ];
        *pValue = (char *)pThis->pbuf + *pParam;
        return *(pParam + 1) - *pParam;
    }
    return 0;
}


#ifndef PCRE_STUDY_JIT_COMPILE
#define PCRE_STUDY_JIT_COMPILE 0
#endif

#ifdef _USE_PCRE_JIT_
#if !defined(__sparc__) && !defined(__sparc64__)
static int s_jit_key_inited = 0;
static pthread_key_t s_jit_stack_key;


void ls_pcre_init_jit_stack()
{
    s_jit_key_inited = 1;
    pthread_key_create(&s_jit_stack_key, ls_pcre_release_jit_stack);
}


void ls_pcre_release_jit_stack(void *pValue)
{
    pcre_jit_stack_free((pcre_jit_stack *) pValue);
}


pcre_jit_stack *ls_pcre_get_jit_stack()
{
    pcre_jit_stack *jit_stack;

    if (s_jit_key_inited == 0)
        ls_pcre_init_jit_stack();
    jit_stack = (pcre_jit_stack *)pthread_getspecific(s_jit_stack_key);
    if (jit_stack == NULL)
    {
        jit_stack = (pcre_jit_stack *)pcre_jit_stack_alloc(32 * 1024, 512 * 1024);
        pthread_setspecific(s_jit_stack_key, jit_stack);
    }
    return jit_stack;
}
#endif
#endif


int ls_pcre_parseoptions(const char *pOptions, size_t iOptLen,
                         unsigned long *pFlags)
{
    int iOptimizeFlags = 0;
    const char *pEnd = pOptions + iOptLen;
    const char *p = pOptions;

    if (pFlags == NULL)
        return LS_FAIL;
    *pFlags = 0;

    while (p < pEnd)
    {
        switch (*p)
        {
        case 'a':
            *pFlags |= PCRE_ANCHORED;
            break;
        case 'd':
            iOptimizeFlags |= LSR_PCRE_DFA_MODE;
            break;
        case 'i':
            *pFlags |= PCRE_CASELESS;
            break;
        case 'j': //Jit mode automatically used when available.
            break;
        case 'm':
            *pFlags |= PCRE_MULTILINE;
            break;
        case 'o':
            iOptimizeFlags |= LSR_PCRE_CACHE_COMPILED;
            break;
        case 's':
            *pFlags |= PCRE_DOTALL;
            break;
        case 'u':
            *pFlags |= PCRE_UTF8;
            break;
        case 'U':
            *pFlags |= (PCRE_UTF8 | PCRE_NO_UTF8_CHECK) ;
            break;
        case 'x':
            *pFlags |= PCRE_EXTENDED;
            break;
#if PCRE_MAJOR > 8 || ( PCRE_MAJOR == 8 && PCRE_MINOR >= 12 )
        case 'D':
            *pFlags |= PCRE_DUPNAMES;
            break;
        case 'J':
            *pFlags |= PCRE_JAVASCRIPT_COMPAT;
            break;
#endif
        default:
            return LS_FAIL;
        }
        ++p;
    }
    return iOptimizeFlags;
}


int ls_pcre_compile(ls_pcre_t *pThis, const char *regex, int options,
                    int matchLimit, int recursionLimit)
{
    const char *error;
    int          erroffset;
    if (pThis->regex != NULL)
        ls_pcre_release(pThis);
    pThis->regex = pcre_compile(regex, options, &error, &erroffset, NULL);
    if (pThis->regex == NULL)
        return LS_FAIL;
    pThis->pattern = ls_pdupstr(regex);
    pThis->extra = pcre_study(pThis->regex,
#if defined( _USE_PCRE_JIT_)&&!defined(__sparc__) && !defined(__sparc64__) && defined( PCRE_CONFIG_JIT )
                              PCRE_STUDY_JIT_COMPILE,
#else
                              0,
#endif
                              & error);
    if (matchLimit > 0)
    {
        pThis->extra->match_limit = matchLimit;
        pThis->extra->flags |= PCRE_EXTRA_MATCH_LIMIT;
    }
    if (recursionLimit > 0)
    {
        pThis->extra->match_limit_recursion = recursionLimit;
        pThis->extra->flags |= PCRE_EXTRA_MATCH_LIMIT_RECURSION;
    }
    pcre_fullinfo(pThis->regex, pThis->extra,
                  PCRE_INFO_CAPTURECOUNT, &(pThis->substr));
    ++(pThis->substr);
    return LS_OK;
}


void ls_pcre_release(ls_pcre_t *pThis)
{
    if (pThis->regex != NULL)
    {
        if (pThis->extra != NULL)
        {
#if defined( _USE_PCRE_JIT_)&&!defined(__sparc__) && !defined(__sparc64__) && defined( PCRE_CONFIG_JIT )
            pcre_free_study(pThis->m_extra);
#else
            pcre_free(pThis->extra);
#endif
            pThis->extra = NULL;
        }
        pcre_free(pThis->regex);
        pThis->regex = NULL;
    }
}


int ls_pcre_getnamedsubcnt(ls_pcre_t *pThis)
{
    int iCount;
    if (pcre_fullinfo(pThis->regex, NULL, PCRE_INFO_NAMECOUNT, &iCount) != 0)
        return LS_FAIL;
    return iCount;
}


static int ls_pcre_map_name(unsigned char *pEntry, char **pName)
{
    assert(pName);
    unsigned char iMostSig = pEntry[0], //Most significant byte
                  iLeastSig = pEntry[1]; //Least significant byte
    *pName = (char *)&pEntry[2];
    return ((iMostSig << 8) | iLeastSig);   //Combine bytes for number.
}


int ls_pcre_getnamedsubs(const ls_pcre_t *pThis, const ls_pcreres_t *pRes,
                         ls_strpair_t *pSubPats, int iCount)
{
    int i, iEntryLen, iSubLen;
    unsigned char *pNames;
    char *pName, *pSubStr = NULL;

    if (pcre_fullinfo(
            pThis->regex, NULL, PCRE_INFO_NAMEENTRYSIZE, &iEntryLen) != 0)
        return LS_FAIL;
    if (pcre_fullinfo(
            pThis->regex, NULL, PCRE_INFO_NAMETABLE, &pNames) != 0)
        return LS_FAIL;

    for (i = 0; i < iCount; ++i)
    {
        unsigned char *pCurEntry = pNames + (i * iEntryLen);
        iSubLen = ls_pcreres_getsubstr(pRes,
                                       ls_pcre_map_name(pCurEntry, &pName),
                                       &pSubStr);
        ls_str_set(&pSubPats[i].key, pName, strlen(pName));
        ls_str_set(&pSubPats[i].val, pSubStr, iSubLen);
    }

    return i;
}


void ls_pcresub_release(ls_pcresub_t *pThis)
{
    if (pThis->parsed != NULL)
        ls_pfree(pThis->parsed);
    pThis->parsed = NULL;
    pThis->plist = NULL;
    pThis->plistend = NULL;
}


int ls_pcresub_compile(ls_pcresub_t *pThis, const char *rule)
{
    if (rule == NULL)
        return LS_FAIL;
    const char     *p = rule;
    char   c;
    int             entries = 0;
    while ((c = *p++) != '\0')
    {
        if (c == '&')
            ++entries;
        else if (c == '$' && isdigit(*p))
        {
            ++p;
            ++entries;
        }
        else if (c == '\\' && (*p == '$' || *p == '&'))
            ++p;
    }
    ++entries;
    int bufSize = strlen(rule) + 1;
    bufSize = ((bufSize + 7) >> 3) << 3;
    if ((pThis->parsed = ls_prealloc(
                             pThis->parsed, bufSize + entries * sizeof(ls_pcresubent_t))) == NULL)
        return LS_FAIL;
    pThis->plist = (ls_pcresubent_t *)(pThis->parsed + bufSize);
    memset(pThis->plist, 0xff, entries * sizeof(ls_pcresubent_t));

    char *pDest = pThis->parsed;
    p = rule;
    ls_pcresubent_t *pEntry = pThis->plist;
    pEntry->strbegin = 0;
    pEntry->strlen = 0;
    while ((c = *p++) != '\0')
    {
        if (c == '&')
            pEntry->param = 0;
        else if (c == '$' && isdigit(*p))
            pEntry->param = *p++ - '0';
        else
        {
            if (c == '\\' && (*p == '$' || *p == '&'))
                c = *p++;
            *pDest++ = c;
            ++(pEntry->strlen);
            continue;
        }
        ++pEntry;
        pEntry->strbegin = pDest - pThis->parsed;
        pEntry->strlen = 0;
    }
    *pDest = 0;
    if (pEntry->strlen == 0)
        --entries;
    else
        ++pEntry;
    pThis->plistend = pEntry;
    assert(pEntry - pThis->plist == entries);
    return LS_OK;
}


int ls_pcresub_exec(ls_pcresub_t *pThis, const char *input,
                    const int *ovector, int ovec_num, char *output, int *length)
{

    ls_pcresubent_t *pEntry = pThis->plist;
    char *p = output;
    assert(length);
    char *pBufEnd = output + *length;
    while (pEntry < pThis->plistend)
    {
        if (pEntry->strlen > 0)
        {
            if (p + pEntry->strlen < pBufEnd)
                memmove(p, pThis->parsed + pEntry->strbegin, pEntry->strlen);
            p += pEntry->strlen;
        }
        if ((pEntry->param >= 0) && (pEntry->param < ovec_num))
        {
            const int *pParam = ovector + (pEntry->param << 1);
            int len = *(pParam + 1) - *pParam;
            if (len > 0)
            {
                if (p + len < pBufEnd)
                    memmove(p, input + *pParam , len);
                p += len;
            }
        }
        ++pEntry;
    }
    if (p < pBufEnd)
        *p = '\0';
    *length = p - output;
    return (p < pBufEnd) ? LS_OK : LS_FAIL;
}


int ls_pcresub_getlen(ls_pcresub_t *pThis, const char *input,
                      const int *ovector, int ovec_num)
{

    ls_pcresubent_t *pEntry = pThis->plist;
    int iLen = 0;
    while (pEntry < pThis->plistend)
    {
        if (pEntry->strlen > 0)
            iLen += pEntry->strlen;
        if ((pEntry->param >= 0) && (pEntry->param < ovec_num))
        {
            const int *pParam = ovector + (pEntry->param << 1);
            int len = *(pParam + 1) - *pParam;
            if (len > 0)
                iLen += len;
        }
        ++pEntry;
    }
    ++iLen;
    return iLen;
}

