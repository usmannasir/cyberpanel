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
#ifndef AUTOSTR_H
#define AUTOSTR_H

#include <lsr/ls_str.h>
#include <string.h>

class AutoStr
{
    char *m_pStr;
    AutoStr &operator=(const AutoStr *pStr);

public:
    AutoStr();
    explicit AutoStr(const char *pStr);
    AutoStr(const AutoStr &);
    ~AutoStr();
    AutoStr &operator=(const char *pStr);
    AutoStr &operator=(const AutoStr &rhs)
    {
        setStr(rhs.c_str());
        return *this;
    }

    int          setStr(const char *pStr);
    int          setStr(const char *pStr, int len);
    char        *prealloc(int size);
    char        *buf()                    {   return m_pStr;  }
    const char *c_str()    const         {   return m_pStr;  }
    operator const char *() const         {   return m_pStr;  }

};


class AutoStr2 : private ls_str_t
{
    AutoStr2 &operator=(const AutoStr *pStr);
    AutoStr2 &operator=(const AutoStr2 *pStr);
public:
    AutoStr2()
    {   ls_str_blank(this);    }

    AutoStr2(const AutoStr2 &rhs)
    {   ls_str_copy(this, &rhs); }

    AutoStr2(const char *pStr)
    {   ls_str(this, pStr, strlen(pStr));   }

    AutoStr2(const char *pStr, int len)
    {   ls_str(this, pStr, len);   }

    ~AutoStr2()
    {   ls_str_d(this);  }

    AutoStr2 &operator=(const char *pStr)
    {
        ls_str_dup(this, pStr, strlen(pStr));
        return *this;
    }

    AutoStr2 &operator=(const AutoStr2 &rhs)
    {
        ls_str_dup(this, rhs.c_str(), rhs.len());
        return *this;
    }

    char       *buf()                                {   return ptr;  }
    const char *c_str() const                        {   return ptr;  }
    int         len() const                          {   return ls_str_s::len;   }
    void        setLen(int len)                      {   ls_str_s::len = len;    }

    char   *prealloc(int size)                       {   return ls_str_prealloc(this, size);    }
    void    append(const char *pStr, const int len)  {   ls_str_append(this, pStr, len);  }
    int     setStr(const char *pStr, int len)        {   return ls_str_dup(this, pStr, len);   }
    int     setStr(const char *pStr)
    {
        return ls_str_dup(this, pStr, strlen(pStr));
    }

    //operator const char *() const   {   return m_pStr;  }

};

static inline int operator==(const AutoStr &s1, const char *s2)
{   return ((s1.c_str() == s2) || (s1.c_str() && s2 && !strcmp(s1.c_str(), s2)));    }
static inline int operator==(const char *s1, const AutoStr &s2)
{   return ((s1 == s2.c_str()) || (s1 && s2.c_str() && !strcmp(s1, s2.c_str())));    }
static inline int operator==(const AutoStr2 &s1, const char *s2)
{   return ((s1.c_str() == s2) || (s1.c_str() && s2 && !strcmp(s1.c_str(), s2)));    }
static inline int operator==(const char *s1, const AutoStr2 &s2)
{   return ((s1 == s2.c_str()) || (s1 && s2.c_str() && !strcmp(s1, s2.c_str())));    }

static inline int operator==(const AutoStr &s1, const AutoStr2 &s2)
{   return ((s1.c_str() == s2.c_str()) || (s1.c_str() && s2.c_str() && !strcmp(s1.c_str(), s2.c_str())));    }
static inline int operator==(const AutoStr2 &s1, const AutoStr &s2)
{   return ((s1.c_str() == s2.c_str()) || (s1.c_str() && s2.c_str() && !strcmp(s1.c_str(), s2.c_str())));    }

static inline int operator==(const AutoStr &s1, const AutoStr &s2)
{   return ((s1.c_str() == s2.c_str()) || (s1.c_str() && s2.c_str() && !strcmp(s1.c_str(), s2.c_str())));    }
static inline int operator==(const AutoStr2 &s1, const AutoStr2 &s2)
{   return ((s1.c_str() == s2.c_str()) || (s1.c_str() && s2.c_str() && !strcmp(s1.c_str(), s2.c_str())));    }


#endif


