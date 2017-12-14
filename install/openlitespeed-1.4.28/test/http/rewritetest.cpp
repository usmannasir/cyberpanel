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

#include "rewritetest.h"
#include <http/rewriterule.h>
#include <http/rewritemap.h>
#include <http/httpheader.h>
#include <http/httpstatuscode.h>
#include "unittest-cpp/UnitTest++.h"



void testParseCond()
{
    char achTest1[] = " \t %{REMOTE_HOST} \t !^host1.* [OR, \tnocase]";
    RewriteCond rule1;
    char *pBegin = achTest1;
    char *pEnd = achTest1 + strlen(achTest1);
    CHECK(rule1.parse(pBegin, pEnd, NULL) == 0);
    CHECK(rule1.getFlag() ==
          (COND_FLAG_NOCASE | COND_FLAG_OR | COND_FLAG_NOMATCH));
    CHECK(rule1.getOpcode() == COND_OP_REGEX);

    char achTest2[] = "%{HTTP_REFERER} !=\"\"";
    RewriteCond rule2;
    pBegin = achTest2;
    pEnd = achTest2 + strlen(achTest2);
    CHECK(rule2.parse(pBegin, pEnd, NULL) == 0);
    CHECK(rule2.getFlag() ==
          (COND_FLAG_NOMATCH));
    CHECK(rule2.getOpcode() == COND_OP_EQ);
    CHECK(strcmp(rule2.getPattern(), "") == 0);

}

void testParseRule()
{
    char achTest1[] = " \t !^/somepath(.*)  \t /otherpath$1 "
                      "[R=305, \tnocase, L\t , Skip=8\t, N , C, T=text/plain, noescape, PT, NS, qsappend]";
    RewriteRule rule1;
    char *pBegin = achTest1;
    char *pEnd = achTest1 + strlen(achTest1);
    CHECK(rule1.parseRule(pBegin, pEnd, NULL) == 0);
    CHECK(rule1.getSkip() == 8);
    CHECK(rule1.getFirstCond() == NULL);
    CHECK(rule1.getStatusCode() == SC_305);
    CHECK(strcmp(rule1.getMimeType(), "text/plain") == 0);
    CHECK(rule1.getAction() == RULE_ACTION_REDIRECT);
    CHECK(rule1.getFlag() ==
          (RULE_FLAG_NOCASE | RULE_FLAG_NOMATCH | RULE_FLAG_LAST |
           RULE_FLAG_NEXT | RULE_FLAG_CHAIN | RULE_FLAG_NOESCAPE |
           RULE_FLAG_PASSTHRU | RULE_FLAG_NOSUBREQ | RULE_FLAG_QSAPPEND));

    char achTest2[] = "RewriteCond %{HTTP_HOST} \t!^my\\.domain\\.name [nc]\n"
                      "RewriteCond %{HTTP_HOST} \t-d\n"
                      "RewriteCond %{SERVER_PORT}\t>80\n"
                      "RewriteRule ^/(.*)\t\thttp://my\\.doamin\\.name:%{SERVER_PORT}/$1 [L,R]\n";

    RewriteRule rule2;
    pBegin = achTest2;
    pEnd = achTest2 + strlen(achTest2);
    CHECK(rule2.parse(pBegin, NULL) == 0);
    CHECK(rule2.getStatusCode() == SC_302);
    CHECK(rule2.getSkip() == 0);
    CHECK(rule2.getMimeType() == NULL);
    CHECK(rule2.getAction() == RULE_ACTION_REDIRECT);
    CHECK(rule2.getFlag() == RULE_FLAG_LAST);
    const RewriteCond *pCond = rule2.getFirstCond();
    CHECK(pCond != NULL);
    CHECK(pCond->getFlag() == (COND_FLAG_NOMATCH | COND_FLAG_NOCASE));
    CHECK(pCond->getOpcode() == COND_OP_REGEX);
    pCond = (RewriteCond *)pCond->next();
    CHECK(pCond != NULL);
    CHECK(pCond->getFlag() == 0);
    CHECK(pCond->getOpcode() == COND_OP_DIR);
    pCond = (RewriteCond *)pCond->next();
    CHECK(pCond != NULL);
    CHECK(pCond->getFlag() == 0);
    CHECK(pCond->getOpcode() == COND_OP_GREATER);
    pCond = (RewriteCond *)pCond->next();
    CHECK(pCond == NULL);


    char achTest3[] = "RewriteRule !^user/[^/]*/web - [C]";
    RewriteRule rule3;
    pBegin = achTest3;
    pEnd = achTest3 + strlen(achTest3);
    CHECK(rule3.parse(pBegin, NULL) == 0);
    CHECK(rule3.getFlag() & RULE_FLAG_CHAIN);
    CHECK(rule3.getFlag() & RULE_FLAG_NOREWRITE);





}



void testParseSubst()
{
    RewriteMapList mapList;
    RewriteSubstFormat subst;
    RewriteMap *pMap = new RewriteMap();
    pMap->setName("map1");
    mapList.insert(pMap->getName(), pMap);
    char achTest1[] =
        "$1%0\\\\\\$1\\%1${map1:${map1:$2|\"\"}|%{DOCUMENT_ROOT}}%{HTTP_USER_AGENT}"
        "%{HTTP:usEr-agent}%{HTTP:customized-header}%{ENV:path} \tlast";
    char *pBegin = achTest1;
    char *pEnd = achTest1 + strlen(achTest1);
    CHECK(subst.parse(pBegin, pEnd, &mapList) == 0);
    RewriteSubstItem *pItem;

    pItem = (RewriteSubstItem *)subst.head()->next();
    CHECK(pItem != NULL);
    CHECK(pItem->getType() == REF_RULE_SUBSTR);
    CHECK(pItem->getIndex() == 1);

    pItem = (RewriteSubstItem *)pItem->next();
    CHECK(pItem != NULL);
    CHECK(pItem->getType() == REF_COND_SUBSTR);
    CHECK(pItem->getIndex() == 0);

    pItem = (RewriteSubstItem *)pItem->next();
    CHECK(pItem != NULL);
    CHECK(pItem->getType() == REF_STRING);
    CHECK(pItem->getStr()->len() == 5);
    CHECK(strcmp(pItem->getStr()->c_str(), "\\$1%1") == 0);

    pItem = (RewriteSubstItem *)pItem->next();
    CHECK(pItem != NULL);
    CHECK(pItem->getType() == REF_MAP);
    MapRefItem *pMapRef = ((RewriteSubstItem *)pItem)->getMapRef();
    CHECK(pMapRef);
    CHECK(pMapRef->getMap() == pMap);
    CHECK(pMapRef->getDefaultFormat());
    CHECK(((RewriteSubstItem *)
           pMapRef->getDefaultFormat()->head()->next())->getType()
          == REF_DOC_ROOT);
    CHECK(pMapRef->getKeyFormat());
    RewriteSubstItem *pItem1 = (RewriteSubstItem *)(
                                   pMapRef->getKeyFormat()->head()->next());
    CHECK(pItem1->getType() == REF_MAP);

    pItem = (RewriteSubstItem *)pItem->next();
    CHECK(pItem != NULL);
    CHECK(pItem->getType() == HttpHeader::H_USERAGENT);

    pItem = (RewriteSubstItem *)pItem->next();
    CHECK(pItem != NULL);
    CHECK(pItem->getType() == HttpHeader::H_USERAGENT);

    pItem = (RewriteSubstItem *)pItem->next();
    CHECK(pItem != NULL);
    CHECK(pItem->getType() == REF_HTTP_HEADER);
    CHECK(strcmp(pItem->getStr()->c_str(), "customized-header") == 0);

    pItem = (RewriteSubstItem *)pItem->next();
    CHECK(pItem != NULL);
    CHECK(pItem->getType() == REF_ENV);
    CHECK(strcmp(pItem->getStr()->c_str(), "path") == 0);

    pItem = (RewriteSubstItem *)pItem->next();
    CHECK(pItem != NULL);
    CHECK(pItem->getType() == REF_STRING);
    CHECK(pItem->getStr()->len() == 6);
    CHECK(strcmp(pItem->getStr()->c_str(), " \tlast") == 0);

    pItem = (RewriteSubstItem *)pItem->next();
    CHECK(pItem == NULL);
}


TEST(RewriteTest_testParse)
{
    testParseSubst();
    testParseCond();
    testParseRule();
}
#endif

