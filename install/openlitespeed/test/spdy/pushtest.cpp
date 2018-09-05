/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#include "unittest-cpp/UnitTest++.h"
#include <stdlib.h>
#include <http/httpvhost.h>
#include <http/httpsession.h>


TEST(VHOST_URL_HASH)
{
    HttpVHost *vhost = new HttpVHost("testhost");
    const char *url = "http://test.com/";
    
    int id = vhost->getIdBitOfUrl(url);
    CHECK(id == -1);
    
    int id1 = vhost->addUrlToUrlIdHash(url);
    CHECK(id1 == 0);
    id = vhost->getIdBitOfUrl(url);
    CHECK(id == id1);
    
    
    
    
    url = "http://test1.com/";
    id = vhost->getIdBitOfUrl(url);
    CHECK(id == -1);
    
    id1 = vhost->addUrlToUrlIdHash(url);
    CHECK(id1 == 1);
    id = vhost->getIdBitOfUrl(url);
    CHECK(id == id1);
    
    
    url = "http://test2.com/";
    id = vhost->getIdBitOfUrl(url);
    CHECK(id == -1);
    
    id1 = vhost->addUrlToUrlIdHash(url);
    CHECK(id1 == 2);
    id = vhost->getIdBitOfUrl(url);
    CHECK(id == id1);
    
    const char *s="abcdefghji";
    const char *s2="jklmnopqrest";
    char ss[3] = {0};
    
    for(int i=0; i<10; ++i)
    {
        for(int j=0; j<10; ++j)
        {
            ss[0] = s[i];
            ss[1] = s2[j];
            url = ss;
            id = vhost->getIdBitOfUrl(url);
            CHECK(id == -1);
            
            id1 = vhost->addUrlToUrlIdHash(url);
            id = vhost->getIdBitOfUrl(url);
            CHECK(id == id1);
        }
    }

}

TEST(SESSION_COOKIE)
{

 
}



#endif
