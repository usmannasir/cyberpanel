/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2018  LiteSpeed Technologies, Inc.                 *
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
#ifndef LS_XPOOL_INT_H
#define LS_XPOOL_INT_H

typedef __link_t            ls_xblkctrl_t;

struct xpool_alink_s
{
    ls_xpool_header_t header;
    union
    {
        struct xpool_alink_s *next;
        char data[1];
    };
};

typedef struct xpool_alink_s        xpool_alink_t;

/**
 * @struct ls_qlist_s
 * @brief Session memory pool list management.
 */
struct xpool_qlist_s
{
    xpool_alink_t      *ptr;
    ls_lfstack_t        stack;
    ls_spinlock_t       lock;
};


//typedef struct ls_xpool_sb_s        ls_xpool_sb_t;
typedef struct xpool_qlist_s        xpool_qlist_t;

/**
 * @struct ls_xpool_s
 * @brief Session memory pool top level management.
 */
struct ls_xpool_s
{
    volatile ls_pool_blk_t      *psuperblk;
    xpool_qlist_t       smblk;
    xpool_qlist_t       lgblk;
    ls_xpool_bblk_t    *pbigblk;
    ls_xblkctrl_t      *pfreelists;
    int                 flag;
    int                 init;
    ls_spinlock_t       lock;
};

#endif /* LS_XPOOL_INT_H */
