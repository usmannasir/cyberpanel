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

#include <lsr/ls_confparser.h>
#include <lsr/ls_pool.h>
#include <lsr/ls_strtool.h>
#include <stddef.h>
#include <sys/types.h>

typedef void (*skipLeadingFn)(const char **p, const char *pEnd);

static void ls_conf_reset_parser(ls_confparser_t *pThis, int size);
static ls_objarray_t *ls_conf_parse(ls_confparser_t *pThis,
                                    const char *pConf, const char *pConfEnd, skipLeadingFn skipFn);
static const char *ls_get_param(
    const char *pBufBegin, const char *pBufEnd, const char **pParamEnd);
static const char *ls_find_end_quote(
    const char *pBegin, const char *pEnd, char ch);
static void ls_add_to_list(ls_confparser_t *pThis, const char *pBegin,
                           int len);


static inline void skipLeadingDelims(const char **p, const char *pEnd)
{
    while (*p < pEnd && isspace(**p))
        ++(*p);
}


static inline void skipLeadingWhiteSpace(const char **p, const char *pEnd)
{
    char ch;
    while (*p < pEnd && (((ch = **p) == ' ') || (ch == '\t')))
        ++(*p);
}


void ls_confparser(ls_confparser_t *pThis)
{
    ls_objarray_init(&pThis->plist, sizeof(ls_str_t));
    ls_objarray_setcapacity(&pThis->plist, NULL, 5);
    ls_str(&pThis->pstr, NULL, 0);
}


void ls_confparser_d(ls_confparser_t *pThis)
{
    ls_objarray_release(&pThis->plist, NULL);
    ls_str_d(&pThis->pstr);
}


inline ls_objarray_t *ls_confparser_line(
    ls_confparser_t *pThis, const char *pLine, const char *pLineEnd)
{
    return ls_conf_parse(pThis, pLine, pLineEnd, skipLeadingWhiteSpace);
}


ls_objarray_t *ls_confparser_linekv(
    ls_confparser_t *pThis, const char *pLine, const char *pLineEnd)
{
    const char *pParam;
    const char *pParamEnd;

    ls_strtrim2(&pLine, &pLineEnd);
    if (pLine >= pLineEnd)
        return NULL;

    ls_conf_reset_parser(pThis, pLineEnd - pLine + 1);

    pParam = ls_get_param(pLine, pLineEnd, &pParamEnd);
    ls_add_to_list(pThis, pParam, pParamEnd - pParam);

    pParam = pParamEnd + 1;
    skipLeadingWhiteSpace(&pParam, pLineEnd);

    if (pParam >= pLineEnd)
        pParam = NULL;
    else if ((*pParam == *(pLineEnd - 1))
             && (*pParam == '\"' || *pParam == '\''))
    {
        pParamEnd = ls_find_end_quote(pParam + 1, pLineEnd, *pParam);
        if (pParamEnd == pLineEnd - 1)
        {
            ++pParam;
            --pLineEnd;
        }
    }

    ls_add_to_list(pThis, pParam, pLineEnd - pParam);
    return &pThis->plist;
}


inline ls_objarray_t *ls_confparser_multi(
    ls_confparser_t *pThis, const char *pBlock, const char *pBlockEnd)
{
    return ls_conf_parse(pThis, pBlock, pBlockEnd, skipLeadingDelims);
}


static ls_objarray_t *ls_conf_parse(ls_confparser_t *pThis,
                                    const char *pConf, const char *pConfEnd, skipLeadingFn skipFn)
{
    ls_strtrim2(&pConf, &pConfEnd);
    if (pConf >= pConfEnd)
        return NULL;

    ls_conf_reset_parser(pThis, pConfEnd - pConf + 1);

    while (pConf < pConfEnd)
    {
        const char *pParam;
        const char *pParamEnd;

        skipFn(&pConf, pConfEnd);
        if ((pParam = ls_get_param(pConf, pConfEnd, &pParamEnd)) == NULL)
            return &pThis->plist;

#ifdef LSR_CONFPARSERDEBUG
        printf("CONFPARSELINE: New Parameter: %.*s\n",
               pParamEnd - pParam, pParam);
#endif

        ls_add_to_list(pThis, pParam, pParamEnd - pParam);
        pConf = pParamEnd + 1;
    }
    return &pThis->plist;
}


static void ls_conf_reset_parser(ls_confparser_t *pThis, int size)
{
    ls_str_prealloc(&pThis->pstr, size);
    ls_str_setlen(&pThis->pstr, 0);
    ls_objarray_clear(&pThis->plist);
}


static const char *ls_get_param(
    const char *pBufBegin, const char *pBufEnd, const char **pParamEnd)
{
    switch (*pBufBegin)
    {
    case '\"':
    case '\'':
        *pParamEnd = ls_find_end_quote(pBufBegin + 1, pBufEnd, *pBufBegin);
        ++pBufBegin;
        break;
    case '\r':
    case '\n':
        // This should only be an option for parse_line,
        //   in which case we should call this no param.
        return NULL;
    default:
        *pParamEnd = ls_strnextarg(&pBufBegin, NULL);
        break;
    }
    if (*pParamEnd == NULL)
    {
        *pParamEnd = pBufEnd;
        while (isspace((*pParamEnd)[-1]))
            --(*pParamEnd);
    }
    return pBufBegin;
}


static const char *ls_find_end_quote(
    const char *pBegin, const char *pEnd, char ch)
{
    const char *p = memchr(pBegin, ch, pEnd - pBegin);
    if (p == NULL)
        return NULL;
    while ((p != NULL) && (p < pEnd) && *(p - 1) == '\\')
    {
        ++p;
        p = memchr(p, ch, pEnd - p);
    }
    return p;
}


static void ls_add_to_list(ls_confparser_t *pThis, const char *pBegin,
                           int len)
{
    ls_str_t *p;
    char *pBuf = NULL;

    if (ls_objarray_getsize(&pThis->plist) >=
        ls_objarray_getcapacity(&pThis->plist))
    {
        ls_objarray_guarantee(&pThis->plist,
                              NULL, ls_objarray_getcapacity(&pThis->plist) + 10);
    }
    p = ls_objarray_getnew(&pThis->plist);

    if (pBegin != NULL)
    {
        pBuf = ls_str_buf(&pThis->pstr) + ls_str_len(&pThis->pstr);

        memmove(pBuf, pBegin, len);
        *(pBuf + len) = '\0';
        ls_str_setlen(&pThis->pstr, ls_str_len(&pThis->pstr) + len + 1);
    }
    else
        len = 0;

    ls_str_set(p, pBuf, len);
}


