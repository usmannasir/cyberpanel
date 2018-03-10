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
#ifdef RUN_TEST

#ifndef STRINGTOOLTEST_H
#define STRINGTOOLTEST_H

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

static const char *pMemspnInput = "abcdefghijklmnopqrstuvwxyz";
static const char *pMemspnAccept = "123abcdefghijklmnopqrstuvwxyz";

static const int aMemspnInputSize[] =
{
    0,
    26,
    26,
    26,
    26,
    26
};
static const int aMemspnAcceptSize[] =
{
    12,
    0,
    12,
    6,
    29,
    3
};
static const size_t aMemspnOutput[] =
{
    0,
    0,
    9,
    3,
    26,
    0
};

static const size_t aMemCspnOutput[] =
{
    0,
    26,
    0,
    0,
    0,
    26
};

/******** Look up Substring Testing Dictionary ********/
/* Check List:
* 1. Check if it finds key, value goes to the end.
* 2. Check if it handles key not found
* 3. Check when key is in the middle of buffer, space before comparator
* 4. Same as 3 except + space after comparator and before seperator as well.
* 5. Same as 3 except + multiple spaces after comparator
* 6. Multiple spaces in middle of value
* 7. Alphanumeric seperators
* 8. Alphanumeric comparators
* 9. Empty value
* 10. No Value and No Comparator
* 11. Target is substring of a key, target doesn't exist.
* 12. Multiple spaces in front of buffer, at end of buffer, in front of value, at end of value
* 13. Check single key
* 14. Check multiple keys, target included
* 15. Check multiple keys, target excluded
* 16. Check Multiple Keys, empty target
* 17. Check quotes
* 18. Check single quotes
* 19. Check dangling quotes
* 20. Check spaces everywhere
*/

static const char *aLUSSInputs[] =
{
    "key=value",
    "key=value",
    "key=value; first=alpha; second =beta; third= delta; fourth=epsilon",
    "key=value; first=alpha; second = beta    ; third= delta; fourth=epsilon",
    "key=value; first=alpha; second =     beta; third= delta; fourth=epsilon",
    "key=val     ue",
    "key=valuez first=alphaz second = betaz third= deltaz fourth=epsilon",
    "keydvalue; firstdalpha; second d beta; thirdd delta; fourthdepsilon",
    "key=",
    "key",
    "key=value; first=alpha; second =beta; third= delta; fourth=epsilon",
    "                key=value; first=alpha; second =           beta                ; third= delta; fourth=epsilon       ",
    "key",
    "key, alpha, beta, delta, epsilon",
    "key, alpha, beta, delta, epsilon",
    "key, alpha, beta, delta, epsilon",
    "key=value; first=alpha; second =\"beta\"; third= delta; fourth=epsilon",
    "key=value; first=alpha; second ='beta'; third= delta; fourth=epsilon",
    "key=value; first=alpha; second =\"beta    ",
    "key=value; first=alpha; second =    \"    beta    \"    ; third= delta; fourth=epsilon"
};

static const int aLUSSInputLen[] =
{
    9,
    9,
    66,
    71,
    71,
    14,
    67,
    67,
    4,
    3,
    66,
    116,
    3,
    32,
    32,
    32,
    68,
    68,
    41,
    84
};

static const char *aLUSSKeys[] =
{
    "key",
    "blah",
    "second",
    "second",
    "second",
    "key",
    "second",
    "second",
    "key",
    "key",
    "con",
    "second",
    "key",
    "beta",
    "theta",
    "",
    "second",
    "second",
    "second",
    "second"
};

static const int aLUSSKeyLen[] =
{
    3,
    4,
    6,
    6,
    6,
    3,
    6,
    6,
    3,
    3,
    3,
    6,
    3,
    4,
    5,
    0,
    6,
    6,
    6,
    6
};

static const char aLUSSSep[] =
{
    ';',
    ';',
    ';',
    ';',
    ';',
    ';',
    'z',
    ';',
    ';',
    ';',
    ';',
    ';',
    ';',
    ',',
    ',',
    ',',
    ';',
    ';',
    ';',
    ';'
};

static const char aLUSSComp[] =
{
    '=',
    '=',
    '=',
    '=',
    '=',
    '=',
    '=',
    'd',
    '=',
    '=',
    '=',
    '=',
    '\0',
    '\0',
    '\0',
    '\0',
    '=',
    '=',
    '=',
    '='
};

static const int aLUSSRet[] =
{
    4,
    -1,
    32,
    33,
    37,
    4,
    33,
    33,
    4,
    -1,
    -1,
    59,
    0,
    12,
    -1,
    -1,
    33,
    33,
    33,
    37
};

static const int aLUSSRetLen[] =
{
    5,
    -1,
    4,
    4,
    4,
    10,
    4,
    4,
    0,
    -1,
    -1,
    4,
    -2,
    -2,
    -1,
    -1,
    4,
    4,
    8,
    12
};







#endif

#endif
