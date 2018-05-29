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
#include "hpacktest.h"
#include "unittest-cpp/UnitTest++.h"
#include <util/autostr.h>
#include <util/autobuf.h>
#include <stdlib.h>
#include <stdio.h>


void addEntry(HpackDynTbl &dynTab, const char *name,
              const char *value, uint8_t nameId)
{
    dynTab.pushEntry((char *)name, strlen(name), (char *)value, strlen(value),
                     nameId);
}

void printTable(HpackDynTbl &dynTab)
{
    printf("Dynamic Table : \n");
    int count = dynTab.getEntryCount();
    for (int i = 1 ; i <= count; ++i)
    {
        int tabId = i + HPACK_STATIC_TABLE_SIZE;
        DynTblEntry *pEntry = (DynTblEntry *)dynTab.getEntry(
                                  tabId);

        printf("[%3d]  (s = %3d) %s: %s\n",
               i, pEntry->getEntrySize(), pEntry->getName(), pEntry->getValue());
    }
    printf("\tTable size: %zd\n", dynTab.getTotalTableSize());
}

TEST(hapck_test_1)
{
    HpackDynTbl dynTable;
    dynTable.updateMaxCapacity(256);

    printf("size of DynTblEntry is %zd\n", sizeof(DynTblEntry));

    addEntry(dynTable, ":authority", "www.example.com", 1);
    printTable(dynTable);

    addEntry(dynTable, "cache-control", "no-cache", 24);
    printTable(dynTable);

    addEntry(dynTable, "custom-key", "custom-value", 0);
    printTable(dynTable);

    addEntry(dynTable, "custom-key2",
             "custom-value22321grotretretuerotiueroituerotureotuouertoueirtoeirutoierutoeirt3213123123213213213213",
             0);
    printTable(dynTable);

//    int index = 0;
//     DynamicTableEntry *pEntry = dynTable.find((char *)"custom-key", sizeof("custom-key") -1, index);
//     if (pEntry)
//         dynTable.removeEntry(pEntry);
    printTable(dynTable);

    dynTable.reset();
    printTable(dynTable);
    dynTable.updateMaxCapacity(256);
    printTable(dynTable);

    addEntry(dynTable, ":status", "302", 0);
    addEntry(dynTable, "cache-control", "private", 24);
    addEntry(dynTable, "date", "Mon, 21 Oct 2013 20:13:21 GMT", 33);
    addEntry(dynTable, "location", "https://www.example.com", 46);
    printTable(dynTable);

    addEntry(dynTable, ":status", "307", 0);
    printTable(dynTable);

    addEntry(dynTable, "date", "Mon, 21 Oct 2013 20:13:22 GMT", 33);
    printTable(dynTable);

    addEntry(dynTable, "content-encoding", "gzip", 0);
    printTable(dynTable);

    addEntry(dynTable, "set-cookie",
             "foo=ASDJKHQKBZXOQWEOPIUAXQWEOIU; max-age=3600; version=1", 55);
    printTable(dynTable);

    dynTable.updateMaxCapacity(110);
    printTable(dynTable);

    dynTable.updateMaxCapacity(256);
    printTable(dynTable);



}

void testNameValue(const char *name, const char *val, int result,
                   int val_match_result)
{
    int val_match;
    int index = Hpack::getStxTabId((char *)name, (uint16_t)strlen(name) ,
                                   (char *)val, (uint16_t)strlen(val), val_match);
    printf("name: %s, val: %s, index = %d match = %d\n", name, val, index,
           val_match);
    CHECK(index == result && val_match == val_match_result);
}


TEST(hapck_test_2)
{
    testNameValue(":authority", "www.example.com", 1, 0);
    testNameValue(":authority1", "www.example.com", 0, 0);
    testNameValue(":authority", "www.example.com", 1, 0);
    testNameValue(":authority1", "www.example.com", 0, 0);

    testNameValue(":method", "GET", 2, 1);
    testNameValue(":method", "gET", 2, 0);
    testNameValue(":method", "PURGE", 2, 0);
    testNameValue(":method", "POST", 3, 1);

    testNameValue(":scheme", "http", 6, 1);
    testNameValue(":scheme", "HTTP", 6, 0);
    testNameValue(":scheme", "https", 7, 1);
    testNameValue(":scheme", "httPS", 6, 0);

//     testNameValue("scheme", "http", 0, 0);
//     testNameValue("scheme", "https", 0, 0);

    testNameValue(":status", "200", 8, 1);
    testNameValue(":status", "401", 8, 0);
    testNameValue(":status", "500", 14, 1);
//    testNameValue(":status-xxx", "200", 0, 0);

    testNameValue("accept-encoding", "gzip, deflate", 16, 1);
    testNameValue("accept-encoding", "gzip", 16, 0);

    testNameValue("accept-charset", "en", 15, 0);
    testNameValue("accept-charset", "EN", 15, 0);

    testNameValue("age", "100", 21, 0);
    testNameValue("age", "10000", 21, 0);

    testNameValue("www-authenticate", "wwwewe", 61, 0);
    testNameValue("www-authenticate-", "dtertete", 0, 0);

}

void displayHeader(unsigned char *buf, int len)
{
    int i;
    for (i = 0; i < len / 16; ++i)
    {
        printf("%02x%02x %02x%02x %02x%02x %02x%02x %02x%02x %02x%02x %02x%02x %02x%02x | \n",
               buf[i * 16 + 0], buf[i * 16 + 1], buf[i * 16 + 2], buf[i * 16 + 3],
               buf[i * 16 + 4], buf[i * 16 + 5], buf[i * 16 + 6], buf[i * 16 + 7],
               buf[i * 16 + 8], buf[i * 16 + 9], buf[i * 16 + 10], buf[i * 16 + 11],
               buf[i * 16 + 12], buf[i * 16 + 13], buf[i * 16 + 14], buf[i * 16 + 15]);
    }

    i *= 16;
    for (; i < len; ++i)
        printf(((i % 2 == 0) ? "%02x" : "%02x "), buf[i]);
    printf("\n");

}

#define STR_TO_IOVEC_TEST(a) ((char *)a), (sizeof(a) -1)
TEST(hapck_test_RFC_EXample)
{
    unsigned char respBuf[8192] = {0};
    unsigned char *respBufEnd = respBuf + 8192;
    Hpack hpack;
    hpack.getRespDynTbl().updateMaxCapacity(256);

    unsigned char *pBuf = respBuf;
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST(":status"),
                           STR_TO_IOVEC_TEST("302"));
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("cache-control"), STR_TO_IOVEC_TEST("private"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("date"),
                           STR_TO_IOVEC_TEST("Mon, 21 Oct 2013 20:13:21 GMT"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("location"),
                           STR_TO_IOVEC_TEST("https://www.example.com"));
    displayHeader(respBuf, pBuf - respBuf);
    printTable(hpack.getRespDynTbl());
    char bufSample1[] =
        "\x48\x82\x64\x02\x58\x85\xae\xc3\x77\x1a\x4b\x61\x96\xd0\x7a\xbe"
        "\x94\x10\x54\xd4\x44\xa8\x20\x05\x95\x04\x0b\x81\x66\xe0\x82\xa6"
        "\x2d\x1b\xff\x6e\x91\x9d\x29\xad\x17\x18\x63\xc7\x8f\x0b\x97\xc8"
        "\xe9\xae\x82\xae\x43\xd3";
    CHECK(memcmp(bufSample1, respBuf, pBuf - respBuf) == 0);


    pBuf = respBuf;
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST(":status"),
                           STR_TO_IOVEC_TEST("307"));
    printTable(hpack.getRespDynTbl());
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("cache-control"), STR_TO_IOVEC_TEST("private"));
    printTable(hpack.getRespDynTbl());
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("date"),
                           STR_TO_IOVEC_TEST("Mon, 21 Oct 2013 20:13:21 GMT"));
    printTable(hpack.getRespDynTbl());
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("location"),
                           STR_TO_IOVEC_TEST("https://www.example.com"));
    displayHeader(respBuf, pBuf - respBuf);
    printTable(hpack.getRespDynTbl());
    char bufSample2[] = "\x48\x83\x64\x0e\xff\xc1\xc0\xbf";
    CHECK(memcmp(bufSample2, respBuf, pBuf - respBuf) == 0);

    pBuf = respBuf;
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST(":status"),
                           STR_TO_IOVEC_TEST("200"));
    printTable(hpack.getRespDynTbl());
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("cache-control"), STR_TO_IOVEC_TEST("private"));
    printTable(hpack.getRespDynTbl());
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("date"),
                           STR_TO_IOVEC_TEST("Mon, 21 Oct 2013 20:13:22 GMT"));
    printTable(hpack.getRespDynTbl());
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("location"),
                           STR_TO_IOVEC_TEST("https://www.example.com"));
    printTable(hpack.getRespDynTbl());
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("content-encoding"), STR_TO_IOVEC_TEST("gzip"));
    printTable(hpack.getRespDynTbl());
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("set-cookie"),
                           STR_TO_IOVEC_TEST("foo=ASDJKHQKBZXOQWEOPIUAXQWEOIU; max-age=3600; version=1"));
    printTable(hpack.getRespDynTbl());
    displayHeader(respBuf, pBuf - respBuf);


    char bufSample3[] =
        "\x88\xc1\x61\x96\xd0\x7a\xbe\x94\x10\x54\xd4\x44\xa8\x20\x05\x95"
        "\x04\x0b\x81\x66\xe0\x84\xa6\x2d\x1b\xff\xc0\x5a\x83\x9b\xd9\xab"
        "\x77\xad\x94\xe7\x82\x1d\xd7\xf2\xe6\xc7\xb3\x35\xdf\xdf\xcd\x5b"
        "\x39\x60\xd5\xaf\x27\x08\x7f\x36\x72\xc1\xab\x27\x0f\xb5\x29\x1f"
        "\x95\x87\x31\x60\x65\xc0\x03\xed\x4e\xe5\xb1\x06\x3d\x50\x07";
    CHECK(memcmp(bufSample3, respBuf, pBuf - respBuf) == 0);



    /****************************
     * decHeader testing
     *
     ****************************/
    unsigned char *bufSamp4 = (unsigned char *)
                              "\x82\x86\x84\x41\x8c\xf1\xe3\xc2\xe5\xf2\x3a\x6b\xa0\xab\x90\xf4\xff";
    unsigned char *pSrc = bufSamp4;
    unsigned char *bufEnd =  bufSamp4 + strlen((const char *)bufSamp4);
    int rc;
    char out[2048];
//     char name[1024];
//     char val[1024];
    uint16_t name_len = 1024;
    uint16_t val_len = 1024;
    while ((rc = hpack.decHeader(pSrc, bufEnd, out, out + sizeof(out), name_len,
                                 val_len)) > 0)
    {
        char *name = out;
        char *val = name + name_len;
        printf("[%d %d]%.*s: %.*s\n", name_len, val_len,
               name_len, name, val_len, val);
    }
    printTable(hpack.getReqDynTbl());


    unsigned char *bufSamp = (unsigned char *)
                             "\x82\x86\x84\xbe\x58\x86\xa8\xeb\x10\x64\x9c\xbf";
    pSrc = bufSamp;
    bufEnd =  bufSamp + strlen((const char *)bufSamp);
    while ((rc = hpack.decHeader(pSrc, bufEnd, out, out + sizeof(out), name_len,
                                 val_len)) > 0)
    {
        char *name = out;
        char *val = name + name_len;
        printf("[%d %d]%.*s: %.*s\n", name_len, val_len,
               name_len, name, val_len, val);
    }
    printTable(hpack.getReqDynTbl());

    bufSamp = (unsigned char *)
              "\x82\x87\x85\xbf\x40\x88\x25\xa8\x49\xe9\x5b\xa9\x7d\x7f\x89\x25\xa8\x49\xe9\x5b\xb8\xe8\xb4\xbf";
    pSrc = bufSamp;
    bufEnd =  bufSamp + strlen((const char *)bufSamp);
    while ((rc = hpack.decHeader(pSrc, bufEnd, out, out + sizeof(out), name_len,
                                 val_len)) > 0)
    {
        char *name = out;
        char *val = name + name_len;
        printf("[%d %d]%.*s: %.*s\n", name_len, val_len,
               name_len, name, val_len, val);
    }
    printTable(hpack.getReqDynTbl());

}


TEST(hapck_self_enc_dec_test)
{
    unsigned char respBuf[8192] = {0};
    unsigned char *respBufEnd = respBuf + 8192;
    Hpack hpack;
    unsigned char *pSrc = respBuf;
    unsigned char *bufEnd;
    int rc;
    char out[2048];
//     char name[1024];
//     char val[1024];
    uint16_t name_len = 0;
    uint16_t val_len = 0;

    hpack.getRespDynTbl().updateMaxCapacity(256);
    hpack.getReqDynTbl().updateMaxCapacity(256);

    unsigned char *pBuf = respBuf;

    //Reproduce bug with special charset
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("content-disposition"),
                           STR_TO_IOVEC_TEST("inline; filename=\"Ekran Alıntısı.PNG\""));
    displayHeader(respBuf, pBuf - respBuf);
    printTable(hpack.getRespDynTbl());

    /****************************
    * decHeader testing
    ****************************/
    pSrc = respBuf;
    bufEnd =  pBuf;
    while ((rc = hpack.decHeader(pSrc, bufEnd, out, out + sizeof(out), name_len,
                                 val_len)) > 0)
    {
        char *name = out;
        char *val = name + name_len;
        printf("[%d %d]%.*s: %.*s\n", name_len, val_len,
               name_len, name, val_len, val);
    }
    printTable(hpack.getReqDynTbl());


    //1:
    pBuf = respBuf;
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST(":status"),
                           STR_TO_IOVEC_TEST("200"));
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("cache-control"),
                           STR_TO_IOVEC_TEST("public, max-age=1000"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("date"),
                           STR_TO_IOVEC_TEST("Mon, 21 Oct 2013 20:13:23 GMT"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("allow"),
                           STR_TO_IOVEC_TEST("*.*"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("location"),
                           STR_TO_IOVEC_TEST("https://www.example.com"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("my-test_key"),
                           STR_TO_IOVEC_TEST("my-test-values1111"));
    displayHeader(respBuf, pBuf - respBuf);
    printTable(hpack.getRespDynTbl());


    /****************************
    * decHeader testing
    ****************************/
    pSrc = respBuf;
    bufEnd =  pBuf;
    while ((rc = hpack.decHeader(pSrc, bufEnd, out, out + sizeof(out), name_len,
                                 val_len)) > 0)
    {
        char *name = out;
        char *val = name + name_len;
        printf("[%d %d]%.*s: %.*s\n", name_len, val_len,
               name_len, name, val_len, val);
    }
    printTable(hpack.getReqDynTbl());




    //2:
    pBuf = respBuf;
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST(":status"),
                           STR_TO_IOVEC_TEST("404"));
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("cache-control"),
                           STR_TO_IOVEC_TEST("public, max-age=1000"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("allow"),
                           STR_TO_IOVEC_TEST("*.*"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("from"),
                           STR_TO_IOVEC_TEST("123456@mymail.com"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("host"),
                           STR_TO_IOVEC_TEST("www.host.com"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("vary"),
                           STR_TO_IOVEC_TEST("wsdsdsdfdsfues1111"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("via"),
                           STR_TO_IOVEC_TEST("m"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("range"),
                           STR_TO_IOVEC_TEST("1111"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("my-test_key2"),
                           STR_TO_IOVEC_TEST("my-test-values22222222222222"));
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("my-test_key3333"), STR_TO_IOVEC_TEST("my-test-va3"));
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("my-test_key44"), STR_TO_IOVEC_TEST("my-test-value444"));
    displayHeader(respBuf, pBuf - respBuf);
    printTable(hpack.getRespDynTbl());


    /****************************
    * decHeader testing
    ****************************/
    pSrc = respBuf;
    bufEnd =  pBuf;
    while ((rc = hpack.decHeader(pSrc, bufEnd, out, out + sizeof(out), name_len,
                                 val_len)) > 0)
    {
        char *name = out;
        char *val = name + name_len;
        printf("[%d %d]%.*s: %.*s\n", name_len, val_len,
               name_len, name, val_len, val);
    }
    printTable(hpack.getReqDynTbl());

    //3:
    pBuf = respBuf;
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST(":status"),
                           STR_TO_IOVEC_TEST("307"));
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("cache-control"),
                           STR_TO_IOVEC_TEST("public, max-age=1000"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("allow"),
                           STR_TO_IOVEC_TEST("*.*.*.*"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("from"),
                           STR_TO_IOVEC_TEST("123456@mymail.com"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("host"),
                           STR_TO_IOVEC_TEST("www.host.com"));
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("my-test_key3333"), STR_TO_IOVEC_TEST("my-test-va3"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("vary"),
                           STR_TO_IOVEC_TEST("wsdsdsdfdsfues1111"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("via"),
                           STR_TO_IOVEC_TEST("mmmmm"));
    pBuf = hpack.encHeader(pBuf, respBufEnd, STR_TO_IOVEC_TEST("my-test_key2"),
                           STR_TO_IOVEC_TEST("my-test-values22222222222222"));
    pBuf = hpack.encHeader(pBuf, respBufEnd,
                           STR_TO_IOVEC_TEST("my-test_key44"), STR_TO_IOVEC_TEST("my-test-value444"));
    displayHeader(respBuf, pBuf - respBuf);
    printTable(hpack.getRespDynTbl());


    /****************************
    * decHeader testing
    ****************************/
    pSrc = respBuf;
    bufEnd =  pBuf;
    while ((rc = hpack.decHeader(pSrc, bufEnd, out, out + sizeof(out), name_len,
                                 val_len)) > 0)
    {
        char *name = out;
        char *val = name + name_len;
        printf("[%d %d]%.*s: %.*s\n", name_len, val_len,
               name_len, name, val_len, val);
    }
    printTable(hpack.getReqDynTbl());




}


#define LS_STR_TO_IOVEC(a) (a), (sizeof(a) -1)
static HpackHdrTbl_t g_HpackDynInitTable_t[] =
{
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("2145") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"1e0c-54feefd5-7bfd383f\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("31793") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"3235d-54feefd5-9d7c08af\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("407") },
    {LS_STR_TO_IOVEC("content-type"),    LS_STR_TO_IOVEC("text/css") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"6bc-54feefd5-a7725cbd\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("1884") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"1b5a-54feefd5-b6a3dc2a\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("2308") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"1aee-54feefd5-1d91a5e4\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("702") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"5f8-54feefd5-197a93f1\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("556") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"52b-54feefd5-e6075901\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("6913") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"5767-54feefd5-4a868698\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("6724") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"64de-54feefd5-fb73534f\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("2568") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"2530-54feefd5-cccfff57\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("973") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"b00-54feefd5-e48546d\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("709") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"6a4-54feefd5-82d8609d\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("6520") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"5b0d-54feefd5-44735f27\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("3954") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"22ac-54feefd5-600b05fd\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("32825") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"16bb3-54feefd5-d669865d\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("1055") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"a37-54feefd5-59e4760e\"") },
    {LS_STR_TO_IOVEC("date"),    LS_STR_TO_IOVEC("Tue, 10 Mar 2015 19:00:06 GMT") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("737") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"63d-54feefd5-c244a03a\"") },
    {LS_STR_TO_IOVEC("expires"),    LS_STR_TO_IOVEC("Tue, 17 Mar 2015 19:00:06 GMT") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("3205") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"37cf-54feefd5-10e8e54\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("6336") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"58d9-54feefd5-f0d60c72\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("2707") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"285b-54feefd5-2e2834bf\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("9050") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"87ed-54feefd5-741b49ef\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("7562") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"795a-54feefd5-9e535995\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("8780") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"9759-54feefd5-6c09a64d\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("1842") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"1288-54feefd5-51ae6c5a\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("9153") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"a2af-54feefd5-83098d2b\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("437") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"2eb-54feefd5-26eef95\"") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("37451") },
    {LS_STR_TO_IOVEC("content-type"),    LS_STR_TO_IOVEC("application/javascript") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"27df1-54feefd5-fe76c415\"") },
    {LS_STR_TO_IOVEC("expires"),    LS_STR_TO_IOVEC("Tue, 17 Mar 2015 19:00:05 GMT") },
    {LS_STR_TO_IOVEC("cache-control"),    LS_STR_TO_IOVEC("public, max-age=604800") },
    {LS_STR_TO_IOVEC("server"),    LS_STR_TO_IOVEC("LiteSpeed") },
    {LS_STR_TO_IOVEC("accept-ranges"),    LS_STR_TO_IOVEC("bytes") },
    {LS_STR_TO_IOVEC("date"),    LS_STR_TO_IOVEC("Tue, 10 Mar 2015 19:00:05 GMT") },
    {LS_STR_TO_IOVEC("vary"),    LS_STR_TO_IOVEC("Accept-Encoding") },
    {LS_STR_TO_IOVEC("content-encoding"),    LS_STR_TO_IOVEC("gzip") },
    {LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("5298") },
    {LS_STR_TO_IOVEC("content-type"),    LS_STR_TO_IOVEC("text/html") },
    {LS_STR_TO_IOVEC("last-modified"),    LS_STR_TO_IOVEC("Tue, 10 Mar 2015 13:21:25 GMT") },
    {LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("\"748f-54feefd5-dca65763\"") },
};



TEST(hapck_self_enc_dec_test_firefox_error)
{
    unsigned char respBuf[8192] = {0};
    unsigned char *respBufEnd = respBuf + 8192;
    Hpack hpack;
    int nCount = sizeof(g_HpackDynInitTable_t) / sizeof(HpackHdrTbl_t);
    int i;
    for (i = nCount - 1; i >= 0; --i)
    {
        int val_match;
        int staticTableIndex = Hpack::getStxTabId((char *)
                               g_HpackDynInitTable_t[i].name,
                               g_HpackDynInitTable_t[i].name_len,
                               (char *)g_HpackDynInitTable_t[i].val,
                               g_HpackDynInitTable_t[i].val_len,
                               val_match);

        if (staticTableIndex <= 0)
            printf("Error, not in static table. \n");

        hpack.getReqDynTbl().pushEntry((char *)g_HpackDynInitTable_t[i].name,
                                       g_HpackDynInitTable_t[i].name_len,
                                       (char *)g_HpackDynInitTable_t[i].val,
                                       g_HpackDynInitTable_t[i].val_len,
                                       staticTableIndex);

        hpack.getRespDynTbl().pushEntry((char *)g_HpackDynInitTable_t[i].name,
                                        g_HpackDynInitTable_t[i].name_len,
                                        (char *)g_HpackDynInitTable_t[i].val,
                                        g_HpackDynInitTable_t[i].val_len,
                                        staticTableIndex);

    }
    printTable(hpack.getReqDynTbl());


    char buf[] =
        "\x88\xF9\x64\x96\xDF\x69\x7E\x94\x0B\xAA\x68\x1D\x8A\x08\x01\x6D"
        "\x40\xBF\x70\x00\xB8\x07\x54\xC5\xA3\x7F\x62\x92\xFE\x42\x21\xBA"
        "\xB3\x6D\x4A\x52\xCB\x23\x6B\x0D\xE1\x3E\x17\x05\x2F\xF3\xFF\x04"
        "\x5F\x87\x35\x23\x98\xAC\x57\x54\xDF\x5C\x83\x69\xD7\x5B\x61\x96"
        "\xDF\x69\x7E\x94\x08\x14\xD0\x3B\x14\x10\x02\xDA\x81\x7E\xE0\x01"
        "\x70\x0E\xA9\x8B\x46\xFF\xFF\x01\xFF\x00";

    int rc;
    unsigned char *pSrc = (unsigned char *)buf;
    unsigned char *bufEnd = (unsigned char *)buf + 90;

    char out[2048];
    uint16_t name_len, val_len;

    unsigned char *pBuf = respBuf;
    respBufEnd = respBuf + 8192;

    while (pSrc < bufEnd)
    {
        rc = hpack.decHeader(pSrc, bufEnd, out, out + sizeof(out), name_len, val_len);
        CHECK(rc > 0);

        char *name = out;
        char *val = name + name_len;
        printf("[%d %d]%.*s: %.*s\n", name_len, val_len,
               name_len, name, val_len, val);

        pBuf = hpack.encHeader(pBuf, respBufEnd, (char *)name, name_len,
                               (char *)val, val_len);

        name_len = 1024;
        val_len = 1024;
    }

    displayHeader(respBuf, pBuf - respBuf);
    CHECK(memcmp(respBuf, buf, 90) == 0);
}


// TEST(hapck_dec_test_firefox_error2)
// {
//     unsigned char respBuf[8192] = {0};
//     unsigned char *respBufEnd = respBuf + 8192;
//     Hpack hpack;
//
//
//     char buf[] =
//     "\x88\x40\x89\xF2\xB5\x67\xF0\x5B\x0B\x22\xD1\xFA\x88\xD7\x8F\x5B"
//     "\x0D\xAE\xDA\xE2\x6B\x77\xB3\xF3\x2A\x45\x12\x0A\x84\x18\xF5\x40"
//     "\x17\xDF\x71\xC2\x08\x12\x0C\x12\x38\x30\x3D\x20\x63\x0C\x62\x8D"
//     "\xD2\x3C\xDB\x2E\x0A\x50\x7D\xA9\x58\xD3\x3C\x0C\x7D\xA8\x82\x92"
//     "\xDB\x0B\xF6\xA4\xE9\x4D\x67\xAA\x8F\x5F\x58\x85\xAE\xC3\x77\x1A"
//     "\x4B\x40\x8B\xF2\xB4\xB6\x0E\x92\xAC\x7A\xD2\x63\xD4\x8F\x89\xDD"
//     "\x0E\x8C\x1A\xB6\xE4\xC5\x93\x4F\x6C\x96\xDC\x34\xFD\x28\x17\x14"
//     "\xD0\x3F\x4A\x08\x01\x6D\x41\x02\xE3\x4F\xDC\x65\xB5\x31\x68\xDF"
//     "\x5F\x87\x35\x23\x98\xAC\x57\x54\xDF\x59\x2B\x69\x6E\x6C\x69\x6E"
//     "\x65\x3B\x20\x66\x69\x6C\x65\x6E\x61\x6D\x65\x3D\x22\x45\x6B\x72"
//     "\x61\x6E\x20\x41\x6C\xC4\xB1\x6E\x74\xC4\xB1\x73\xC4\xB1\x2E\x50"
//     "\x4E\x47\x22\x62\x8A\xFE\x42\xD3\x21\x6C\x2F\x09\xB7\xFF\x9F\x40"
//     "\x90\xF2\xB1\x0F\x52\x4B\x52\x56\x4F\xAA\xCA\xB1\xEB\x49\x8F\x52"
//     "\x3F\x85\xA8\xE8\xA8\xD2\xCB\x5C\x84\x6C\x00\x68\x00\x61\x96\xDC"
//     "\x34\xFD\x28\x17\x14\xD0\x3F\x4A\x08\x01\x6D\x41\x02\xE3\x4F\xDC"
//     "\x65\xB5\x31\x68\xDF\x52\x84\x8F\xD2\x4A\x8F\x76\x87\xCE\x64\x97"
//     "\x75\x65\x2C\x9F";
//     int rc;
//     unsigned char *pSrc = (unsigned char *)buf;
//     unsigned char *bufEnd = (unsigned char *)buf + sizeof( buf ) - 1;
//
//     AutoBuf autoBuf(2048);
//     uint16_t name_len, val_len;
//
//     unsigned char *pBuf = respBuf;
//     respBufEnd = respBuf + 8192;
//
//     while (pSrc < bufEnd)
//     {
//         rc = hpack.decHeader(pSrc, bufEnd, autoBuf, name_len, val_len);
//         CHECK (rc > 0);
//
//         char *name = autoBuf.begin();
//         char *val = name + name_len;
//         printf("[%d %d]%s: %s\n", name_len, val_len,
//                AutoStr2(name,name_len).c_str(),
//                AutoStr2(val, val_len).c_str());
//
//         pBuf = hpack.encHeader(pBuf, respBufEnd, (char *)name, name_len, (char *)val, val_len);
//
//         name_len = 1024;
//         val_len = 1024;
//     }
//
//     displayHeader(respBuf, pBuf - respBuf);
//     CHECK(memcmp(respBuf, buf, 90) ==0);
// }



/*
TEST(getDynTblId_testing)
{
    HpackDynTbl dynTbl0;
    HpackDynTbl_Forloop dynTbl1;
    int nCount = sizeof(g_HpackDynInitTable_t) / sizeof(HpackHdrTbl_t);
    int i;
    for ( i=nCount -1; i>=0; --i )
    {
        int val_match;
        int staticTableIndex = Hpack::getStxTabId((char *)g_HpackDynInitTable_t[i].name,
                                                       g_HpackDynInitTable_t[i].name_len,
                                                       (char *)g_HpackDynInitTable_t[i].val,
                                                       g_HpackDynInitTable_t[i].val_len,
                                                       val_match);

        if (staticTableIndex <= 0)
            printf("Error, not in static table. \n");

        dynTbl0.pushEntry((char *)g_HpackDynInitTable_t[i].name,
                                             g_HpackDynInitTable_t[i].name_len,
                                             (char *)g_HpackDynInitTable_t[i].val,
                                             g_HpackDynInitTable_t[i].val_len,
                                             staticTableIndex);

        dynTbl1.pushEntry((char *)g_HpackDynInitTable_t[i].name,
                                             g_HpackDynInitTable_t[i].name_len,
                                             (char *)g_HpackDynInitTable_t[i].val,
                                             g_HpackDynInitTable_t[i].val_len,
                                             staticTableIndex);
    }

    printf("\nSpeed test of getDynTblId:");
    printf("\nWith hashTable testing ");

    time_t t0 = time(NULL);
    char name[20];
    char val[20];
    int name_len =14;
    int val_len = 13;
    int val_matched;
    for (int k = 0; k < 8000 ; ++k)
    {
        for (i = 0; i< 97; ++i)
        {
            sprintf(name, "TESTHEADER%04d", i);
            sprintf(val, "TESTVALUE%04d", i);
            dynTbl0.getDynTabId((char *)name, name_len, (char *)val, val_len, val_matched, 0);
            dynTbl0.pushEntry(name, name_len, val, val_len, 0);

            sprintf(name, "TESTHEADER%04d", i+1);
            sprintf(val, "TESTVALUE%04d", i+1);
            dynTbl0.getDynTabId(name, name_len, val, val_len, val_matched, 0);

            sprintf(name, "TESTHEADER%04d", i+2);
            sprintf(val, "TESTVALUE%04d", i+2);
            dynTbl0.getDynTabId(name, name_len, val, val_len, val_matched, 0);
        }
    }
    time_t t1 = time(NULL);
    printf("(100 headers)----time: %ds\n", (int)(t1 - t0));

    printf("Without hashTable testing (use for loop) ");

    t0 = time(NULL);
    for (int k = 0; k < 8000 ; ++k)
    {
        for (i = 0; i< 97; ++i)
        {
            sprintf(name, "TESTHEADER%04d", i);
            sprintf(val, "TESTVALUE%04d", i);
            dynTbl1.getDynTabId(name, name_len, val, val_len, val_matched, 0);
            dynTbl1.pushEntry(name, name_len, val, val_len, 0);

            sprintf(name, "TESTHEADER%04d", i+1);
            sprintf(val, "TESTVALUE%04d", i+1);
            dynTbl1.getDynTabId(name, name_len, val, val_len, val_matched, 0);

            sprintf(name, "TESTHEADER%04d", i+2);
            sprintf(val, "TESTVALUE%04d", i+2);
            dynTbl1.getDynTabId(name, name_len, val, val_len, val_matched, 0);
        }
    }
    t1 = time(NULL);
    printf("(100 headers)----time: %ds\n", (int)(t1 - t0));

    //============================================
    printf("\nWith hashTable testing ");
    t0 = time(NULL);
    for (int k = 0; k < 4000 ; ++k)
    {
        for (i = 0; i< 997; ++i)
        {
            sprintf(name, "TESTHEADER%04d", i);
            sprintf(val, "TESTVALUE%04d", i);
            dynTbl0.getDynTabId((char *)name, name_len, (char *)val, val_len, val_matched, 0);
            dynTbl0.pushEntry(name, name_len, val, val_len, 0);

            sprintf(name, "TESTHEADER%04d", i+1);
            sprintf(val, "TESTVALUE%04d", i+1);
            dynTbl0.getDynTabId(name, name_len, val, val_len, val_matched, 0);

            sprintf(name, "TESTHEADER%04d", i+2);
            sprintf(val, "TESTVALUE%04d", i+2);
            dynTbl0.getDynTabId(name, name_len, val, val_len, val_matched, 0);
        }
    }
    t1 = time(NULL);
    printf("(1000 headers)----time: %ds\n", (int)(t1 - t0));

    printf("Without hashTable testing (use for loop) ");

    t0 = time(NULL);
    for (int k = 0; k < 4000 ; ++k)
    {
        for (i = 0; i< 997; ++i)
        {
            sprintf(name, "TESTHEADER%04d", i);
            sprintf(val, "TESTVALUE%04d", i);
            dynTbl1.getDynTabId(name, name_len, val, val_len, val_matched, 0);
            dynTbl1.pushEntry(name, name_len, val, val_len, 0);

            sprintf(name, "TESTHEADER%04d", i+1);
            sprintf(val, "TESTVALUE%04d", i+1);
            dynTbl1.getDynTabId(name, name_len, val, val_len, val_matched, 0);

            sprintf(name, "TESTHEADER%04d", i+2);
            sprintf(val, "TESTVALUE%04d", i+2);
            dynTbl1.getDynTabId(name, name_len, val, val_len, val_matched, 0);
        }
    }
    t1 = time(NULL);
    printf("(1000 headers)----time: %ds\n", (int)(t1 - t0));





    printf("\nhapck_self_enc_dec_test_firefox_error Done\n");


}*/


static HpackHdrTbl_t g_HpackStaticTableTset[] =
{
    { LS_STR_TO_IOVEC(":authority"),         LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC(":method"),            LS_STR_TO_IOVEC("GET") },
    { LS_STR_TO_IOVEC(":method"),            LS_STR_TO_IOVEC("POST") },
    { LS_STR_TO_IOVEC(":path"),              LS_STR_TO_IOVEC("/") },
    { LS_STR_TO_IOVEC(":path"),              LS_STR_TO_IOVEC("/index.html") },
    { LS_STR_TO_IOVEC(":scheme"),            LS_STR_TO_IOVEC("http") },
    { LS_STR_TO_IOVEC(":scheme"),            LS_STR_TO_IOVEC("https") },
    { LS_STR_TO_IOVEC(":status"),            LS_STR_TO_IOVEC("200") },
    { LS_STR_TO_IOVEC(":status"),            LS_STR_TO_IOVEC("204") },
    { LS_STR_TO_IOVEC(":status"),            LS_STR_TO_IOVEC("206") },
    { LS_STR_TO_IOVEC(":status"),            LS_STR_TO_IOVEC("304") },
    { LS_STR_TO_IOVEC(":status"),            LS_STR_TO_IOVEC("400") },
    { LS_STR_TO_IOVEC(":status"),            LS_STR_TO_IOVEC("404") },
    { LS_STR_TO_IOVEC(":status"),            LS_STR_TO_IOVEC("500") },
    { LS_STR_TO_IOVEC("accept-charset"),     LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("accept-encoding"),    LS_STR_TO_IOVEC("gzip, deflate") },
    { LS_STR_TO_IOVEC("accept-language"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("accept-ranges"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("accept"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("access-control-allow-origin"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("age"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("allow"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("authorization"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("cache-control"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("content-disposition"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("content-encoding"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("content-language"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("content-length"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("content-location"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("content-range"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("content-type"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("cookie"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("date"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("etag"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("expect"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("expires"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("from"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("host"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("if-match"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("if-modified-since"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("if-none-match"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("if-range"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("if-unmodified-since"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("last-modified"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("link"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("location"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("max-forwards"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("proxy-authenticate"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("proxy-authorization"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("range"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("referer"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("refresh"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("retry-after"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("server"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("set-cookie"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("strict-transport-security"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("transfer-encoding"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("user-agent"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("vary"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("via"),    LS_STR_TO_IOVEC("") },
    { LS_STR_TO_IOVEC("www-authenticate"),    LS_STR_TO_IOVEC("") }
};

TEST(hapck_getStaticTableId)
{
    int count = sizeof(g_HpackStaticTableTset) / sizeof(HpackHdrTbl_t);
    CHECK(count == 61);

    int val_matched;
    int id;
    for (int i = 0; i < count; ++i)
    {
        id = Hpack::getStxTabId((char *)g_HpackStaticTableTset[i].name,
                                g_HpackStaticTableTset[i].name_len,
                                (char *)g_HpackStaticTableTset[i].val,
                                g_HpackStaticTableTset[i].val_len,
                                val_matched);
        CHECK(id == i + 1);
        if (i >= 1 && i <= 15 && i != 14)
            CHECK(val_matched == 1);
        else
            CHECK(val_matched == 0);
    }

    id = Hpack::getStxTabId((char *)":method", 7, (char *)"Get", 3,
                            val_matched);
    CHECK(id == 2);
    CHECK(val_matched == 0);

    id = Hpack::getStxTabId((char *)":method", 7, (char *)"GGG", 3,
                            val_matched);
    CHECK(id == 2);
    CHECK(val_matched == 0);

    id = Hpack::getStxTabId((char *)":method", 7, (char *)"gET", 3,
                            val_matched);
    CHECK(id == 2);
    CHECK(val_matched == 0);

    id = Hpack::getStxTabId((char *)":method", 7, (char *)"GETsss", 6,
                            val_matched);
    CHECK(id == 2);
    CHECK(val_matched == 0);

    id = Hpack::getStxTabId((char *)":method", 7, (char *)"GETsss", 3,
                            val_matched);
    CHECK(id == 2);
    CHECK(val_matched == 1);

    id = Hpack::getStxTabId((char *)":method", 7, (char *)"POST", 4,
                            val_matched);
    CHECK(id == 3);
    CHECK(val_matched == 1);

    id = Hpack::getStxTabId((char *)":status", 7, (char *)"POST", 4,
                            val_matched);
    CHECK(id == 8);
    CHECK(val_matched == 0);

    id = Hpack::getStxTabId((char *)":status", 7, (char *)"2000", 4,
                            val_matched);
    CHECK(id == 8);
    CHECK(val_matched == 0);

    printf("hapck_getStaticTableId DOne.\n");
}

static bool
all_set_to (unsigned const char *buf, size_t bufsz, unsigned char val)
{
    unsigned n, count = 0;
    for (n = 0; n < bufsz; ++n)
        count += buf[n] == val;
    return count == bufsz;
}

TEST(hpack_decode_limits)
{
    unsigned char comp[0x100], *end;
    unsigned char *src;
    char out[0x100];
    Hpack hpack;
    uint16_t name_len, val_len;
    int s;
    unsigned enough[] = { 33, 34, 40, 50, 100, };
    unsigned not_enough[] = { 32, 31, 30, 10, 1, 0, };
    unsigned n;

    end = hpack.encHeader(comp, comp + sizeof(comp),
        (char *) "some-header-name", 16, (char *) "some-header-value", 17, 0);

    for (n = 0; n < sizeof(enough) / sizeof(enough[0]); ++n)
    {
        memset(out, 0xFA, sizeof(out));
        src = comp;
        s = hpack.decHeader(src, end, out, out + enough[n],
                                name_len, val_len);
        CHECK_EQUAL(1, s);
        CHECK_EQUAL(src, end);
        CHECK_EQUAL(16, name_len);
        CHECK_EQUAL(17, val_len);
        CHECK_EQUAL(0, memcmp(out, "some-header-namesome-header-value", 33));
        CHECK(all_set_to((unsigned char *) out + enough[n],
                                        sizeof(out) - enough[n], 0xFA));
    }

    for (n = 0; n < sizeof(not_enough) / sizeof(not_enough[0]); ++n)
    {
        memset(out, 0xFA, sizeof(out));
        src = comp;
        s = hpack.decHeader(src, end, out, out + not_enough[n],
                                name_len, val_len);
        CHECK(s < 0);
        CHECK(all_set_to((unsigned char *) out + not_enough[n],
                                    sizeof(out) - not_enough[n], 0xFA));
    }
}

#endif
