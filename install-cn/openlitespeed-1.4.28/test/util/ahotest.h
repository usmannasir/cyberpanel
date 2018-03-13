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

#include <sys/types.h>
#include <util/aho.h>

#ifndef AHOTEST_H
#define AHOTEST_H

Aho *getTree(const char *acceptBuf[], int bufCount, int sensitive);

const int iTestOneLen = 86;
const char *pTestOne =
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Quisque sagittis lectus erat.";

//Find first occurrence
const int iAcceptOneLen = 5;
const char *aAcceptOne[] =
{
    "dolof",
    "ultricies",
    "mattis",
    "Quisque",
    "Mauris"
};

//Never find occurrence
const int iAcceptTwoLen = 5;
const char *aAcceptTwo[] =
{
    "stuff",
    "blah",
    "extravagent",
    "excluded",
    "unused"
};

const int iTestTwoLen = 5;
const char *pTestTwo = "apple";

//Length of accept is longer than input
const int iAcceptThreeLen = 4;
const char *aAcceptThree[] =
{
    "alphabet",
    "octangular",
    "western",
    "parabolic"
};

//Input matches all but last character
const int iAcceptFourLen = 5;
const char *aAcceptFour[] =
{
    "appla",
    "applb",
    "applc",
    "appld",
    "apple"
};

const int iTestThreeLen = 21;
const char *pTestThree = "blahabdcdegfghjkstuff";

//Jump branches
const int iAcceptFiveLen = 4;
const char *aAcceptFive[] =
{
    "abcdefg",
    "bdcdefgh",
    "degfghi",
    "egfghjk"
};

const int iTestFourLen = 21;
const char *pTestFour = "APPLESBANANASCHERRIES";

//Case insensitive and sensitive
const int iAcceptSixLen = 2;
const char *aAcceptSix[] =
{
    "bAnAnas",
    "Apples"
};

const int iTestFiveLen = 10;
const char *pTestFive = "aaaaaaaaaa";

//Test null check
const int iAcceptSevenLen = 8;
const char *aAcceptSeven[] =
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

const char *aTestInput[] =
{
    pTestOne,
    pTestOne,
    pTestTwo,
    pTestTwo,
    pTestThree,
    pTestFour,
    pTestFour,
    pTestFive
};
int aTestInputLen[] =
{
    iTestOneLen,
    iTestOneLen,
    iTestTwoLen,
    iTestTwoLen,
    iTestThreeLen,
    iTestFourLen,
    iTestFourLen,
    iTestFiveLen
};
const char **aTestAccept[] =
{
    aAcceptOne,
    aAcceptTwo,
    aAcceptThree,
    aAcceptFour,
    aAcceptFive,
    aAcceptSix,
    aAcceptSix,
    aAcceptSeven
};
int aTestAcceptLen[] =
{
    iAcceptOneLen,
    iAcceptTwoLen,
    iAcceptThreeLen,
    iAcceptFourLen,
    iAcceptFiveLen,
    iAcceptSixLen,
    iAcceptSixLen,
    iAcceptSevenLen
};

size_t aOutStartRes[] =
{
    57,
    (size_t) - 1,
    (size_t) - 1,
    0,
    9,
    (size_t) - 1,
    0,
    (size_t) - 1
};
size_t aOutEndRes[] =
{
    64,
    (size_t) - 1,
    (size_t) - 1,
    5,
    16,
    (size_t) - 1,
    6,
    (size_t) - 1
};
int aSensitive[] =
{
    1,
    1,
    1,
    1,
    1,
    1,
    0,
    1
};

#endif // AHOTEST_H

#endif
