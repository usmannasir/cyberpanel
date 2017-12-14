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
#include "lookupfd.h"

#include <errno.h>
#include <stdlib.h>
#include <string.h>


/** No descriptions */
int LookUpFD::allocate(int capacity)
{
    // Resize arrays indexed by fd if fd is beyond what we've seen.
    int *pn = (int *)realloc(m_pIntArray, capacity * sizeof(int));
    if (!pn)
        return ENOMEM;
    // Clear new elements
    //for (int i=m_iCapacity; i<n; i++)
    //  pn[i] = -1;
    memset(pn + m_iCapacity, -1,
           sizeof(int) * (capacity - m_iCapacity));
    m_pIntArray = pn;

    m_iCapacity = capacity;
    return LS_OK;

}
/** No descriptions */
int LookUpFD::deallocate()
{
    if (m_pIntArray)
    {
        free(m_pIntArray);
        m_pIntArray = NULL;
        m_iCapacity = 0;
    }
    return LS_OK;
}
/** No descriptions */
int LookUpFD::grow(int fd)
{
    // Resize arrays indexed by fd if fd is beyond what we've seen.
    int n = m_iCapacity * 2;
    if (n < fd + 10)
        n = fd + 10;
    return allocate(n);
}

