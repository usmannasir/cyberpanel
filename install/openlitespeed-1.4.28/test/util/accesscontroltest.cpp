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

#include "accesscontroltest.h"
#include <util/accessdef.h>
#include <util/accesscontrol.h>
#include "unittest-cpp/UnitTest++.h"

TEST(AccessControlTest_testOverlap)
{
    AccessControl ac;
    ac.addSubNetControl("198.0.0.0/8", AC_DENY);
    CHECK(ac.hasAccess("198.255.0.1") == AC_DENY);
    CHECK(ac.hasAccess("198.0.0.1") == AC_DENY);
    ac.addSubNetControl("198.0.0.0/13", AC_DENY);
    int ret = ac.hasAccess("198.255.0.1");
    CHECK(ret == AC_DENY);
    ret = ac.hasAccess("198.0.0.1");
    CHECK(ret == AC_DENY);
}


TEST(AccessControlTest_test)
{
    AccessControl ac;
    ac.addIPControl("192.168.2.2", AC_DENY);
    ac.addIPControl("192.168.2.3", AC_ALLOW);
    ac.addIPControl("192.168.2.4", AC_DENY);
    ac.addIPControl("::FFFF:192.168.2.5t", AC_ALLOW);
    ac.addIPControl("192.168.2.6", AC_DENY);
    ac.addIPControl("192.168.12.7", AC_TRUST);
    ac.addIPControl("192.168.12.8", AC_DENY);
    ac.addIPControl("192.168.12.9", AC_ALLOW);
    ac.addIPControl("192.168.12.10", AC_DENY);
    ac.addIPControl("192.168.12.3", AC_ALLOW);
    CHECK(ac.hasAccess("192.168.2.2") == AC_DENY);
    CHECK(ac.hasAccess("192.168.2.3") == AC_ALLOW);
    CHECK(ac.hasAccess("192.168.2.4") == AC_DENY);
    CHECK(ac.hasAccess("192.168.2.5") == AC_TRUST);
    CHECK(ac.hasAccess("192.168.2.6") == AC_DENY);
    CHECK(ac.hasAccess("192.168.12.7") == AC_TRUST);
    CHECK(ac.hasAccess("192.168.12.8") == AC_DENY);
    CHECK(ac.hasAccess("192.168.12.9") == AC_ALLOW);
    CHECK(ac.hasAccess("192.168.12.10") == AC_DENY);
    CHECK(ac.hasAccess("192.168.12.3") == AC_ALLOW);
    ac.addIPControl("192.168.12.3", AC_DENY);
    CHECK(ac.hasAccess("192.168.12.3") == AC_DENY);
    ac.removeIPControl("192.168.12.3");
    CHECK(ac.hasAccess("192.168.12.3") == AC_ALLOW);

    CHECK(ac.hasAccess("192.168.1.3") == AC_ALLOW);
    CHECK(ac.hasAccess("192.168.10.3") == AC_ALLOW);
    CHECK(ac.addIPControl("0.1.2.3", AC_DENY) == 0);
    CHECK(ac.addIPControl("10.1000.2.3", AC_DENY) == -1);

    CHECK(!ac.addSubNetControl("192.168.2.0", "255.255.255.0", AC_DENY));
    CHECK(!ac.addSubNetControl("::FFFF:192.168.0.0", "112", AC_ALLOW));
    CHECK(!ac.addSubNetControl("192.0.0.0", "255.0.0.0", AC_DENY));

    CHECK(!ac.addSubNetControl("102.168.2.0", "255.255.255.0", AC_ALLOW));
    CHECK(!ac.addSubNetControl("102.168.0.0", "255.255.0.0", AC_DENY));
    CHECK(!ac.addSubNetControl("102.0.0.0", "255.0.0.0", AC_ALLOW));
    CHECK(!ac.addSubNetControl("192.167.12.3", "255.255.255.255", AC_ALLOW));
    CHECK(!ac.addSubNetControl("192.167.12.0", "255.255.255.0", AC_DENY));
    CHECK(!ac.addSubNetControl("192.167.0.0", "255.255.0.0", AC_ALLOW));

    CHECK(ac.hasAccess("192.168.2.3") == AC_ALLOW);
    CHECK(ac.hasAccess("192.168.2.8") == AC_DENY);
    CHECK(ac.hasAccess("192.168.1.3") == AC_ALLOW);

    CHECK(ac.hasAccess("192.167.1.3") == AC_ALLOW);
    CHECK(ac.addIPControl("192.167.1.3", AC_DENY) == 0);
    CHECK(ac.hasAccess("192.167.1.3") == AC_DENY);
    CHECK(ac.hasAccess("192.167.1.4") == AC_ALLOW);
    CHECK(!ac.addSubNetControl("192.167.0.0", "255.255.0.0", AC_DENY));
    CHECK(ac.hasAccess("192.167.1.4") == AC_DENY);

    CHECK(ac.hasAccess("102.168.1.3") == AC_DENY);
    CHECK(ac.hasAccess("102.168.2.3") == AC_ALLOW);
    CHECK(ac.hasAccess("102.167.1.3") == AC_ALLOW);

    ac.addSubNetControl("0.0.0.0", "0.0.0.0", AC_DENY);

    CHECK(ac.hasAccess("192.168.1.3") == AC_ALLOW);
    CHECK(ac.hasAccess("191.167.1.3") == AC_DENY);
    CHECK(ac.hasAccess("102.167.1.3") == AC_ALLOW);
    CHECK(ac.hasAccess("102.168.2.3") == AC_ALLOW);
    CHECK(ac.hasAccess("102.168.1.3") == AC_DENY);

    CHECK(ac.hasAccess("192.168.2.2") == AC_DENY);
    CHECK(ac.hasAccess("192.168.2.3") == AC_ALLOW);
    CHECK(ac.hasAccess("192.168.2.4") == AC_DENY);
    CHECK(ac.hasAccess("192.168.2.5") == AC_TRUST);
    CHECK(ac.hasAccess("192.168.2.6") == AC_DENY);
    CHECK(ac.hasAccess("192.168.12.7") == AC_TRUST);
    CHECK(ac.hasAccess("192.168.12.8") == AC_DENY);
    CHECK(ac.hasAccess("192.168.12.9") == AC_ALLOW);
    CHECK(ac.hasAccess("192.168.12.10") == AC_DENY);
    CHECK(ac.hasAccess("192.167.12.3") == AC_ALLOW);
    CHECK(ac.hasAccess("192.167.12.4") == AC_DENY);
    CHECK(ac.hasAccess("192.167.10.2") == AC_DENY);
    CHECK(ac.hasAccess("192.165.12.4") == AC_DENY);

    ac.addSubNetControl("40.23.*", AC_DENY);
    ac.addSubNetControl("40.23.21.0/24T", AC_ALLOW);
    ac.addSubNetControl("40.23.21.43", AC_DENY);
    ac.addSubNetControl("40.23.128.5/255.255.128.0", AC_ALLOW);

    CHECK(ac.hasAccess("40.23.5.1") == AC_DENY);
    CHECK(ac.hasAccess("40.23.21.10") == AC_TRUST);
    CHECK(ac.hasAccess("40.23.21.43") == AC_DENY);
    CHECK(ac.hasAccess("40.23.128.10") == AC_ALLOW);
    CHECK(ac.hasAccess("40.23.228.10") == AC_ALLOW);
    CHECK(ac.hasAccess("40.23.28.10") == AC_DENY);

    CHECK(ac.hasAccess("::1") == AC_ALLOW);
    ac.addSubNetControl("ALL", AC_DENY);
    CHECK(ac.hasAccess("::1") == AC_DENY);
    CHECK(ac.hasAccess("::2") == AC_DENY);
    ac.addSubNetControl("::", AC_ALLOW);
    CHECK(ac.hasAccess("::2") == AC_ALLOW);
    CHECK(ac.hasAccess("::1") == AC_ALLOW);
    ac.addSubNetControl("::1", AC_DENY);
    CHECK(ac.hasAccess("::1") == AC_DENY);
    CHECK(ac.hasAccess("::2") == AC_ALLOW);
    ac.addSubNetControl("::0f/120", AC_DENY);
    CHECK(ac.hasAccess("::2") == AC_DENY);
    ac.addSubNetControl("::0f/124", AC_ALLOW);
    CHECK(ac.hasAccess("::1") == AC_DENY);
    CHECK(ac.hasAccess("::2") == AC_ALLOW);

}

#endif
