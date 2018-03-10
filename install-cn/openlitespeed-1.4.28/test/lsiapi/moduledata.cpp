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
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>

int freefn(void *p)
{
    return 0;
}

typedef struct
{
    int number1;
    char s[8];
    int number2;
} MyTestData_st;

char *s_fn(void *obj, int *len)
{
    *len = sizeof(MyTestData_st);
    MyTestData_st *buf = (MyTestData_st *)malloc(*len);
    memcpy((char *)buf, (char *)obj, *len);
    return (char *)buf;
}

void *des_fn(char *buf, int len)
{
    assert((size_t)len >= sizeof(MyTestData_st));
    MyTestData_st *obj = (MyTestData_st *)malloc(sizeof(MyTestData_st));
    memcpy((char *)obj, buf, sizeof(MyTestData_st));
    return (void *)obj;
}

#define GET_GLOBAL_HASH_DATA_TEST
#ifdef GET_GLOBAL_HASH_DATA_TEST

/*
TEST(INIT_LSIAPI)
{
    init_lsiapi();
}

TEST(FILE_globalLsiDataTest)
{

    struct lsi_gdata_cont_val_t * pCont1 = LsiapiBridge::getLsiapiFunctions()->get_gdata_container(LSI_CONTAINER_FILE, "111", 3);
    struct lsi_gdata_cont_val_t * pCont2 = LsiapiBridge::getLsiapiFunctions()->get_gdata_container(LSI_CONTAINER_FILE, "122", 3);
    struct lsi_gdata_cont_val_t * pCont11 = LsiapiBridge::getLsiapiFunctions()->get_gdata_container(LSI_CONTAINER_FILE, "1111", 3);
    CHECK(pCont1 == pCont11);
    struct lsi_gdata_cont_val_t * pCont3 = LsiapiBridge::getLsiapiFunctions()->get_gdata_container(LSI_CONTAINER_FILE, "1111", 4);
    CHECK(pCont1 != pCont3);


    const char *k1 = "123";
    const char *k11 = "123";
    const char *k111 = "123";
    const char *k2 = "1234";
    const char *k21 = "1234";
    const char k3[] = "123\0\0"  "123";
    const char k4[] = "123\0\0""123\0";

    char *v1 = (char *)"12345670---xxxx\0\0""123";
    char *v2 = (char *)"12345670---xxxx\0\0""1234";

    MyTestData_st myTestData_st = {111, "1234567", 22222};

    void *p =  LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k1, 3, NULL, 0, des_fn);
    MyTestData_st *myTestData_st0 = NULL;
    if (p)
    {
        CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );
        myTestData_st0 = (MyTestData_st *)p;
    }


    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k1, 3, &myTestData_st, 1000, freefn, 1, s_fn);

    MyTestData_st myTestData_st2 = {222, "2222333", 333};
    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k2, 4, &myTestData_st2, 1000, freefn, 1, s_fn);

    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k1, 3, freefn, 0, des_fn);
    CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );

    void *p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, des_fn);
    CHECK( memcmp((void*)(&myTestData_st2), p2, sizeof(MyTestData_st)) == 0 );

    LsiapiBridge::getLsiapiFunctions()->delete_gdata(pCont1, k2, 4);
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, des_fn);
    CHECK( p2 == NULL);

    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k1, 3, freefn, 0, des_fn);
    CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );

    sleep(2); //sleep to make sure container create time > the item create time
    LsiapiBridge::getLsiapiFunctions()->empty_gdata_container(pCont1);
    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k1, 3, freefn, 0, des_fn);
    CHECK( p == NULL);

    LsiapiBridge::getLsiapiFunctions()->purge_gdata_container(pCont1);

    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k1, 3, &myTestData_st, 1000, freefn, 1, s_fn);
    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k1, 3, freefn, 0, des_fn);
    CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );

    sleep(2);
    system("touch /home/user/lsws-test/gdata/i1/76d/10/3.tmp");
    //Will call recover to reload file
    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k1, 3, freefn, 0, des_fn);
    CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );


    //EXPIRE testing, DO NOT SET BREAKPOINT
    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k2, 4, &myTestData_st2, 5, freefn, 1, s_fn);
    sleep(3);
    expire_gdata_check();
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, des_fn);     //renewed, still have 5 seconds expire time
    CHECK( memcmp((void*)(&myTestData_st2), p2, sizeof(MyTestData_st)) == 0 );
    sleep(3);
    expire_gdata_check();
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 0, des_fn);
    CHECK( memcmp((void*)(&myTestData_st2), p2, sizeof(MyTestData_st)) == 0 );  //passed 3 s, not renewed
    sleep(3);
    expire_gdata_check();
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 0, des_fn);     //expired!
    CHECK( p2 == NULL);             //You can set a break point here


    //TEst key name
    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k111, 3, freefn, 0, des_fn);
    CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );
    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 3, freefn, 0, des_fn);
    CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );

    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k2, 4, &myTestData_st2, 500, freefn, 1, s_fn);
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, des_fn);
    CHECK( memcmp((void*)(&myTestData_st2), p2, sizeof(MyTestData_st)) == 0 );

    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k2, 4, &myTestData_st, 500, freefn, 0, s_fn);  //not force, fail and no change
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, des_fn);
    CHECK( memcmp((void*)(&myTestData_st2), p2, sizeof(MyTestData_st)) == 0 );

    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k2, 4, &myTestData_st, 500, freefn, 1, s_fn);  //forced  change
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, des_fn);
    CHECK( memcmp((void*)(&myTestData_st), p2, sizeof(MyTestData_st)) == 0 );

    LsiapiBridge::getLsiapiFunctions()->delete_gdata(pCont1, k2, 4);
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, des_fn);
    CHECK( p2 == NULL);
}

TEST(Memory_globalLsiDataTest)
{
    struct lsi_gdata_cont_val_t * pCont1 = LsiapiBridge::getLsiapiFunctions()->get_gdata_container(LSI_CONTAINER_MEMORY, "111", 3);
    struct lsi_gdata_cont_val_t * pCont2 = LsiapiBridge::getLsiapiFunctions()->get_gdata_container(LSI_CONTAINER_MEMORY, "122", 3);
    struct lsi_gdata_cont_val_t * pCont11 = LsiapiBridge::getLsiapiFunctions()->get_gdata_container(LSI_CONTAINER_MEMORY, "1111", 3);
    CHECK(pCont1 == pCont11);
    struct lsi_gdata_cont_val_t * pCont3 = LsiapiBridge::getLsiapiFunctions()->get_gdata_container(LSI_CONTAINER_MEMORY, "1111", 4);
    CHECK(pCont1 != pCont3);


    const char *k1 = "123";
    const char *k11 = "123";
    const char *k111 = "123";
    const char *k2 = "1234";
    const char *k21 = "1234";
    const char k3[] = "123\0\0"  "123";
    const char k4[] = "123\0\0""123\0";

    char *v1 = (char *)"12345670---xxxx\0\0""123";
    char *v2 = (char *)"12345670---xxxx\0\0""1234";

    MyTestData_st myTestData_st = {111, "1234567", 22222};

    MyTestData_st *myTestData_st0 = NULL;

    void *p =  LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k1, 3, NULL, 0, NULL);
    CHECK( p == NULL);

    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k1, 3, &myTestData_st, 1000, freefn, 1, NULL);

    MyTestData_st myTestData_st2 = {222, "2222333", 333};
    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k2, 4, &myTestData_st2, 1000, freefn, 1, NULL);

    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k1, 3, freefn, 0, NULL);
    CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );

    void *p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, NULL);
    CHECK( memcmp((void*)(&myTestData_st2), p2, sizeof(MyTestData_st)) == 0 );

    LsiapiBridge::getLsiapiFunctions()->delete_gdata(pCont1, k2, 4);
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, NULL);
    CHECK( p2 == NULL);

    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k1, 3, freefn, 0, NULL);
    CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );

    sleep(2); //sleep to make sure container create time > the item create time
    LsiapiBridge::getLsiapiFunctions()->empty_gdata_container(pCont1);
    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k1, 3, freefn, 0, NULL);
    CHECK( p == NULL);

    LsiapiBridge::getLsiapiFunctions()->purge_gdata_container(pCont1);

    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k1, 3, &myTestData_st, 1000, freefn, 1, NULL);
    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k1, 3, freefn, 0, NULL);
    CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );

    //EXPIRE testing, DO NOT SET BREAKPOINT
    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k2, 4, &myTestData_st2, 5, freefn, 1, NULL);
    sleep(3);
    expire_gdata_check();
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, NULL);     //renewed, still have 5 seconds expire time
    CHECK( memcmp((void*)(&myTestData_st2), p2, sizeof(MyTestData_st)) == 0 );
    sleep(3);
    expire_gdata_check();
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 0, NULL);
    CHECK( memcmp((void*)(&myTestData_st2), p2, sizeof(MyTestData_st)) == 0 );  //passed 3 s, not renewed
    sleep(3);
    expire_gdata_check();
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 0, NULL);     //expired!
    CHECK( p2 == NULL);             //You can set a break point here



    //TEst key name
    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k111, 3, freefn, 0, NULL);
    CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );
    p = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 3, freefn, 0, NULL);
    CHECK( memcmp((void*)(&myTestData_st), p, sizeof(MyTestData_st)) == 0 );

    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k2, 4, &myTestData_st2, 500, freefn, 1, NULL);
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, NULL);
    CHECK( memcmp((void*)(&myTestData_st2), p2, sizeof(MyTestData_st)) == 0 );

    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k2, 4, &myTestData_st, 500, freefn, 0, NULL);  //not force, fail and no change
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, NULL);
    CHECK( memcmp((void*)(&myTestData_st2), p2, sizeof(MyTestData_st)) == 0 );

    LsiapiBridge::getLsiapiFunctions()->set_gdata(pCont1, k2, 4, &myTestData_st, 500, freefn, 1, NULL);  //forced  change
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, NULL);
    CHECK( memcmp((void*)(&myTestData_st), p2, sizeof(MyTestData_st)) == 0 );

    LsiapiBridge::getLsiapiFunctions()->delete_gdata(pCont1, k2, 4);
    p2 = LsiapiBridge::getLsiapiFunctions()->get_gdata(pCont1, k2, 4, freefn, 1, NULL);
    CHECK( p2 == NULL);
}
*/

#endif


#endif
