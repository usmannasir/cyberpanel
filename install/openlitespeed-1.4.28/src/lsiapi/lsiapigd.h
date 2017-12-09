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
#ifndef LSIAPILIB_GD_H
#define LSIAPILIB_GD_H
#include <lsiapi/lsiapi.h>
#include <util/ghash.h>

/**
 * @typedef lsi_serialize_pf
 * @brief The serializer callback function for the user global file data.
 * Must use malloc to get the buffer and return the buffer.
 * @since 1.0
 */
typedef char   *(*lsi_serialize_pf)(void *pObject, int *out_length);

/**
 * @typedef lsi_deserialize_pf
 * @brief The deserializer callback function for the user global file data.
 * Must use malloc to get the buffer and return the buffer.
 * @since 1.0
 */
typedef void   *(*lsi_deserialize_pf)(char *, int length);

void init_gdata_hashes();
void release_gdata_container(GDataHash *containerInfo);
void uninit_gdata_hashes();

void erase_gdata_elem(lsi_gdata_cont_t *containerInfo,
                      GDataHash::iterator iter);
LSIAPI void *get_gdata(lsi_gdata_cont_t *containerInfo, const char *key,
                       int key_len, lsi_datarelease_pf release_cb,
                       int renew_TTL, lsi_deserialize_pf deserialize_cb);
LSIAPI int delete_gdata(lsi_gdata_cont_t *containerInfo, const char *key,
                        int key_len);
LSIAPI int set_gdata(lsi_gdata_cont_t *containerInfo, const char *key,
                     int key_len, void *val, int TTL,
                     lsi_datarelease_pf release_cb, int force_update,
                     lsi_serialize_pf serialize_cb);
LSIAPI lsi_gdata_cont_t *get_gdata_container(int type, const char *key,
        int key_len);
LSIAPI int empty_gdata_container(lsi_gdata_cont_t *containerInfo);
LSIAPI int purge_gdata_container(lsi_gdata_cont_t *containerInfo);

#endif //LSIAPILIB_GD_H


