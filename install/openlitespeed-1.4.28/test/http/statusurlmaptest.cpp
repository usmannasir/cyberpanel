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


#include "statusurlmaptest.h"
#include <http/statusurlmap.h>
#include <util/autostr.h>
#include "unittest-cpp/UnitTest++.h"


TEST(StatusUrlMapTest_test)
{
    StatusUrlMap map1;
    int i;
    for (i = SC_300; i < SC_END; ++i)
        CHECK(map1.getUrl(i) == NULL);
    for (i = 300; i < 309; ++i)
        CHECK(map1.setStatusUrlMap(i, "/url3xx") == 0);
    for (i = 400; i < 425; ++i)
        CHECK(map1.setStatusUrlMap(i, "/url4xx") == 0);
    for (i = 500; i < 511; ++i)
        CHECK(map1.setStatusUrlMap(i, "/url5xx") == 0);

    for (i = SC_300; i < SC_400; ++i)
        CHECK(strcmp(map1.getUrl(i)->c_str(), "/url3xx") == 0);
    for (i = SC_400; i < SC_500; ++i)
        CHECK(strcmp(map1.getUrl(i)->c_str(), "/url4xx") == 0);
    for (i = SC_500; i < SC_END; ++i)
        CHECK(strcmp(map1.getUrl(i)->c_str(), "/url5xx") == 0);
    CHECK(map1.setStatusUrlMap(100, "/url100") == 0);
    CHECK(map1.setStatusUrlMap(299, "/url299") == -1);
    CHECK(map1.setStatusUrlMap(309, "/url309") == -1);
    CHECK(map1.setStatusUrlMap(399, "/url308") == -1);
    CHECK(map1.setStatusUrlMap(425, "/url418") == -1);
    CHECK(map1.setStatusUrlMap(499, "/url499") == -1);
    CHECK(map1.setStatusUrlMap(511, "/url506") == -1);

}

#endif
