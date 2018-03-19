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
#ifndef HPACK_TEST_H
#define HPACK_TEST_H

#include "spdy/hpack.h"

class HpackDynTbl_Forloop : public HpackDynTbl
{
public:
    void popEntry()
    {
        DynTblEntry *pEntry = getEntryInternal(0);
        m_loopbuf.pop_front(ENTRYPSIZE);
        m_curCapacity -= pEntry->getEntrySize();
        delete pEntry;
    }

    void pushEntry(char *name, uint16_t name_len, char *val, uint16_t val_len,
                   uint32_t nameIndex)
    {
        DynTblEntry *pEntry = new DynTblEntry(name, name_len, val,
                                              val_len, nameIndex);
        m_loopbuf.append((char *)(&pEntry), ENTRYPSIZE);
        m_curCapacity += pEntry->getEntrySize();
        ++m_nextFlowId;
        removeOverflowEntries();
    }

    void reset()
    {
        int count = getEntryCount();
        for (int i = count - 1; i >= 0; --i)
            delete getEntryInternal(i);

        m_loopbuf.clear();
        m_curCapacity = 0;
        m_maxCapacity = INITIAL_DYNAMIC_TABLE_SIZE;
        m_nextFlowId = 0;
    }

    int getDynTabId(char *name, uint16_t name_len, char *value,
                    uint16_t value_len, int &val_matched, uint8_t stxTabId)
    {
        int id = 0 ;
        DynTblEntry *pEntry;
        int count = getEntryCount();
        for (int i = 0; i < count; ++i)
        {
            pEntry = getEntryInternal(i);
            if (value_len == pEntry->getValueLen()
                && memcmp(value, pEntry->getValue(), value_len) == 0
                && name_len == pEntry->getNameLen()
                && memcmp(name, pEntry->getName(), name_len) == 0)
            {
                val_matched = 1;
                id = i + 1 + HPACK_STATIC_TABLE_SIZE;
                break;
            }
            else if (stxTabId == 0) //If have stxTabId, so needn't go further
            {
                if (name_len == pEntry->getNameLen()
                    && memcmp(name, pEntry->getName(), name_len) == 0)
                {
                    id = i + 1 + HPACK_STATIC_TABLE_SIZE;
                    break;
                }
            }
        }
        return id;
    };
};

#endif
