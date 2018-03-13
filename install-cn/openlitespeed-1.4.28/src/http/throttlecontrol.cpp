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
#include "throttlecontrol.h"
#include <http/httpdefs.h>
#include <main/configctx.h>

#include <assert.h>

ThrottleLimits ThrottleControl::s_default;

void ThrottleControl::resetQuotas()
{
    m_input.reset();
    m_output.reset();
    m_req[0].reset();
    m_req[1].reset();
    m_req[2].reset();
}


void ThrottleLimits::config(const XmlNode *pNode1,
                            const ThrottleLimits *pDefault,
                            ConfigCtx *pCurrentCtx)
{
    int outlimit = -1;
    int inlimit = -1;
    if ((pDefault == this) || (pDefault->getOutputLimit() != INT_MAX))
    {
        outlimit = ConfigCtx::getCurConfigCtx()->getLongValue(pNode1,
                   "outBandwidth", -1, INT_MAX, -1);
        inlimit = ConfigCtx::getCurConfigCtx()->getLongValue(pNode1, "inBandwidth",
                  -1, INT_MAX, -1);
        if (inlimit == -1)
            inlimit = outlimit;
        if (outlimit < 0)
            outlimit = inlimit = ConfigCtx::getCurConfigCtx()->getLongValue(pNode1,
                                 "throttleLimit", 0, INT_MAX, -1);
        if ((outlimit > 0) && (outlimit < INT_MAX - THROTTLE_UNIT))
        {
            outlimit =
                ((outlimit + THROTTLE_UNIT - 1) / THROTTLE_UNIT) * THROTTLE_UNIT;
            if (inlimit < INT_MAX - 1024)
                inlimit = (inlimit + 1023) & ~1023;
        }
        if (outlimit == -1)
        {
            if (pDefault != this)
            {
                outlimit = pDefault->getOutputLimit();
                inlimit = pDefault->getInputLimit();
            }
            else
            {
                outlimit = INT_MAX;
                inlimit = INT_MAX;
            }
        }
    }
    if (outlimit <= 0)
        outlimit = INT_MAX;
    if (inlimit <= 0)
        inlimit = INT_MAX;
    m_iOutput = outlimit;
    m_iInput = inlimit;
    int limit = ConfigCtx::getCurConfigCtx()->getLongValue(pNode1,
                "dynReqPerSec", 0, INT_MAX,
                pDefault->getDynReqLimit());
    if (limit == 0)
        limit = INT_MAX;
    m_iDynReq = limit;
    limit = ConfigCtx::getCurConfigCtx()->getLongValue(pNode1,
            "staticReqPerSec", 0, INT_MAX,
            pDefault->getStaticReqLimit());
    if (limit == 0)
        limit = INT_MAX;
    m_iStaticReq = limit;
}
