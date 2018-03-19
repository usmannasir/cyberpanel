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

#include <lsiapi/lsiapi.h>
#include <ls.h>
#include "unittest-cpp/UnitTest++.h"
#include <unistd.h>
#include <assert.h>
#include <lsiapi/moduletimer.h>
#include <util/datetime.h>

void test_module_timer_cb_fp(const void *p)
{
    char buf[31];
    DateTime::getRFCTime(DateTime::s_curTime, buf);
    printf("Current time is %s[%s]\n", buf, ((p) ? (char *)p : "NULL param"));

}

TEST(INIT_LSIAPI111)
{
    LsiapiBridge::initLsiapi();
}




TEST(TEst_Module_Timer)
{
    int tid1, tid2, tid3, tid4, tid5, tid6;
    tid1 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 3, 0,
            test_module_timer_cb_fp, NULL);
    DateTime::s_curTime += 3;
    CHECK(ModTimerList::getInstance().checkExpired() == 1);
    CHECK(ModTimerList::getInstance().checkExpired() == 0);


    tid1 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 3, 0,
            test_module_timer_cb_fp, (void *)"3 1");
    tid2 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 2, 0,
            test_module_timer_cb_fp, (void *)"2");
    tid3 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 3, 0,
            test_module_timer_cb_fp, (void *)"3 2");
    tid4 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 4, 0,
            test_module_timer_cb_fp, (void *)"4 1");
    tid5 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 5, 0,
            test_module_timer_cb_fp, (void *)"5 1");
    tid6 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 5, 0,
            test_module_timer_cb_fp, (void *)"5 2");
    LsiapiBridge::getLsiapiFunctions()->remove_timer(tid5);
    //"5 1 remove"
    DateTime::s_curTime += 5;
    CHECK(ModTimerList::getInstance().checkExpired() == 5);
    CHECK(ModTimerList::getInstance().checkExpired() == 0);

    tid1 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 3, 0,
            test_module_timer_cb_fp, (void *)"3 1");
    tid2 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 2, 0,
            test_module_timer_cb_fp, (void *)"2 1");
    tid3 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 3, 0,
            test_module_timer_cb_fp, (void *)"3 2");
    tid4 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 4, 0,
            test_module_timer_cb_fp, (void *)"4 1");
    tid5 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 5, 0,
            test_module_timer_cb_fp, (void *)"5 1");
    tid6 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 5, 0,
            test_module_timer_cb_fp, (void *)"5 2");

    tid1 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 3, 0,
            test_module_timer_cb_fp, (void *)"3 3");
    tid2 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 2, 0,
            test_module_timer_cb_fp, (void *)"2 2");
    tid3 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 3, 0,
            test_module_timer_cb_fp, (void *)"3 4");
    tid4 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 4, 0,
            test_module_timer_cb_fp, (void *)"4 2");
    tid5 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 5, 0,
            test_module_timer_cb_fp, (void *)"5 3");
    tid6 = LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 5, 0,
            test_module_timer_cb_fp, (void *)"5 4");

    LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 3, 0,
            test_module_timer_cb_fp, (void *)"3 5");
    LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 2, 0,
            test_module_timer_cb_fp, (void *)"2 3");
    LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 3, 0,
            test_module_timer_cb_fp, (void *)"3 6");
    LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 4, 0,
            test_module_timer_cb_fp, (void *)"4 3");
    LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 5, 0,
            test_module_timer_cb_fp, (void *)"5 5");
    LsiapiBridge::getLsiapiFunctions()->set_timer(1000 * 5, 0,
            test_module_timer_cb_fp, (void *)"5 6");

    LsiapiBridge::getLsiapiFunctions()->remove_timer(tid1);
    LsiapiBridge::getLsiapiFunctions()->remove_timer(tid2);
    LsiapiBridge::getLsiapiFunctions()->remove_timer(tid3);
    LsiapiBridge::getLsiapiFunctions()->remove_timer(tid4);
    LsiapiBridge::getLsiapiFunctions()->remove_timer(tid5);
    LsiapiBridge::getLsiapiFunctions()->remove_timer(tid6);
    //Remove "3 3" "2 2" "3 4" "4 2" "5 3" "5 4"

    DateTime::s_curTime += 5;
    //NOTICE: This is 13 because the cleanup timer expires as well.
    CHECK(ModTimerList::getInstance().checkExpired() == 13);
    CHECK(ModTimerList::getInstance().checkExpired() == 0);

}

#endif
