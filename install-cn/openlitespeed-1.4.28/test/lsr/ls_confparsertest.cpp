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

#include <lsr/ls_confparser.h>
#include <lsr/ls_strtool.h>

#include <stdio.h>
#include <string.h>
#include "unittest-cpp/UnitTest++.h"

/**
 * A note about this test file:
 * If you want to add a test case for...
 *
 * ls_confparser_line/ls_confparser_linekv:
 * - Increment numItems
 * - Add the test case to the end of pInput
 * - Add the length of the test case to the end of pInputLen
 * - Create a pOut* array for the expected outcome for parse_line
 * - Add the array to the end of pOutput
 * - Add the number of items in the array to iOutArraySize
 * - Create a matching pOut*KV for the expected outcome for parser_linekv
 * - Add the array to the end of pOutputKV
 * The test should now be added.
 *
 * ls_confparser_multi/ls_getconfline:
 * - Add the string to the end of pMultiLineInput (separate it with \r\n)
 * - Add the expected new parameters to the end of pMultiLineOutput
 * - Increment iMultiLineOutLen to match the number of items in the array
 * - Increment iNumGetLineOut by the number of new lines created
 * - Create a pGetLineOut* array for the expected outcome for each line
 * - Add the array to the end of pGetLineOut
 * - Add the number of items in the array to iGetLineOutSize
 *
 * Any new complete tests should be added at the bottom, before the
 * confparser destruction if you want to use the same confparser.
 */



const int numItems = 12;
// Input for parse line and parse line KV tests.
const char *pInput[] =
{
    "Initial Test",
    " Second Test ",
    "     Third  \t  Test     ",
    " \"Fourth\"    \"   With Quotations   \"  And Without",
    "  \"Fifth\"   'With Different Types' of Quotations   ",
    "  Sixth    \" With \\\"Interior Quotes\\\" \" ",
    "Seventh with \"No closing quote.",
    "\r\nEighth with leading newline",
    "Ninth with trailing newline\r\n",
    "Tenth with\r\nInternal newline",
    "Eleventh with\\r\\nInternal newline",
    "        Twelfth     "
};

const int pInputLen[] =
{
    12,
    13,
    23,
    49,
    51,
    40,
    31,
    29,
    29,
    28,
    33,
    20
};

// Input for multi line and iterating getline tests.
const char *pMultiLineInput = "This\r\nis an\r\n attempt at\r\n"
                              "a multi-line\r\n\"\\\"input\\\"\".";

// Output for parse line tests
const char *pOut1[] = {"Initial", "Test"};
const char *pOut2[] = {"Second", "Test"};
const char *pOut3[] = {"Third", "Test"};
const char *pOut4[] = {"Fourth", "   With Quotations   ", "And", "Without"};
const char *pOut5[] = {"Fifth", "With Different Types", "of", "Quotations"};
const char *pOut6[] = {"Sixth", " With \\\"Interior Quotes\\\" "};
const char *pOut7[] = {"Seventh", "with", "No closing quote."};
const char *pOut8[] = {"Eighth", "with", "leading", "newline"};
const char *pOut9[] = {"Ninth", "with", "trailing", "newline"};
const char *pOut10[] = {"Tenth", "with"};
const char *pOut11[] = {"Eleventh", "with\\r\\nInternal", "newline"};
const char *pOut12[] = {"Twelfth"};

const char **pOutput[] =
{
    pOut1,
    pOut2,
    pOut3,
    pOut4,
    pOut5,
    pOut6,
    pOut7,
    pOut8,
    pOut9,
    pOut10,
    pOut11,
    pOut12
};

const int iOutArraySize[] =
{
    2,
    2,
    2,
    4,
    4,
    2,
    3,
    4,
    4,
    2,
    3,
    1
};

// Output for parse line KV tests.
const char *pOut1KV[] = {"Initial", "Test"};
const char *pOut2KV[] = {"Second", "Test"};
const char *pOut3KV[] = {"Third", "Test"};
const char *pOut4KV[] = {"Fourth", "\"   With Quotations   \"  And Without"};
const char *pOut5KV[] = {"Fifth", "'With Different Types' of Quotations"};
const char *pOut6KV[] = {"Sixth", " With \\\"Interior Quotes\\\" "};
const char *pOut7KV[] = {"Seventh", "with \"No closing quote."};
const char *pOut8KV[] = {"Eighth", "with leading newline"};
const char *pOut9KV[] = {"Ninth", "with trailing newline"};
const char *pOut10KV[] = {"Tenth", "with"};
const char *pOut11KV[] = {"Eleventh", "with\\r\\nInternal newline"};
const char *pOut12KV[] = {"Twelfth", NULL};

const char **pOutputKV[] =
{
    pOut1KV,
    pOut2KV,
    pOut3KV,
    pOut4KV,
    pOut5KV,
    pOut6KV,
    pOut7KV,
    pOut8KV,
    pOut9KV,
    pOut10KV,
    pOut11KV,
    pOut12KV
};

// Output for multi line test.
const char *pMultiLineOutput[] =
{
    "This",
    "is",
    "an",
    "attempt",
    "at",
    "a",
    "multi-line",
    "\\\"input\\\"",
    "."
};
const int iMultiLineOutLen = 9;

int iNumGetLineOut = 5;
const char *pGetLineOut1[] = {"This"};
const char *pGetLineOut2[] = {"is", "an"};
const char *pGetLineOut3[] = {"attempt", "at"};
const char *pGetLineOut4[] = {"a", "multi-line"};
const char *pGetLineOut5[] = {"\\\"input\\\"", "."};

const char **pGetLineOut[] =
{
    pGetLineOut1,
    pGetLineOut2,
    pGetLineOut3,
    pGetLineOut4,
    pGetLineOut5,
};

const int iGetLineOutSize[] =
{
    1,
    2,
    2,
    2,
    2
};

TEST(ls_confparser_test)
{
    const char *pBufBegin;
    const char *pBufEnd;
    const char *pLineBegin;
    const char *pLineEnd;
#ifdef LSR_CONFPARSERDEBUG
    printf("Start LSR Conf Parser Test\n");
#endif

    ls_confparser_t confParser;
    ls_confparser(&confParser);
    // Parse Line Test
    for (int i = 0; i < numItems; ++i)
    {
        ls_objarray_t *pList =
            ls_confparser_line(&confParser, pInput[i], pInput[i] + pInputLen[i]);
        CHECK(iOutArraySize[i] == ls_objarray_getsize(pList));
        for (int j = 0; j < iOutArraySize[i]; ++j)
        {
            ls_str_t *pObj = (ls_str_t *)ls_objarray_getobj(pList, j);
            CHECK(strncmp(
                      pOutput[i][j], ls_str_cstr(pObj), ls_str_len(pObj)) == 0);
        }
    }

    pBufBegin = pMultiLineInput;
    pBufEnd = pBufBegin + strlen(pMultiLineInput);
    // Parse Multi Test
    ls_objarray_t *pMulti =
        ls_confparser_multi(&confParser, pBufBegin, pBufEnd);
    CHECK(ls_objarray_getsize(pMulti) == iMultiLineOutLen);
    for (int i = 0; i < iMultiLineOutLen; ++i)
    {
        ls_str_t *pObj = (ls_str_t *)ls_objarray_getobj(pMulti, i);
        CHECK(strncmp(
                  pMultiLineOutput[i], ls_str_cstr(pObj), ls_str_len(pObj)) == 0);
    }
    // Get Line Test - use same initial buf begin and buf end.
    int n = 0;
    while ((pLineBegin =
                ls_getconfline(&pBufBegin, pBufEnd, &pLineEnd)) != NULL)
    {
        CHECK(pBufBegin <= pBufEnd + 1);
        CHECK(pLineBegin < pLineEnd);
        CHECK(n < iNumGetLineOut);
        ls_objarray_t *pList =
            ls_confparser_line(&confParser, pLineBegin, pLineEnd);
        CHECK(iGetLineOutSize[n] == ls_objarray_getsize(pList));
        for (int j = 0; j < iGetLineOutSize[n]; ++j)
        {
            ls_str_t *pObj = (ls_str_t *)ls_objarray_getobj(pList, j);
            CHECK(strncmp(
                      pGetLineOut[n][j], ls_str_cstr(pObj), ls_str_len(pObj)) == 0);
        }
        ++n;
    }
    CHECK(pBufBegin == pBufEnd + 1);

    // Parse Line KV Test
    for (int i = 0; i < numItems; ++i)
    {
        pBufBegin = pInput[i];
        pLineBegin =
            ls_getconfline(&pBufBegin, pBufBegin + pInputLen[i], &pLineEnd);
        CHECK(pLineBegin != NULL);
        ls_objarray_t *pList =
            ls_confparser_linekv(&confParser, pLineBegin, pLineEnd);
        CHECK(ls_objarray_getsize(pList) == 2);
        for (int j = 0; j < 2; ++j)
        {
            ls_str_t *pObj = (ls_str_t *)ls_objarray_getobj(pList, j);
            CHECK(!pOutputKV[i][j] == !ls_str_cstr(pObj));
            CHECK(strncmp(
                      pOutputKV[i][j], ls_str_cstr(pObj), ls_str_len(pObj)) == 0);
        }
    }

    ls_confparser_d(&confParser);

}

#endif

