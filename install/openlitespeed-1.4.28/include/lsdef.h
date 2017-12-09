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
#ifndef _LSDEF_H_
#define _LSDEF_H_

#define __STDC_FORMAT_MACROS

#include <stddef.h>
#include <inttypes.h>
#include <string.h>


#define LS_OK       0
#define LS_FAIL     (-1)

#define LS_AGAIN    1
#define LS_DONE     0

#define LS_TRUE     1
#define LS_FALSE    0

#define LS_NO_COPY_ASSIGN(T) \
    private: \
    T(const T&);               \
    void operator=(const T&);

#define LS_ZERO_FILL(x, y)     memset(&x, 0, (char *)(&y+1) - (char *)&x)

#define ls_inline           static inline
#define ls_always_inline    static inline __attribute__((always_inline))
#define ls_attr_inline      __attribute__((always_inline))


#endif //_LSDEF_H_
