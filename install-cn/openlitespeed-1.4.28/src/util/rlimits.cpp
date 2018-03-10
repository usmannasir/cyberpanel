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
#include <util/rlimits.h>
#include <util/xmlnode.h>

#include <string.h>
#include <limits.h>

RLimits::RLimits()
{
    reset();
}


RLimits::~RLimits()
{
}


void RLimits::reset()
{
    memset(this, 0, sizeof(RLimits));
}


void RLimits::setDataLimit(rlim_t cur, rlim_t max)
{
#if defined(RLIMIT_AS) || defined(RLIMIT_DATA) || defined(RLIMIT_VMEM)
    if (cur)
        m_data.rlim_cur = cur;
    if (max)
        m_data.rlim_max = max;
#endif
}


void RLimits::setProcLimit(rlim_t cur, rlim_t max)
{
#if defined(RLIMIT_NPROC)
    if (cur)
        m_nproc.rlim_cur = cur;
    if (max)
        m_nproc.rlim_max = max;
#endif
}


void RLimits::setCPULimit(rlim_t cur, rlim_t max)
{
#if defined(RLIMIT_CPU)
    if (cur)
        m_cpu.rlim_cur = cur;
    if (max)
        m_cpu.rlim_max = max;
#endif
}


int RLimits::applyMemoryLimit() const
{
#if defined(RLIMIT_AS) || defined(RLIMIT_DATA) || defined(RLIMIT_VMEM)
    if (m_data.rlim_cur)
    {
        return
#if defined(RLIMIT_AS)
            setrlimit(RLIMIT_AS, &m_data);
#elif defined(RLIMIT_DATA)
            setrlimit(RLIMIT_DATA, &m_data);
#elif defined(RLIMIT_VMEM)
            setrlimit(RLIMIT_VMEM, &m_data);
#endif
    }
#endif
    return 0;
}


int RLimits::applyProcLimit() const
{
#if defined(RLIMIT_NPROC)
    if (m_nproc.rlim_cur)
        setrlimit(RLIMIT_NPROC, &m_nproc);
#endif
    return 0;
}


int RLimits::apply() const
{
    applyMemoryLimit();
    applyProcLimit();
#if defined(RLIMIT_NPROC)
    if (m_nproc.rlim_cur)
        setrlimit(RLIMIT_NPROC, &m_nproc);
#endif

#if defined(RLIMIT_CPU)
    if (m_cpu.rlim_cur)
        setrlimit(RLIMIT_CPU, &m_cpu);
#endif
    return 0;
}

