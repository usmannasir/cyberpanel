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
#ifndef LSIAPI_H
#define LSIAPI_H
#include <ls.h>

#define LSIAPI extern "C"



template< class T >
class THash;
class LsiModuleData;

typedef struct gdata_key_s
{
    char *key_str;
    int key_str_len;
} gdata_key_t;

typedef struct gdata_item_s
{
    gdata_key_t key;          //Need to deep copy the original buffer
    void *value;
    time_t tmcreate;
    time_t tmexpire;        //Create time + TTL = expird time
    time_t tmaccess;        //For not checking file too often
    lsi_datarelease_pf release_cb;
} gdata_item_t;

typedef  THash<gdata_item_t *> GDataHash;

typedef struct lsi_gdata_cont_s
{
    gdata_key_t key;          //Need to deep copy the original buffer
    GDataHash *container;
    time_t tmcreate;
    int type;
} lsi_gdata_cont_t;

typedef  THash<lsi_gdata_cont_t *> GDataContainer;
//extern GDataContainer *gLsiGDataContHashT[];


class LsiapiBridge
{
public:
    LsiapiBridge() {};
    ~LsiapiBridge() {};

    static lsi_api_t  g_lsiapiFunctions;
    //static GDataContainer *g_aGDataContainer[LSI_CONTAINER_COUNT];


    static int initLsiapi();
    static void uninitLsiapi();
    //static void checkExpiredGData();
    static void releaseModuleData(int level, LsiModuleData *pData);
    static lsi_api_t *getLsiapiFunctions()
    { return &LsiapiBridge::g_lsiapiFunctions; };

};


#endif // LSIAPI_H
