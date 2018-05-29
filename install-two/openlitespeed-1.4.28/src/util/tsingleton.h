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
#ifndef TSINGLETON_H
#define TSINGLETON_H

//#ifdef _REENTRANT
//#endif
#ifdef _REENTRANT
#include <lsr/ls_lock.h>
#endif

#include <assert.h>
#include <stdlib.h>

template < class T >
class TSingleton
{
private:
    TSingleton(const TSingleton &rhs);
    void operator=(const TSingleton &rhs);
protected:
    TSingleton() {};
    ~TSingleton() {};
public:
    static T &getInstance()
    {
#ifdef LAZY_CREATE
        static T *s_pInstance = NULL;
        if (s_pInstance == NULL)
        {
#ifdef _REENTRANT
            {
                static ls_spinlock_t lock = LS_LOCK_AVAIL;
                ls_spinlock_lock(&lock);
                if (s_pInstance == NULL)
                    s_pInstance = new T();
                ls_spinlock_unlock(&lock);
            }
#else
            s_pInstance = new T();
#endif
            assert(s_pInstance != NULL);
        }
        return *s_pInstance;
#else  //LAZY_CREATE
        static T  s_instance;
        return s_instance;
#endif //LAZY_CREATE
    }

};


#endif
