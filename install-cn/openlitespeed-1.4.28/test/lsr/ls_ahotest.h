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

#ifndef LSR_AHOTEST_H
#define LSR_AHOTEST_H

#include <sys/types.h>
#include <lsr/ls_aho.h>




ls_aho_t *ls_aho_initTree(const char *acceptBuf[], int bufCount,
                          int sensitive);

const int ls_aho_TestOneLen = 86;
const char *ls_aho_TestOne =
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Quisque sagittis lectus erat.";

//Find first occurrence
const int ls_aho_AcceptOneLen = 5;
const char *ls_aho_AcceptOne[] =
{
    "dolof",
    "ultricies",
    "mattis",
    "Quisque",
    "Mauris"
};

//Never find occurrence
const int ls_aho_AcceptTwoLen = 5;
const char *ls_aho_AcceptTwo[] =
{
    "stuff",
    "blah",
    "extravagent",
    "excluded",
    "unused"
};

const int ls_aho_TestTwoLen = 5;
const char *ls_aho_TestTwo = "apple";

//Length of accept is longer than input
const int ls_aho_AcceptThreeLen = 4;
const char *ls_aho_AcceptThree[] =
{
    "alphabet",
    "octangular",
    "western",
    "parabolic"
};

//Input matches all but last character
const int ls_aho_AcceptFourLen = 5;
const char *ls_aho_AcceptFour[] =
{
    "appla",
    "applb",
    "applc",
    "appld",
    "apple"
};

const int ls_aho_TestThreeLen = 21;
const char *ls_aho_TestThree = "blahabdcdegfghjkstuff";

//Jump branches
const int ls_aho_AcceptFiveLen = 4;
const char *ls_aho_AcceptFive[] =
{
    "abcdefg",
    "bdcdefgh",
    "degfghi",
    "egfghjk"
};

const int ls_aho_TestFourLen = 21;
const char *ls_aho_TestFour = "APPLESBANANASCHERRIES";

//Case insensitive and sensitive
const int ls_aho_AcceptSixLen = 2;
const char *ls_aho_AcceptSix[] =
{
    "bAnAnas",
    "Apples"
};

const int ls_aho_TestFiveLen = 10;
const char *ls_aho_TestFive = "aaaaaaaaaa";

//Test null check
const int ls_aho_AcceptSevenLen = 8;
const char *ls_aho_AcceptSeven[] =
{
    "webZIP",
    "webCopier",
    "webStripper",
    "siteSnagger",
    "proWebWalker",
    "cheeseBot",
    "breakdown",
    "octangular"
};

//Test pattern shrinking
const int ls_aho_AcceptEightLen = 5;
const char *ls_aho_AcceptEight[] =
{
    "abcdefgh",
    "abcdefg",
    "abcdef",
    "abcde",
    "abcd"
};

const char *ls_aho_TestInput[] =
{
    ls_aho_TestOne,
    ls_aho_TestOne,
    ls_aho_TestTwo,
    ls_aho_TestTwo,
    ls_aho_TestThree,
    ls_aho_TestFour,
    ls_aho_TestFour,
    ls_aho_TestFive,
    ls_aho_TestThree
};
int ls_aho_TestInputLen[] =
{
    ls_aho_TestOneLen,
    ls_aho_TestOneLen,
    ls_aho_TestTwoLen,
    ls_aho_TestTwoLen,
    ls_aho_TestThreeLen,
    ls_aho_TestFourLen,
    ls_aho_TestFourLen,
    ls_aho_TestFiveLen,
    ls_aho_TestThreeLen
};
const char **ls_aho_TestAccept[] =
{
    ls_aho_AcceptOne,
    ls_aho_AcceptTwo,
    ls_aho_AcceptThree,
    ls_aho_AcceptFour,
    ls_aho_AcceptFive,
    ls_aho_AcceptSix,
    ls_aho_AcceptSix,
    ls_aho_AcceptSeven,
    ls_aho_AcceptEight
};
int ls_aho_TestAcceptLen[] =
{
    ls_aho_AcceptOneLen,
    ls_aho_AcceptTwoLen,
    ls_aho_AcceptThreeLen,
    ls_aho_AcceptFourLen,
    ls_aho_AcceptFiveLen,
    ls_aho_AcceptSixLen,
    ls_aho_AcceptSixLen,
    ls_aho_AcceptSevenLen,
    ls_aho_AcceptEightLen
};

size_t ls_aho_OutStartRes[] =
{
    57,
    (size_t) - 1,
    (size_t) - 1,
    0,
    9,
    (size_t) - 1,
    0,
    (size_t) - 1,
    (size_t) - 1
};
size_t ls_aho_OutEndRes[] =
{
    64,
    (size_t) - 1,
    (size_t) - 1,
    5,
    16,
    (size_t) - 1,
    6,
    (size_t) - 1,
    (size_t) - 1
};
int ls_aho_Sensitive[] =
{
    1,
    1,
    1,
    1,
    1,
    1,
    0,
    1,
    1
};

#endif // LSR_AHOTEST_H

#endif
