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


#include <thread/thread.h>

#include <pthread.h>
#include <stdio.h>
#include "unittest-cpp/UnitTest++.h"

static void *threadtest(void *arg)
{
    return arg;
}


TEST(THREAD_THREAD_TEST)
{
    printf("Start thread test!\n");
    void *arg = (void *)10;
    void *ret = NULL;
    pthread_t cmp = 0;
    Thread *thread = new Thread();

    CHECK(thread->isEqualTo(cmp));
    CHECK(thread->getAttr() != NULL);
    pthread_attr_t *myattr = const_cast<pthread_attr_t *>(thread->getAttr());
    CHECK(myattr != NULL);
    CHECK(thread->isJoinable());
    thread->attrSetDetachState(PTHREAD_CREATE_DETACHED);
    CHECK(!thread->isJoinable());
    thread->attrSetDetachState(PTHREAD_CREATE_JOINABLE);

    CHECK(thread->run(threadtest, arg) == 0);
    CHECK(thread->join(&ret) == 0);
    CHECK(arg == ret);
}

#endif



