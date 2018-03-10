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

#include "stringmaptest.h"
#include <util/stringmap.h>
#include "unittest-cpp/UnitTest++.h"
#include <util/stringtool.h>
#include <util/stringlist.h>
#include <util/autostr.h>


SUITE(StringMapTest)
{
    TEST(test)
    {
        const char *ps[] = { "Zero", "One", "Two", "Three" };

        StringMap<int> map1;
        for (int i = 0 ; i < 4 ; i++)
            CHECK(map1.insert(ps[i], i) == true);
        for (int i = 0 ; i < 4 ; i++)
            CHECK(map1.insert(ps[i], i + 10) == false);
        typedef StringMap<int> StringIntMap;
        StringIntMap::const_iterator iter = map1.find("Zero");
        CHECK(iter != map1.end());
        CHECK(map1.find("Z") == map1.end());
        CHECK(iter->second == 0);
        for (int i = 0 ; i < 4 ; i++)
        {
            iter = map1.find(ps[i]);
            CHECK(iter != map1.end());
            CHECK(iter->second == i);
        }

        for (int i = 0 ; i < 4 ; i++)
            CHECK(map1.insertUpdate(ps[i], i + 10) == true);

        for (int i = 0 ; i < 4 ; i++)
        {
            iter = map1.find(ps[i]);
            CHECK(iter != map1.end());
            CHECK(iter->second == i + 10);
        }
    }


    TEST(testStringMatch)
    {
        char pattern1[] = "**.example.??m";
        char testcase1[] = "www1.example.com";
        char testcase2[] = ".example.com";
        char testcase3[] = "www1.example.com.";
        char testcase4[] = "www1.Example.CoM";

        char pattern2[] = "*.example.com*";

        char pattern3[] = "*.example.com?";



        StringList *pPattern1 = StringTool::parseMatchPattern(pattern1);
        CHECK(pPattern1);
        CHECK(pPattern1->size() == 4);
        CHECK(strcmp((*pPattern1->begin())->c_str(), "*") == 0);
        CHECK(*((*(pPattern1->begin() + 1))->c_str()) == 0);
        CHECK(strncmp((*(pPattern1->begin() + 1))->c_str() + 1, &pattern1[2],
                      9) == 0);
        CHECK(strcmp((*(pPattern1->begin() + 2))->c_str(), "??") == 0);
        CHECK(strcmp((*(pPattern1->begin() + 3))->c_str() + 1, "m") == 0);
        int ret;
        ret = StringTool::strMatch(testcase1, NULL, pPattern1->begin(),
                                   pPattern1->end(), 1);
        CHECK(ret == 0);
        ret = StringTool::strMatch(testcase1, NULL, pPattern1->begin(),
                                   pPattern1->end(), 0);
        CHECK(ret == 0);

        ret = StringTool::strMatch(testcase2, NULL, pPattern1->begin(),
                                   pPattern1->end(), 1);
        CHECK(ret == 0);
        ret = StringTool::strMatch(testcase2, NULL, pPattern1->begin(),
                                   pPattern1->end(), 0);
        CHECK(ret == 0);

        ret = StringTool::strMatch(testcase3, NULL, pPattern1->begin(),
                                   pPattern1->end(), 1);
        CHECK(ret != 0);
        ret = StringTool::strMatch(testcase3, NULL, pPattern1->begin(),
                                   pPattern1->end(), 0);
        CHECK(ret != 0);

        ret = StringTool::strMatch(testcase4, NULL, pPattern1->begin(),
                                   pPattern1->end(), 1);
        CHECK(ret != 0);
        ret = StringTool::strMatch(testcase4, NULL, pPattern1->begin(),
                                   pPattern1->end(), 0);
        CHECK(ret == 0);
        delete pPattern1;


        StringList *pPattern2 = StringTool::parseMatchPattern(pattern2);
        CHECK(pPattern2);
        CHECK(pPattern2->size() == 3);
        CHECK(strcmp((*pPattern2->begin())->c_str(), "*") == 0);
        CHECK(*((*(pPattern2->begin() + 1))->c_str()) == 0);
        CHECK(strncmp((*(pPattern2->begin() + 1))->c_str() + 1, &pattern2[1],
                      12) == 0);
        CHECK(*((*(pPattern2->begin() + 2))->c_str()) == '*');
        ret = StringTool::strMatch(testcase1, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret == 0);
        ret = StringTool::strMatch(testcase1, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret == 0);

        ret = StringTool::strMatch(testcase2, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret == 0);
        ret = StringTool::strMatch(testcase2, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret == 0);

        ret = StringTool::strMatch(testcase3, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret == 0);
        ret = StringTool::strMatch(testcase3, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret == 0);

        ret = StringTool::strMatch(testcase4, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret != 0);
        ret = StringTool::strMatch(testcase4, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret == 0);

        delete pPattern2;
        pPattern2 = StringTool::parseMatchPattern(pattern3);
        CHECK(pPattern2);
        CHECK(pPattern2->size() == 3);
        CHECK(strcmp((*pPattern2->begin())->c_str(), "*") == 0);
        CHECK(*((*(pPattern2->begin() + 1))->c_str()) == 0);
        CHECK(strncmp((*(pPattern2->begin() + 1))->c_str() + 1, &pattern2[1],
                      12) == 0);
        CHECK(*((*(pPattern2->begin() + 2))->c_str()) == '?');
        ret = StringTool::strMatch(testcase1, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret != 0);
        ret = StringTool::strMatch(testcase1, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret != 0);

        ret = StringTool::strMatch(testcase2, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret != 0);
        ret = StringTool::strMatch(testcase2, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret != 0);

        ret = StringTool::strMatch(testcase3, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret == 0);
        ret = StringTool::strMatch(testcase3, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret == 0);

        ret = StringTool::strMatch(testcase4, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret != 0);
        ret = StringTool::strMatch(testcase4, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret != 0);
        delete pPattern2;

        char pattern5[] = "*abc*?abd*";
        char testcase9[] = "abcdabd";
        char testcase6[] = "abcabd";
        char testcase7[] = "abcdabcabcAbd";
        char testcase8[] = "abcdabcabcabc";

        pPattern2 = StringTool::parseMatchPattern(pattern5);
        CHECK(pPattern2);
        CHECK(pPattern2->size() == 6);
        ret = StringTool::strMatch(testcase9, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret == 0);
        ret = StringTool::strMatch(testcase9, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret == 0);

        ret = StringTool::strMatch(testcase6, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret != 0);
        ret = StringTool::strMatch(testcase6, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret != 0);

        ret = StringTool::strMatch(testcase7, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret != 0);
        ret = StringTool::strMatch(testcase7, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret == 0);

        ret = StringTool::strMatch(testcase8, NULL, pPattern2->begin(),
                                   pPattern2->end(), 1);
        CHECK(ret != 0);
        ret = StringTool::strMatch(testcase8, NULL, pPattern2->begin(),
                                   pPattern2->end(), 0);
        CHECK(ret != 0);

    }
}


#endif
