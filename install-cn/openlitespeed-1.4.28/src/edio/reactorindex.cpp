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
#include "reactorindex.h"
#include <edio/eventreactor.h>
#include <errno.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

ReactorIndex::ReactorIndex()
    : m_pIndexes(NULL)
    , m_capacity(0)
    , m_iUsed(0)
{
}

ReactorIndex::~ReactorIndex()
{
    deallocate();
}

int ReactorIndex::allocate(int capacity)
{
    ReactorHolder *pIndexes = (ReactorHolder *) realloc(m_pIndexes,
                              capacity * sizeof(ReactorHolder));
    if (!pIndexes)
        return LS_FAIL;
    if ((unsigned)capacity > m_capacity)
        memset(pIndexes + m_capacity, 0,
               sizeof(ReactorHolder) * (capacity - m_capacity));
    m_pIndexes = pIndexes;
    m_capacity = capacity;
    return LS_OK;
}

int ReactorIndex::deallocate()
{
    if (m_pIndexes)
        free(m_pIndexes);
    return LS_OK;
}


//#include <typeinfo>
//#include <unistd.h>
//#include <http/httplog.h>

void ReactorIndex::timerExec()
{
    unsigned int i;
    while (((m_iUsed) > 0) && (m_pIndexes[m_iUsed].m_pReactor == NULL))
        --m_iUsed;
    for (i = 0; i <= m_iUsed; ++i)
    {
        EventReactor *pReactor = m_pIndexes[i].m_pReactor;
        if (pReactor)
        {
            if (pReactor->getfd() == (int)i)
                pReactor->onTimer();
            else
            {
//                LS_ERROR( "[%d] ReactorIndex[%d]=%p, getfd()=%d, type: %s", getpid(), i, m_pIndexes[i], m_pIndexes[i]->getfd(),
//                typeid( *m_pIndexes[i] ).name() ));

                m_pIndexes[i].m_pReactor = NULL;
            }
        }
    }
}

