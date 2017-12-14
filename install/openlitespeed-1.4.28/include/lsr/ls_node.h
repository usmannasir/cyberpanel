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
#ifndef LS_NODE_H
#define LS_NODE_H


/**
 * @file
 */


#ifdef __cplusplus
extern "C" {
#endif


typedef struct ls_nodei_s
{
    struct ls_nodei_s   *next;
} ls_nodei_t;

typedef struct ls_lfnodei_s
{
    volatile struct ls_lfnodei_s   *next;  /* internal use */
} ls_lfnodei_t;

typedef struct ls_lfnoden_s
{
    volatile struct ls_lfnoden_s   *next;  /* internal use */
    void                           *pobj;  /* user defined */
} ls_lfnoden_t;


#ifdef __cplusplus
}
#endif

#endif //LS_NODE_H

