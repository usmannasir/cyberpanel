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
#ifndef STRINGTOOL_H
#define STRINGTOOL_H


#include <lsr/ls_strtool.h>

#include <stddef.h>
#include <sys/types.h>


class StrParse : private ls_parse_t
{
public:
    StrParse(const char *pBegin, const char *pEnd, const char *delim)
    {   ls_parse(this, pBegin, pEnd, delim);   }
    ~StrParse()
    {   ls_parse_d(this);   }

    int isEnd() const               {   return pend <= pbegin;   }
    const char *getStrEnd() const  {   return pstrend;   }

    const char *parse()
    {   return ls_parse_parse(this);   }

    const char *trim_parse()
    {   return ls_parse_trimparse(this);   }
};

class StringList;
class AutoStr2;

class StringTool
{
    StringTool() {}
    ~StringTool() {}
public:
    static const char s_aHex[17];
    static inline char getHex(char x)
    {   return s_aHex[ x & 0xf ];    }
    static char *strUpper(const char *pSrc, char *pDest)
    {   return ls_strupper(pSrc, pDest);   }
    static char *strUpper(const char *pSrc, char *pDest, int &n)
    {   return ls_strnupper(pSrc, pDest, &n);   }
    static char *strLower(const char *pSrc, char *pDest)
    {   return ls_strlower(pSrc, pDest);   }
    static char *strLower(const char *pSrc, char *pDest, int &n)
    {   return ls_strnlower(pSrc, pDest, &n);   }
    static char *strTrim(char *p)
    {   return ls_strtrim(p);   }
    static int    strTrim(const char *&pBegin, const char *&pEnd)
    {   return ls_strtrim2(&pBegin, &pEnd);   }
    static int    hexEncode(const char *pSrc, int len, char *pDest)
    {   return ls_hexencode(pSrc, len, pDest);   }
    static int    hexDecode(const char *pSrc, int len, char *pDest)
    {   return ls_hexdecode(pSrc, len, pDest);   }
    static int    strMatch(const char *pSrc, const char *pEnd,
                           AutoStr2 *const *begin, AutoStr2 *const *end, int case_sens)
    {
        return ls_strmatch(pSrc, pEnd,
                           (ls_str_t *const *)begin, (ls_str_t *const *)end, case_sens);
    }
    static StringList *parseMatchPattern(const char *pPattern);
    static const char *strNextArg(const char *&s, const char *pDelim = NULL)
    {   return ls_strnextarg(&s, pDelim);   }
    static char *strNextArg(char *&s, const char *pDelim = NULL)
    {   return (char *)ls_strnextarg((const char **)&s, pDelim);   }
    static const char *getLine(const char *pBegin, const char *pEnd)
    {   return ls_getline(pBegin, pEnd);   }
    static int    parseNextArg(const char *&pRuleStr, const char *pEnd,
                               const char *&argBegin, const char *&argEnd, const char *&pError)
    {   return ls_parsenextarg(&pRuleStr, pEnd, &argBegin, &argEnd, &pError);   }
    static char *convertMatchToReg(char *pStr, char *pBufEnd)
    {   return ls_convertmatchtoreg(pStr, pBufEnd);   }
    static const char *findCloseBracket(const char *pBegin, const char *pEnd,
                                        char chOpen, char chClose)
    {   return ls_findclosebracket(pBegin, pEnd, chOpen, chClose);   }
    static const char *findCharInBracket(const char *pBegin, const char *pEnd,
                                         char searched, char chOpen, char chClose)
    {   return ls_findcharinbracket(pBegin, pEnd, searched, chOpen, chClose);   }
    static int offsetToStr(char *pBuf, int len, off_t val)
    {   return ls_offset2string(pBuf, len, val);   }
    static int unescapeQuote(char *pBegin, char *pEnd, int ch)
    {   return ls_unescapequote(pBegin, pEnd, ch);   }
    static const char *lookupSubString(const char *pInput, const char *pEnd,
                                       const char *key, int keyLen, int *retLen, char sep, char comp)
    {   return ls_lookupsubstring(pInput, pEnd, key, keyLen, retLen, sep, comp);   }
    static const char *mempbrk(const char *pInput, int iSize,
                               const char *accept, int acceptLen)
    {   return ls_mempbrk(pInput, iSize, accept, acceptLen);   }
    static size_t memspn(const char *pInput, int iSize, const char *accept,
                         int acceptLen)
    {   return ls_memspn(pInput, iSize, accept, acceptLen);   }
    static size_t memcspn(const char *pInput, int iSize, const char *accept,
                          int acceptLen)
    {   return ls_memcspn(pInput, iSize, accept, acceptLen);   }

    static void *memmem(const char *haystack, size_t haystacklen,
                        const char *needle, size_t needleLength);

    static void getMd5(const char *src, int len, unsigned char *dstBin)
    {   return ls_getmd5(src, len, dstBin);   }

private:
    static const int NUM_CHAR = 256;
};

#endif
