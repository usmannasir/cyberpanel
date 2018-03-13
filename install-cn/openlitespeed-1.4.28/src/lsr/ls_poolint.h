#ifndef LS_POOLINT_H
#define LS_POOLINT_H


#include <stddef.h>


/**
 * @file
 */


#ifdef __cplusplus
extern "C" {
#endif


unsigned short ls_pool_cur_heaps();

unsigned short * ls_pool_get_multi(short *len);

#ifdef __cplusplus
}
#endif

#endif  /* LS_POOLINT_H */

