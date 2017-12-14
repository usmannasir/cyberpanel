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

#include <stdio.h>

#include <lsr/ls_hash.h>
#include <lsr/ls_xpool.h>
#include "unittest-cpp/UnitTest++.h"


static int plus_int(const void *pKey, void *pData, void *pUData)
{
    ls_hash_t *hash = (ls_hash_t *)pUData;
    ls_hash_update(hash, pKey, (void *)((long)pData + (long)10));
    return 0;
}

TEST(ls_hashtest_test)
{
#ifdef LSR_HASH_DEBUG
    printf("Start LSR Hash Test\n");
#endif
    ls_hash_t *hash = ls_hash_new(10, NULL, NULL, NULL);
    CHECK(ls_hash_size(hash) == 0);
    CHECK(ls_hash_capacity(hash) == 13);
    ls_hash_iter iter = hash->insert_fn(hash, (void *)0, (void *)0);
    CHECK(iter != ls_hash_end(hash));
    CHECK((long)ls_hash_getkey(iter) == 0);
    CHECK((long)ls_hash_getdata(iter) == 0);
    CHECK(ls_hash_gethkey(iter) == 0);
    CHECK(ls_hash_getnext(iter) == NULL);
    CHECK(ls_hash_size(hash) == 1);

    ls_hash_iter iter1 = hash->insert_fn(hash, (void *)13, (void *)13);
    CHECK(iter1 != ls_hash_end(hash));
    CHECK((long)ls_hash_getkey(iter1) == 13);
    CHECK((long)ls_hash_getdata(iter1) == 13);
    CHECK(ls_hash_gethkey(iter1) == 13);
    CHECK(ls_hash_getnext(iter1) == iter);
    CHECK(ls_hash_size(hash) == 2);

    ls_hash_iter iter4 = hash->insert_fn(hash, (void *)26, (void *)26);
    CHECK(iter4 != ls_hash_end(hash));
    CHECK((long)ls_hash_getkey(iter4) == 26);
    CHECK((long)ls_hash_getdata(iter4) == 26);
    CHECK(ls_hash_gethkey(iter4) == 26);
    CHECK(ls_hash_getnext(iter4) == iter1);
    CHECK(ls_hash_size(hash) == 3);

    ls_hash_iter iter2 = hash->insert_fn(hash, (void *)15, (void *)15);
    CHECK(iter2 != ls_hash_end(hash));
    CHECK((long)ls_hash_getkey(iter2) == 15);
    CHECK((long)ls_hash_getdata(iter2) == 15);
    CHECK(ls_hash_gethkey(iter2) == 15);
    CHECK(ls_hash_getnext(iter2) == NULL);
    CHECK(ls_hash_size(hash) == 4);

    ls_hash_iter iter3;
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == iter);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)15);
    CHECK(iter3 == iter2);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)39);
    CHECK(iter3 == NULL);
    iter3 = hash->find_fn(hash, (void *)28);
    CHECK(iter3 == NULL);

    iter3 = ls_hash_begin(hash);
    CHECK(iter3 == iter4);
    iter3 = ls_hash_next(hash, iter3);
    CHECK(iter3 == iter1);
    iter3 = ls_hash_next(hash, iter3);
    CHECK(iter3 == iter);
    iter3 = ls_hash_next(hash, iter3);
    CHECK(iter3 == iter2);
    iter3 = ls_hash_next(hash, iter3);
    CHECK(iter3 == ls_hash_end(hash));

    int n = ls_hash_foreach2(hash, ls_hash_begin(hash), ls_hash_end(hash),
                             plus_int, (void *)hash);

    CHECK(n == 4);
    CHECK((long)ls_hash_getdata(iter) == 10);
    CHECK((long)ls_hash_getdata(iter1) == 23);
    CHECK((long)ls_hash_getdata(iter2) == 25);
    CHECK((long)ls_hash_getdata(iter4) == 36);

    ls_hash_erase(hash, iter);
    CHECK(ls_hash_size(hash) == 3);
    ls_hash_t hash2;
    ls_hash(&hash2, 10, NULL, NULL, NULL);
    CHECK(ls_hash_size(&hash2) == 0);
    CHECK(ls_hash_capacity(&hash2) == 13);
    ls_hash_swap(hash, &hash2);
    CHECK(ls_hash_size(hash) == 0);
    CHECK(ls_hash_size(&hash2) == 3);
    ls_hash_swap(hash, &hash2);
    CHECK(ls_hash_size(hash) == 3);
    ls_hash_d(&hash2);

    CHECK(ls_hash_getnext(iter1) == NULL);
    CHECK(ls_hash_getnext(iter4) == iter1);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == NULL);

    iter = hash->insert_fn(hash, (void *)0, (void *)0);
    CHECK(iter != ls_hash_end(hash));
    CHECK(ls_hash_size(hash) == 4);
    CHECK(ls_hash_getnext(iter) == iter4);
    CHECK(ls_hash_getnext(iter4) == iter1);
    CHECK(ls_hash_getnext(iter1) == NULL);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == iter);

    ls_hash_erase(hash, iter);
    CHECK(ls_hash_size(hash) == 3);
    CHECK(ls_hash_getnext(iter1) == NULL);
    CHECK(ls_hash_getnext(iter4) == iter1);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == NULL);

    iter = hash->insert_fn(hash, (void *)0, (void *)0);
    CHECK(iter != ls_hash_end(hash));
    CHECK(ls_hash_size(hash) == 4);
    CHECK(ls_hash_getnext(iter) == iter4);
    CHECK(ls_hash_getnext(iter4) == iter1);
    CHECK(ls_hash_getnext(iter1) == NULL);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == iter);

    ls_hash_erase(hash, iter4);
    CHECK(ls_hash_size(hash) == 3);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == NULL);
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == iter);
    CHECK(ls_hash_getnext(iter) == iter1);
    CHECK(ls_hash_getnext(iter1) == NULL);

    iter4 = hash->insert_fn(hash, (void *)26, (void *)26);
    CHECK(iter4 != ls_hash_end(hash));
    CHECK(ls_hash_size(hash) == 4);
    CHECK(ls_hash_getnext(iter4) == iter);
    CHECK(ls_hash_getnext(iter) == iter1);
    CHECK(ls_hash_getnext(iter1) == NULL);

    ls_hash_iter iter5 = hash->insert_fn(hash, (void *)5, (void *)5);
    CHECK(ls_hash_capacity(hash) == 13);
    ls_hash_iter iter6 = hash->insert_fn(hash, (void *)6, (void *)6);
    CHECK(ls_hash_capacity(hash) == 13);
    ls_hash_iter iter7 = hash->insert_fn(hash, (void *)7, (void *)7);
    CHECK(ls_hash_capacity(hash) == 13);
    ls_hash_iter iter8 = hash->insert_fn(hash, (void *)8, (void *)8);
    CHECK(ls_hash_capacity(hash) == 53);
    CHECK(ls_hash_getnext(iter) == NULL);
    CHECK(ls_hash_getnext(iter1) == NULL);
    CHECK(ls_hash_getnext(iter2) == NULL);
    CHECK(ls_hash_getnext(iter3) == NULL);
    CHECK(ls_hash_getnext(iter4) == NULL);
    CHECK(ls_hash_getnext(iter5) == NULL);
    CHECK(ls_hash_getnext(iter6) == NULL);
    CHECK(ls_hash_getnext(iter7) == NULL);
    CHECK(ls_hash_getnext(iter8) == NULL);

    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == iter);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)15);
    CHECK(iter3 == iter2);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)28);
    CHECK(iter3 == NULL);

    ls_hash_delete(hash);

    // check interface to xxhash
    ls_hash_t xxhash;
    ls_hash_iter xxiter = NULL;
    const char *pKey = "hello world";
    ls_hash(&xxhash, 10, ls_hash_hfstring, ls_hash_cmpstring, NULL);
    CHECK((xxiter = ls_hash_find(&xxhash, pKey)) == NULL);
    CHECK((xxiter = ls_hash_insert(&xxhash, pKey, NULL)) != NULL);
    CHECK(ls_hash_find(&xxhash, pKey) == xxiter);
    CHECK(ls_hash_size(&xxhash) == 1);
    ls_hash_d(&xxhash);
}

TEST(ls_hashpooltest_test)
{
#ifdef LSR_HASH_DEBUG
    printf("Start LSR Hash XPool Test\n");
#endif
    ls_xpool_t *pool = ls_xpool_new();
    ls_hash_t *hash = ls_hash_new(10, NULL, NULL, pool);
    CHECK(ls_hash_size(hash) == 0);
    CHECK(ls_hash_capacity(hash) == 13);
    ls_hash_iter iter = hash->insert_fn(hash, (void *)0, (void *)0);
    CHECK(iter != ls_hash_end(hash));
    CHECK((long)ls_hash_getkey(iter) == 0);
    CHECK((long)ls_hash_getdata(iter) == 0);
    CHECK(ls_hash_gethkey(iter) == 0);
    CHECK(ls_hash_getnext(iter) == NULL);
    CHECK(ls_hash_size(hash) == 1);

    ls_hash_iter iter1 = hash->insert_fn(hash, (void *)13, (void *)13);
    CHECK(iter1 != ls_hash_end(hash));
    CHECK((long)ls_hash_getkey(iter1) == 13);
    CHECK((long)ls_hash_getdata(iter1) == 13);
    CHECK(ls_hash_gethkey(iter1) == 13);
    CHECK(ls_hash_getnext(iter1) == iter);
    CHECK(ls_hash_size(hash) == 2);

    ls_hash_iter iter4 = hash->insert_fn(hash, (void *)26, (void *)26);
    CHECK(iter4 != ls_hash_end(hash));
    CHECK((long)ls_hash_getkey(iter4) == 26);
    CHECK((long)ls_hash_getdata(iter4) == 26);
    CHECK(ls_hash_gethkey(iter4) == 26);
    CHECK(ls_hash_getnext(iter4) == iter1);
    CHECK(ls_hash_size(hash) == 3);

    ls_hash_iter iter2 = hash->insert_fn(hash, (void *)15, (void *)15);
    CHECK(iter2 != ls_hash_end(hash));
    CHECK((long)ls_hash_getkey(iter2) == 15);
    CHECK((long)ls_hash_getdata(iter2) == 15);
    CHECK(ls_hash_gethkey(iter2) == 15);
    CHECK(ls_hash_getnext(iter2) == NULL);
    CHECK(ls_hash_size(hash) == 4);

    ls_hash_iter iter3;
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == iter);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)15);
    CHECK(iter3 == iter2);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)39);
    CHECK(iter3 == NULL);
    iter3 = hash->find_fn(hash, (void *)28);
    CHECK(iter3 == NULL);

    iter3 = ls_hash_begin(hash);
    CHECK(iter3 == iter4);
    iter3 = ls_hash_next(hash, iter3);
    CHECK(iter3 == iter1);
    iter3 = ls_hash_next(hash, iter3);
    CHECK(iter3 == iter);
    iter3 = ls_hash_next(hash, iter3);
    CHECK(iter3 == iter2);
    iter3 = ls_hash_next(hash, iter3);
    CHECK(iter3 == ls_hash_end(hash));

    int n = ls_hash_foreach2(hash, ls_hash_begin(hash), ls_hash_end(hash),
                             plus_int, (void *)hash);

    CHECK(n == 4);
    CHECK((long)ls_hash_getdata(iter) == 10);
    CHECK((long)ls_hash_getdata(iter1) == 23);
    CHECK((long)ls_hash_getdata(iter2) == 25);
    CHECK((long)ls_hash_getdata(iter4) == 36);

    ls_hash_erase(hash, iter);
    CHECK(ls_hash_size(hash) == 3);
    ls_hash_t hash2;
    ls_hash(&hash2, 10, NULL, NULL, pool);
    CHECK(ls_hash_size(&hash2) == 0);
    CHECK(ls_hash_capacity(&hash2) == 13);
    ls_hash_swap(hash, &hash2);
    CHECK(ls_hash_size(hash) == 0);
    CHECK(ls_hash_size(&hash2) == 3);
    ls_hash_swap(hash, &hash2);
    CHECK(ls_hash_size(hash) == 3);
    ls_hash_d(&hash2);

    CHECK(ls_hash_getnext(iter1) == NULL);
    CHECK(ls_hash_getnext(iter4) == iter1);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == NULL);

    iter = hash->insert_fn(hash, (void *)0, (void *)0);
    CHECK(iter != ls_hash_end(hash));
    CHECK(ls_hash_size(hash) == 4);
    CHECK(ls_hash_getnext(iter) == iter4);
    CHECK(ls_hash_getnext(iter4) == iter1);
    CHECK(ls_hash_getnext(iter1) == NULL);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == iter);

    ls_hash_erase(hash, iter);
    CHECK(ls_hash_size(hash) == 3);
    CHECK(ls_hash_getnext(iter1) == NULL);
    CHECK(ls_hash_getnext(iter4) == iter1);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == NULL);

    iter = hash->insert_fn(hash, (void *)0, (void *)0);
    CHECK(iter != ls_hash_end(hash));
    CHECK(ls_hash_size(hash) == 4);
    CHECK(ls_hash_getnext(iter) == iter4);
    CHECK(ls_hash_getnext(iter4) == iter1);
    CHECK(ls_hash_getnext(iter1) == NULL);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == iter);

    ls_hash_erase(hash, iter4);
    CHECK(ls_hash_size(hash) == 3);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == NULL);
    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == iter);
    CHECK(ls_hash_getnext(iter) == iter1);
    CHECK(ls_hash_getnext(iter1) == NULL);

    iter4 = hash->insert_fn(hash, (void *)26, (void *)26);
    CHECK(iter4 != ls_hash_end(hash));
    CHECK(ls_hash_size(hash) == 4);
    CHECK(ls_hash_getnext(iter4) == iter);
    CHECK(ls_hash_getnext(iter) == iter1);
    CHECK(ls_hash_getnext(iter1) == NULL);

    ls_hash_iter iter5 = hash->insert_fn(hash, (void *)5, (void *)5);
    CHECK(ls_hash_capacity(hash) == 13);
    ls_hash_iter iter6 = hash->insert_fn(hash, (void *)6, (void *)6);
    CHECK(ls_hash_capacity(hash) == 13);
    ls_hash_iter iter7 = hash->insert_fn(hash, (void *)7, (void *)7);
    CHECK(ls_hash_capacity(hash) == 13);
    ls_hash_iter iter8 = hash->insert_fn(hash, (void *)8, (void *)8);
    CHECK(ls_hash_capacity(hash) == 53);
    CHECK(ls_hash_getnext(iter) == NULL);
    CHECK(ls_hash_getnext(iter1) == NULL);
    CHECK(ls_hash_getnext(iter2) == NULL);
    CHECK(ls_hash_getnext(iter3) == NULL);
    CHECK(ls_hash_getnext(iter4) == NULL);
    CHECK(ls_hash_getnext(iter5) == NULL);
    CHECK(ls_hash_getnext(iter6) == NULL);
    CHECK(ls_hash_getnext(iter7) == NULL);
    CHECK(ls_hash_getnext(iter8) == NULL);

    iter3 = hash->find_fn(hash, (void *)0);
    CHECK(iter3 == iter);
    iter3 = hash->find_fn(hash, (void *)13);
    CHECK(iter3 == iter1);
    iter3 = hash->find_fn(hash, (void *)15);
    CHECK(iter3 == iter2);
    iter3 = hash->find_fn(hash, (void *)26);
    CHECK(iter3 == iter4);
    iter3 = hash->find_fn(hash, (void *)28);
    CHECK(iter3 == NULL);

    ls_hash_delete(hash);
    ls_xpool_delete(pool);
}


#endif
