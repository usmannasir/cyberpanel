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

#include <ls.h>
#include <lsiapi/lsiapi.h>
#include <lsiapi/envmanager.h>
#include "unittest-cpp/UnitTest++.h"
#include <unistd.h>

int cb1(lsi_param_t *param)
{
    printf("test cb1, %s %d\n", (char *)param->ptr1, param->len1);
    return 0;
}

int cb2(lsi_param_t *param)
{
    printf("test cb2, %s %d\n", (char *)param->ptr1, param->len1);
    return 0;
}

int cb3(lsi_param_t *param)
{
    printf("test cb3, %s %d\n", (char *)param->ptr1, param->len1);
    return 0;
}

int cb4(lsi_param_t *param)
{
    printf("test cb4, %s %d\n", (char *)param->ptr1, param->len1);
    return 0;
}

int cb5(lsi_param_t *param)
{
    printf("test cb5, %s %d\n", (char *)param->ptr1, param->len1);
    return 0;
}

TEST(envManagerTest)
{
    EnvManager::getInstance().regEnvHandler("c?che*", 6, cb1);
    EnvManager::getInstance().regEnvHandler("hello!", 6, cb2);
    EnvManager::getInstance().regEnvHandler("hel", 3, cb3);
    EnvManager::getInstance().regEnvHandler("cc", 2, cb4);

    EnvManager::getInstance().regEnvHandler("?che*", 5, cb5);
    EnvManager::getInstance().regEnvHandler("che??", 5, cb2);
    EnvManager::getInstance().regEnvHandler("che*", 4, cb3);
    EnvManager::getInstance().regEnvHandler("cache", 5, cb4);


    lsi_callback_pf pcb = NULL;

    pcb = EnvManager::getInstance().findHandler("cc");
    CHECK(pcb == cb4);

    pcb = EnvManager::getInstance().findHandler("ccc");
    CHECK(pcb == NULL);

    pcb = EnvManager::getInstance().findHandler("ccche");
    CHECK(pcb == cb1);

    pcb = EnvManager::getInstance().findHandler("ccche!");
    CHECK(pcb == cb1);

    pcb = EnvManager::getInstance().findHandler("hel");
    CHECK(pcb == cb3);

    pcb = EnvManager::getInstance().findHandler("hello!");
    CHECK(pcb == cb2);

    pcb = EnvManager::getInstance().findHandler("xche!");
    CHECK(pcb == cb5);

    pcb = EnvManager::getInstance().findHandler("che!");
    CHECK(pcb == cb3);

    pcb = EnvManager::getInstance().findHandler("che!!");
    CHECK(pcb == cb2);  //because "che??" is registered before "che*"

    pcb = EnvManager::getInstance().findHandler("che!!!");
    CHECK(pcb == cb3);

    pcb = EnvManager::getInstance().findHandler("cache");
    CHECK(pcb == cb4);

}

TEST(INIT_LSIAPI)
{
    LsiapiBridge::initLsiapi();
}


//if need to test below cases
//Pleaes comment out one line in
//LSIAPI void set_req_env( lsi_session_t *session, const char *name, unsigned int nameLen, const char *val, int valLen )
//COMMENT OUT --->  pReq->addEnv( name, nameLen, val, valLen );
//otherwise will cause crash for pReq is NULL now
//
TEST(envManagerTest2)
{
    //FIXME: unit test crash, comment out for now.
    /*
    lsi_session_t *session = (void *)100;

    LsiapiBridge::getLsiapiFunctions()->set_req_env(session, "cache", 5, (void *)"1", 1);
    LsiapiBridge::getLsiapiFunctions()->set_req_env(session, "cache", 5, (void *)"22", 2);
    LsiapiBridge::getLsiapiFunctions()->set_req_env(session, "cache", 5, (void *)"222", 3);
    //print cb4

    LsiapiBridge::getLsiapiFunctions()->set_req_env(session, "hello!", 6, (void *)"1", 1);
    LsiapiBridge::getLsiapiFunctions()->set_req_env(session, "hello!", 6, (void *)"121212", 6);
    //print

    LsiapiBridge::getLsiapiFunctions()->set_req_env(session, "xche!", 5, (void *)"1", 1);
    LsiapiBridge::getLsiapiFunctions()->set_req_env(session, "xche!", 5, (void *)"abcdef", 6);
    //p
    */
}


#endif
