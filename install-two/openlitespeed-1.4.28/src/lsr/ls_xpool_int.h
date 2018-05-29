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
