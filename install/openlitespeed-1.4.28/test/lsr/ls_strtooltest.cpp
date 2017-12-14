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

#include "ls_strtooltest.h"
#include <lsr/ls_strtool.h>
#include <lsr/ls_strlist.h>
#include <lsr/ls_str.h>
#include "unittest-cpp/UnitTest++.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

SUITE(ls_strtooltest)
{
    TEST(ls_strtest_test)
    {
        /* test string */
        static const char *mystr     = "AbCd1234./?*WxYz";
        /* test string upper case */
        static const char *upperstr  = "ABCD1234./?*WXYZ";
        /* test string lower case */
        static const char *lowerstr  = "abcd1234./?*wxyz";
        /* hex values for first 9 chars in mystr */
        static const char *hexstr    = "41624364313233342e";

        /* parsing strings */
        static const char *parsestr  = "\t Arg1\t \tArg2 \t Arg3 \t";
        static const char *arg1astr  = "Arg1";
        static const char *arg1bstr  = "\"Arg1\\\"\t \\\\\\\" Arg1End\"";
        static const char *arg2str   = "Arg2";
        static const char *rule1str  = "\t  Rule_\\ String 123";
        static const char *rule2str  = "\t \"Rule \\\"String\"123";
        static const char *rule3str  = "\t \"Rule \\\"String 123";

        /* bracketed string - functions assume you are already in a bracket */
        /* fails if called from brackstr, succeeds from brackstr + 1 */
        static const char *brackstr  = "{1|2{AB:CD}4:5}";

        /* an `off_t' (number) value */
        static const char *offtstr   = "-12345";

        /* string with escaped quotes to be unescaped */
        static const char *quotestr  = "\\\"A\\\'B\\\'C\\\"D";
        static const char *quotestr1 = "\\\"A\'B\'C\\\"D";
        static const char *quotestr2 = "\"A\\\'B\\\'C\"D";

        ls_parse_t obj;
        int cnt;
        const char *p1;
        const char *p2;
        const char *p3;
        const char *p4;
        char mybuf[80];

        CHECK(strcmp(ls_strupper(mystr, mybuf), upperstr) == 0);
        CHECK(strcmp(ls_strlower(mystr, mybuf), lowerstr) == 0);
        cnt = sizeof(mybuf);
        CHECK(strcmp(ls_strnupper(mystr, mybuf, &cnt), upperstr) == 0);
        CHECK(cnt == (int)strlen(mystr));
        cnt = 8;
        CHECK(strncmp(ls_strnlower(mystr, mybuf, &cnt), lowerstr, 8) == 0);
        CHECK(cnt == 8);

        snprintf(mybuf, sizeof(mybuf), " \t %s \t ", mystr);
        CHECK(strcmp(ls_strtrim(mybuf), mystr) == 0);
        snprintf(mybuf, sizeof(mybuf), " \t %s \t ", mystr);
        p1 = (const char *)mybuf;
        p2 = p1 + strlen(p1);
        cnt = ls_strtrim2(&p1, &p2);
        CHECK(cnt == (int)strlen(mystr));
        CHECK(strncmp(p1, mystr, cnt) == 0);

        cnt = strlen(hexstr);
        CHECK(ls_hexencode(mystr, (cnt >> 1), mybuf) == cnt);
        CHECK(strcmp(mybuf, hexstr) == 0);
        strcpy(mybuf, mystr);       /* encode in place */
        CHECK(ls_hexencode((const char *)mybuf, (cnt >> 1), mybuf) == cnt);
        CHECK(strcmp(mybuf, hexstr) == 0);
        CHECK(ls_hexdecode(hexstr, cnt, mybuf) == (cnt >> 1));
        CHECK(strncmp(mybuf, mystr, (cnt >> 1)) == 0);

        p1 = parsestr + strlen(parsestr);
        ls_parse(&obj, parsestr, p1, " \t");
        CHECK(ls_parse_isend(&obj) ==  0);
        CHECK(ls_parse_getstrend(&obj) ==  NULL);
        for (cnt = 0; cnt < 3; ++cnt)       /* 3 args at parsestr */
        {
            p1 = ls_parse_trimparse(&obj);
            CHECK((ls_parse_getstrend(&obj) - p1) == 4);
            CHECK(strncmp(p1, "Arg", 3) == 0);
        }
        CHECK(ls_parse_trimparse(&obj) == NULL);
        CHECK(ls_parse_isend(&obj) ==  1);

        p1 = (const char *)mybuf;
        snprintf(mybuf, sizeof(mybuf), "%s\t %s", arg1astr, arg2str);
        CHECK(strcmp(ls_strtrim((char *)ls_strnextarg(&p1, " \t") + 1),
                     arg2str) == 0);
        CHECK(p1 == (const char *)mybuf);
        p1 = (const char *)mybuf;
        snprintf(mybuf, sizeof(mybuf), "%s\t %s", arg1bstr, arg2str);
        CHECK(strcmp(ls_strtrim((char *)ls_strnextarg(&p1, NULL) + 1),
                     arg2str) == 0);
        CHECK(p1 == (const char *)&mybuf[1]);

        p1 = rule1str;                  /* space delimited */
        p4 = rule1str + strlen(rule1str);
        CHECK(ls_parsenextarg(&p1, p4, &p2, &p3, &p4) == 0);
        CHECK(p2 == rule1str + 3);      /* ArgBegin */
        CHECK(p3 == (const char *)strrchr(rule1str, ' '));     /* ArgEnd */
        CHECK(p1 == (p3 + 1));          /* RuleStr */
        p1 = rule2str;                  /* quote delimited */
        p4 = rule2str + strlen(rule2str);
        CHECK(ls_parsenextarg(&p1, p4, &p2, &p3, &p4) == 0);
        CHECK(p2 == rule2str + 3);      /* ArgBegin */
        CHECK(p3 == (const char *)strrchr(rule2str, '\"'));     /* ArgEnd */
        CHECK(p1 == (p3 + 1));          /* RuleStr */
        p1 = rule3str;                  /* not delimited */
        p4 = rule3str + strlen(rule3str);
        CHECK(ls_parsenextarg(&p1, p4, &p2, &p3, &p4) == 0);
        CHECK(p2 == rule3str + 3);      /* ArgBegin */
        CHECK(p3 == p4);                /* ArgEnd */
        CHECK(p1 == p4);                /* RuleStr */

        p2 = brackstr + strlen(brackstr);
        CHECK(ls_findclosebracket(brackstr, p2, '{', '}') == p2);
        CHECK(ls_findclosebracket(brackstr + 1, p2, '{', '}')
              == (const char *)strrchr(brackstr, '}'));
        CHECK(ls_findcharinbracket(brackstr, p2, ':', '{', '}') == NULL);
        CHECK(ls_findcharinbracket(brackstr + 1, p2, ':', '{', '}')
              == (const char *)strrchr(brackstr, ':'));
        CHECK(ls_findcharinbracket(brackstr + 1, p2, '!', '{', '}') == NULL);

        CHECK(ls_offset2string(mybuf, sizeof(mybuf), atoi(offtstr))
              == (int)strlen(offtstr));
        CHECK(strcmp(mybuf, offtstr) == 0);

        strcpy(mybuf, quotestr);
        CHECK(ls_unescapequote(mybuf, mybuf + strlen(mybuf), '\'') == 2);
        CHECK(strcmp(&mybuf[2], quotestr1) == 0);
        strcpy(mybuf, quotestr);
        CHECK(ls_unescapequote(mybuf, mybuf + strlen(mybuf), '\"') == 2);
        CHECK(strcmp(&mybuf[2], quotestr2) == 0);
    }


    typedef struct
    {
        const char *str;
        int case_sens_match;
        int no_case_match;
    } testcases_t;

    static char pattern1[] = "**.example.??m";
    static testcases_t test1[] =
    {
        {   "www1.example.com",     1,  1   },
        {   ".example.com",         1,  1   },
        {   "www1.example.com.",    0,  0   },
        {   "www1.Example.CoM",     0,  1   },
    };

    static char pattern2[] = "*.example.com*";
    static testcases_t test2[] =
    {
        {   "www1.example.com",     1,  1   },
        {   ".example.com",         1,  1   },
        {   "www1.example.com.",    1,  1   },
        {   "www1.Example.CoM",     0,  1   },
    };

    static char pattern3[] = "*.example.com?";
    static testcases_t test3[] =
    {
        {   "www1.example.com",     0,  0   },
        {   ".example.com",         0,  0   },
        {   "www1.example.com.",    1,  1   },
        {   "www1.Example.CoM",     0,  0   },
    };

    static char pattern5[] = "*abc*?abd*";
    static testcases_t test5[] =
    {
        {   "abcdabd",              1,  1,  },
        {   "abcabd",               0,  0,  },
        {   "abcdabcabcAbd",        0,  1,  },
        {   "abcdabcabcabc",        0,  0,  },
    };

    TEST(ls_teststringmatch)
    {
        testcases_t *ptst;
        ls_strlist_iter pbegin, pend;
        ls_strlist_t *ppattern;

        ppattern = ls_parsematchpattern(pattern1);
        CHECK(ppattern);
        CHECK(ls_strlist_size(ppattern) == 4);
        pbegin = ls_strlist_begin(ppattern);
        pend = ls_strlist_end(ppattern);

        CHECK(strcmp(ls_str_cstr(pbegin[0]), "*") == 0);
        CHECK(*(ls_str_cstr(pbegin[1])) == 0);
        CHECK(strncmp(ls_str_cstr(pbegin[1]) + 1, &pattern1[2], 9) == 0);
        CHECK(strcmp(ls_str_cstr(pbegin[2]), "??") == 0);
        CHECK(strcmp(ls_str_cstr(pbegin[3]) + 1, "m") == 0);

        ptst = test1;
        while (ptst < &test1[sizeof(test1) / sizeof(test1[0])])
        {
            CHECK((ls_strmatch(ptst->str, NULL, pbegin, pend, 1) == 0)
                  == ptst->case_sens_match);
            CHECK((ls_strmatch(ptst->str, NULL, pbegin, pend, 0) == 0)
                  == ptst->no_case_match);
            ++ptst;
        }
        ls_strlist_delete(ppattern);

        ppattern = ls_parsematchpattern(pattern2);
        CHECK(ppattern);
        CHECK(ls_strlist_size(ppattern) == 3);
        pbegin = ls_strlist_begin(ppattern);
        pend = ls_strlist_end(ppattern);

        CHECK(strcmp(ls_str_cstr(pbegin[0]), "*") == 0);
        CHECK(*(ls_str_cstr(pbegin[1])) == 0);
        CHECK(strncmp(ls_str_cstr(pbegin[1]) + 1, &pattern2[1], 12) == 0);
        CHECK(strcmp(ls_str_cstr(pbegin[2]), "*") == 0);

        ptst = test2;
        while (ptst < &test2[sizeof(test2) / sizeof(test2[0])])
        {
            CHECK((ls_strmatch(ptst->str, NULL, pbegin, pend, 1) == 0)
                  == ptst->case_sens_match);
            CHECK((ls_strmatch(ptst->str, NULL, pbegin, pend, 0) == 0)
                  == ptst->no_case_match);
            ++ptst;
        }
        ls_strlist_delete(ppattern);

        ppattern = ls_parsematchpattern(pattern3);
        CHECK(ppattern);
        CHECK(ls_strlist_size(ppattern) == 3);
        pbegin = ls_strlist_begin(ppattern);
        pend = ls_strlist_end(ppattern);

        CHECK(strcmp(ls_str_cstr(pbegin[0]), "*") == 0);
        CHECK(*(ls_str_cstr(pbegin[1])) == 0);
        CHECK(strncmp(ls_str_cstr(pbegin[1]) + 1, &pattern3[1], 12) == 0);
        CHECK(*(ls_str_cstr(pbegin[2])) == '?');

        ptst = test3;
        while (ptst < &test3[sizeof(test3) / sizeof(test3[0])])
        {
            CHECK((ls_strmatch(ptst->str, NULL, pbegin, pend, 1) == 0)
                  == ptst->case_sens_match);
            CHECK((ls_strmatch(ptst->str, NULL, pbegin, pend, 0) == 0)
                  == ptst->no_case_match);
            ++ptst;
        }
        ls_strlist_delete(ppattern);

        ppattern = ls_parsematchpattern(pattern5);
        CHECK(ppattern);
        CHECK(ls_strlist_size(ppattern) == 6);
        pbegin = ls_strlist_begin(ppattern);
        pend = ls_strlist_end(ppattern);

        ptst = test5;
        while (ptst < &test5[sizeof(test5) / sizeof(test5[0])])
        {
            CHECK((ls_strmatch(ptst->str, NULL, pbegin, pend, 1) == 0)
                  == ptst->case_sens_match);
            CHECK((ls_strmatch(ptst->str, NULL, pbegin, pend, 0) == 0)
                  == ptst->no_case_match);
            ++ptst;
        }
        ls_strlist_delete(ppattern);
    }

    TEST(ls_mempbrktest)
    {
        const char *pAccept, *pInput = "abcdefg";
        int iAcceptLength, iInputLength = 7;

        printf("ls_strtool: mempbrk test\n");
        pAccept = "f";
        iAcceptLength = 1;
        CHECK(ls_mempbrk(pInput, iInputLength, pAccept, iAcceptLength)
              == pInput + 5);

        pAccept = "jklofd";
        iAcceptLength = 4;
        CHECK(ls_mempbrk(pInput, iInputLength, pAccept, iAcceptLength)
              == NULL);

        iAcceptLength = 5;
        CHECK(ls_mempbrk(pInput, iInputLength, pAccept, iAcceptLength)
              == pInput + 5);

        iAcceptLength = 6;
        CHECK(ls_mempbrk(pInput, iInputLength, pAccept, iAcceptLength)
              == pInput + 3);

        pInput = "zxvnmgfpoi";
        iInputLength = 10;
        pAccept = "abcdefg";
        iAcceptLength = 7;
        CHECK(ls_mempbrk(pInput, iInputLength, pAccept, iAcceptLength)
              == pInput + 5);
    }

    /* For Look Up SubString, if fail, check again with debugger to find i value */
    TEST(ls_lookupsubstringtest)
    {
        const char *pRet;
        int iRetLen, iNumTests = 20;
        printf("ls_strtool: lookupsubstring test\n");

        for (int i = 0; i < iNumTests; ++i)
        {
            iRetLen = 0;
            pRet = ls_lookupsubstring(aLUSSInputs[i],
                                      aLUSSInputs[i] + aLUSSInputLen[i],
                                      aLUSSKeys[i],
                                      aLUSSKeyLen[i],
                                      &iRetLen,
                                      aLUSSSep[i],
                                      aLUSSComp[i]
                                     );
            /* if aLUSSRet == -1, expect NULL */
            /* if aLUSSRetLen == -2 not looking for a len */
            if (aLUSSRet[i] == -1)
            {
                CHECK(pRet == NULL);
                if (pRet != NULL)
                {
                    printf("ERROR: Failed test i = %d\n", i);
                    printf("Expected pRet == NULL, got %p\n", pRet);
                }
            }
            else if (aLUSSRetLen[i] == -2)
            {
                CHECK(pRet == aLUSSInputs[i] + aLUSSRet[i]);
                if (pRet != aLUSSInputs[i] + aLUSSRet[i])
                {
                    printf("ERROR: Failed test i = %d\n", i);
                    printf("Expected pRet = %p, got %p\n",
                           (aLUSSInputs[i] + aLUSSRet[i]), pRet);
                }
            }
            else
            {
                CHECK(pRet == aLUSSInputs[i] + aLUSSRet[i]
                      && iRetLen == aLUSSRetLen[i]);
                if (pRet != aLUSSInputs[i] + aLUSSRet[i]
                    || iRetLen != aLUSSRetLen[i])
                {
                    printf("ERROR: Failed test i = %d\n", i);
                    printf("Expected pRet = %p, retLen = %d, got %p, %d\n",
                           (aLUSSInputs[i] + aLUSSRet[i]),
                           aLUSSRetLen[i],
                           pRet, iRetLen);
                }
            }
        }
    }

    TEST(ls_memspntest)
    {
        size_t iOutput;
        int iNumTests = 6;
        printf("ls_strtool: memspn test\n");
        for (int i = 0; i < iNumTests; ++i)
        {
            iOutput = ls_memspn(pMemspnInput, aMemspnInputSize[i],
                                pMemspnAccept, aMemspnAcceptSize[i]);
            CHECK(iOutput == aMemspnOutput[i]);
            if (iOutput != aMemspnOutput[i])
            {
                printf("ERROR: Failed test i = %d\n", i);
                printf("Expected output = %d, got %d\n", (int)aMemspnOutput[i],
                       (int)iOutput);
            }
        }
    }

    TEST(ls_memcspntest)
    {
        size_t iOutput;
        int iNumTests = 6;
        printf("ls_strtool: memcspn test\n");
        for (int i = 0; i < iNumTests; ++i)
        {
            iOutput = ls_memcspn(pMemspnInput, aMemspnInputSize[i],
                                 pMemspnAccept, aMemspnAcceptSize[i]);
            CHECK(iOutput == aMemCspnOutput[i]);
            if (iOutput != aMemCspnOutput[i])
            {
                printf("ERROR: Failed test i = %d\n", i);
                printf("Expected output = %d, got %d\n", (int)aMemCspnOutput[i],
                       (int)iOutput);
            }
        }
    }

}

#endif
