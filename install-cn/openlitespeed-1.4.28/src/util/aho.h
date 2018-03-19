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
#ifndef AHO_H
#define AHO_H

#include <lsr/ls_aho.h>

#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <stdlib.h>



#define MAX_STRING_LEN 8192
#define MAX_FIRST_CHARS 256


#ifdef __cplusplus
extern "C"
{
#endif

typedef ls_aho_state_t AhoState;

class Aho : private ls_aho_t
{
private:
    Aho(const Aho &rhs);
    void operator=(const Aho &rhs);
public:
    Aho(int case_insensitive)
    {   ls_aho(this, case_insensitive);    }

    ~Aho()
    {   ls_aho_d(this);  }

    AhoState *getZeroState()
    {   return zero_state;    }

    int addPattern(const char *pattern, size_t size)
    {   return ls_aho_addpattern(this, pattern, size);   }

    int addPatternsFromFile(const char *filename)
    {   return ls_aho_addfromfile(this, filename);    }

    int makeTree()
    {   return ls_aho_maketree(this);   }

    int optimizeTree()
    {   return ls_aho_optimizetree(this);    }

    /* search for matches in an aho corasick tree. */
    unsigned int search(AhoState *start_state, const char *string, size_t size,
                        size_t startpos,
                        size_t *out_start, size_t *out_end, AhoState **out_last_state)
    {
        return ls_aho_search(this, start_state, string, size, startpos,
                             out_start, out_end, out_last_state);
    }
};

#ifdef __cplusplus
}
#endif


#endif
