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
#ifndef PCREGEX_H
#define PCREGEX_H


#include <lsdef.h>
#include <lsr/ls_pcreg.h>
#include <pcre.h>

//#define _USE_PCRE_JIT_


class RegexResult : private ls_pcreres_t
{
public:
    RegexResult()
    {   ls_pcre_result(this);   }

    ~RegexResult()
    {   ls_pcreres_d(this);     }

    void setBuf(const char *pBuf)   {   pbuf = pBuf;          }

    void setMatches(int iMatches)   {   matches = iMatches;    }

    int getSubstr(int i, char *&pValue) const
    {   return ls_pcreres_getsubstr(this, i, &pValue);    }

    int *getVector()                {   return ovector;       }

    int  getMatches() const         {   return matches;       }


    LS_NO_COPY_ASSIGN(RegexResult);
};

class Pcregex : private ls_pcre_t      //pcreapi
{
public:
    Pcregex()
    {   ls_pcre(this);   }

    ~Pcregex()
    {   ls_pcre_d(this); }

#ifdef _USE_PCRE_JIT_
#if !defined(__sparc__) && !defined(__sparc64__)
    static void initJitStack();
    static pcre_jit_stack *getJitStack();
    static void releaseJitStack(void *pValue);
#endif
#endif
    int  compile(const char *regex, int options, int matchLimit = 0,
                 int recursionLimit = 0)
    {
        return ls_pcre_compile(this, regex, options, matchLimit, recursionLimit);
    }

    int  exec(const char *subject, int length, int startoffset,
              int options, int *ovector, int ovecsize) const
    {
#ifdef _USE_PCRE_JIT_
#if !defined(__sparc__) && !defined(__sparc64__)
        pcre_jit_stack *stack = getJitStack();
        pcre_assign_jit_stack(m_extra, NULL, stack);
#endif
#endif
        return pcre_exec(regex, extra, subject, length, startoffset,
                         options, ovector, ovecsize);
    }

    int  exec(const char *subject, int length, int startoffset,
              int options, RegexResult *pRes) const
    {
        pRes->setMatches(pcre_exec(regex, extra, subject, length, startoffset,
                                   options, pRes->getVector(), 30));
        return pRes->getMatches();
    }

    void release()              {   ls_pcre_release(this);   }

    int  getSubStrCount() const  {   return substr;   }



    LS_NO_COPY_ASSIGN(Pcregex);
};

class RegSub : private ls_pcresub_t
{
    void operator=(const RegSub &rhs);
public:
    RegSub()
    {   ls_pcre_sub(this);   }

    RegSub(const RegSub &rhs)
    {   ls_pcresub_copy(this, &rhs); }

    ~RegSub()
    {   ls_pcresub_d(this); }

    void release()
    {   ls_pcresub_release(this);   }

    int compile(const char *input)
    {   return ls_pcresub_compile(this, input); }

    int exec(const char *input, const int *ovector, int ovec_num,
             char *output, int &length)
    {
        return ls_pcresub_exec(this, input, ovector, ovec_num,
                               output, &length);
    }
};
#endif






