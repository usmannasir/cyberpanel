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
#ifndef PCUTIL_H
#define PCUTIL_H

#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
#include <sched.h>
# define SET_AFFINITY(pid, size, mask) sched_setaffinity(0, size, mask)
# define GET_AFFINITY(pid, size, mask) sched_getaffinity(0, size, mask)

#elif defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__)
#include <mach/mach_init.h>
#include <mach/thread_policy.h>
#include <sys/sysctl.h>
#define cpu_set_t thread_affinity_policy_data_t
#define CPU_SET(cpu_id, new_mask) \
    (*(new_mask)).affinity_tag = (cpu_id + 1)
#define CPU_ZERO(new_mask)                 \
    (*(new_mask)).affinity_tag = THREAD_AFFINITY_TAG_NULL
#define SET_AFFINITY(pid, size, mask)       \
    thread_policy_set(mach_thread_self(), THREAD_AFFINITY_POLICY, mask, \
                      THREAD_AFFINITY_POLICY_COUNT)

#else //__FreeBSD__ and others
//#if (defined(__FreeBSD__) && (__FreeBSD_version >= 700110) )
#   include <sys/param.h>
#   include <sys/resource.h>
#   include <sys/cpuset.h>
#   define cpu_set_t cpuset_t
#   define SET_AFFINITY(pid, size, mask) \
    cpuset_setaffinity(CPU_LEVEL_WHICH, CPU_WHICH_TID, -1, size, mask)
#   define GET_AFFINITY(pid, size, mask) \
    cpuset_getaffinity(CPU_LEVEL_WHICH, CPU_WHICH_TID, -1, size, mask)

//# else
////#   error "This platform does not support GET_AFFINITY"
//#define LSWS_NO_SET_AFFINITY    1
//# endif /* __FreeBSD_version */
#endif //defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)


class PCUtil
{
    PCUtil();
    PCUtil(const PCUtil &rhs);
    ~PCUtil();
    void operator=(const PCUtil &rhs);
public:
    static int waitChildren();
    static int getNumProcessors();
    static void getAffinityMask(int iCpuCount, int iProcessNum,
                                int iNumCoresToUse, cpu_set_t *_mask);
    static int setCpuAffinity(cpu_set_t *mask);
    static void setCpuAffinityAll();

private:
    static int          s_nCpu;
    static cpu_set_t    s_maskAll;



};

#endif
