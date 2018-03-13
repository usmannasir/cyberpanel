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
#ifndef LSIADDONDATA_H
#define LSIADDONDATA_H


#include <stdlib.h>
#include <assert.h>


class LsiModuleData
{
private:
    LsiModuleData &operator=(const LsiModuleData &other);
    bool operator==(const LsiModuleData &other) const;
    LsiModuleData(const LsiModuleData &other);

public:
    LsiModuleData()
        : m_pData(NULL)
        , m_iCount(0)
    {}
    ~LsiModuleData()
    {
        if (m_pData)
            delete [] m_pData;
    }
    bool isDataInited() { return m_pData != NULL;   }
    bool initData(int count);

    void set(short _data_id, void *data)
    {
        if ((_data_id >= 0) && (_data_id < m_iCount))
            m_pData[_data_id] = data;
    }
    void *get(short _data_id) const
    {
        if ((_data_id >= 0) && (_data_id < m_iCount))
            return m_pData[_data_id];
        return NULL;
    }
    void reset()
    {
        for (int i = 0; i < m_iCount; ++i)
            assert((m_pData[i] == NULL)
                   && "Addon Module must release data when session finishes");
    }

protected:
    void    **m_pData;
    int     m_iCount;

};


#endif // LSIADDONDATA_H
