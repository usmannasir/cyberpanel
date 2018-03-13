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
#ifndef THROTTLECONTROL_H
#define THROTTLECONTROL_H


#include <lsdef.h>

#include <stddef.h>
#include <time.h>
#include <limits.h>

#define THROTTLE_MAX (INT_MAX/2)

class XmlNode;
class ConfigCtx;
class ThrottleUnit
{
    int     m_iLimit;
    int     m_iAvailable;
public:
    ThrottleUnit()
        : m_iLimit(THROTTLE_MAX)
        , m_iAvailable(THROTTLE_MAX)
    {}
    ~ThrottleUnit()          {}

    int     getAvail() const    {   return m_iAvailable;        }
    int     getLimit() const    {   return m_iLimit;            }
    void    reset()             {   m_iAvailable = m_iLimit;    }
    void    setLimit(int n)   {   m_iLimit = n;               }
    void    used(int n)       {   m_iAvailable -= n;          }
    void    adjustLimit(int n)
    {   m_iAvailable += (n - m_iLimit);   m_iLimit = (n > 0) ? n : THROTTLE_MAX;       }

};


class ThrottleLimits
{
    int m_iInput;
    int m_iOutput;
    int m_iStaticReq;
    int m_iDynReq;

public:
    ThrottleLimits()
        : m_iInput(INT_MAX)
        , m_iOutput(INT_MAX)
        , m_iStaticReq(INT_MAX)
        , m_iDynReq(INT_MAX)
    {}
    ~ThrottleLimits()   {}

    void setInputLimit(int n)     {   m_iInput = n;           }
    void setOutputLimit(int n)    {   m_iOutput = n ;         }
    void setStaticReqLimit(int n) {   m_iStaticReq = n  ;     }
    void setDynReqLimit(int n)    {   m_iDynReq = n  ;        }

    int getInputLimit() const       {   return m_iInput;        }
    int getOutputLimit() const      {   return m_iOutput;       }
    int getStaticReqLimit() const   {   return m_iStaticReq;    }
    int getDynReqLimit() const      {   return m_iDynReq;       }
    void config(const XmlNode *pNode1, const ThrottleLimits *pDefault,
                ConfigCtx *pCurrentCtx);
    LS_NO_COPY_ASSIGN(ThrottleLimits);
};


class ThrottleControl
{
private:
    /** indicates the maximum throughput in bytes per seconds.
     * <=0 disable throttle, >0 enable throttle, should be at least 4096 */
    static ThrottleLimits s_default;

    ThrottleUnit    m_input;
    ThrottleUnit    m_output;
    ThrottleUnit
    m_req[3]; //0 is static, 2 is the processors in use, 1 is the requests processed

public:
    ThrottleControl()       {}
    ~ThrottleControl()      {}
    int getISQuota() const          {   return m_input.getAvail();      }
    int getOSQuota() const          {   return m_output.getAvail();     }
    void setISLimit(int limit)      {   m_input.setLimit(limit);        }
    void setOSLimit(int limit)      {   m_output.setLimit(limit);       }

    void useISQuota(int used)       {   m_input.used(used);             }
    void useOSQuota(int used)       {   m_output.used(used);            }
    bool allowRead() const          {   return (m_input.getAvail() > 0);  }
    bool allowWrite() const         {   return (m_output.getAvail() > 0); }
    bool allowProcess(int dyn) const
    {   return (m_req[dyn].getAvail() > 0) && (!dyn || (m_req[2].getAvail() > 0));    }

    ThrottleUnit *getThrottleUnit(int dyn)
    {   return &m_req[dyn];   }

    void incReqProcessed(int dyn)
    {
        m_req[dyn].used(1);
        if (dyn)
            m_req[2].used(1);
    }

    void decDynReqProcessing()      {   m_req[2].used(-1);              }

    void resetQuotas();

    void setUnlimited()
    {
        m_input.setLimit(THROTTLE_MAX);
        m_output.setLimit(THROTTLE_MAX);
        m_req[0].setLimit(THROTTLE_MAX);
        m_req[1].setLimit(THROTTLE_MAX);
        m_req[2].setLimit(THROTTLE_MAX);
    }
    void adjustLimits(const ThrottleLimits *pLimits)
    {
        m_input.adjustLimit(pLimits->getInputLimit());
        m_output.adjustLimit(pLimits->getOutputLimit());
        m_req[0].adjustLimit(pLimits->getStaticReqLimit());
        m_req[1].adjustLimit(pLimits->getDynReqLimit());
        m_req[2].adjustLimit(pLimits->getDynReqLimit());
    }

    static ThrottleLimits *getDefault()    {   return &s_default;      }


};


#endif
