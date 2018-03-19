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
#ifndef RLIMITS_H
#define RLIMITS_H


#include <sys/types.h>
#include <sys/time.h>
#include <sys/resource.h>
class XmlNode;
class ConfigCtx;

class RLimits
{
#if defined(RLIMIT_AS) || defined(RLIMIT_DATA) || defined(RLIMIT_VMEM)
    struct rlimit   m_data;
#endif
#if defined(RLIMIT_NPROC)
    struct rlimit   m_nproc;
#endif

#if defined(RLIMIT_CPU)
    struct rlimit   m_cpu;
#endif

    RLimits(const RLimits &rhs);
public:
    RLimits();
    ~RLimits();
    int apply() const;
    int applyMemoryLimit() const;
    int applyProcLimit() const;
    void setDataLimit(rlim_t cur, rlim_t max);
    void setProcLimit(rlim_t cur, rlim_t max);
#if defined(RLIMIT_NPROC)
    struct rlimit *getProcLimit() {    return &m_nproc;    }
#endif
    void setCPULimit(rlim_t cur, rlim_t max);
    void reset();

    void operator=(const RLimits &rhs)
    {
#if defined(RLIMIT_AS) || defined(RLIMIT_DATA) || defined(RLIMIT_VMEM)
        m_data = rhs.m_data;
#endif
#if defined(RLIMIT_NPROC)
        m_nproc = rhs.m_nproc;
#endif
#if defined(RLIMIT_CPU)
        m_cpu = rhs.m_cpu;
#endif
    }
};

#endif
