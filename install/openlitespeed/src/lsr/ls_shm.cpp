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
/*
 *   LiteSpeed SHM interface
 */
#include <lsr/ls_shm.h>

#include <shm/lsshmhash.h>
#include <shm/lsshmpool.h>

#include <assert.h>
#include <stdint.h>
#include <sys/types.h>
#include <unistd.h>

#ifdef __cplusplus
extern "C" {
#endif


/*
 *  LiteSpeed SHM CONTAINER
 */


ls_shm_t *ls_shm_open(const char *shmname, size_t initialsize)
{
    return LsShm::open(shmname, (LsShmXSize_t)initialsize);
}


int ls_shm_close(ls_shm_t *shmhandle)
{
    ((LsShm *)shmhandle)->close();
    return 0;
}


int ls_shm_destroy(ls_shm_t *shmhandle)
{
    ::unlink(((LsShm *)shmhandle)->fileName());
    ((LsShm *)shmhandle)->close();
    return 0;
}


/*
 *  SHM memory allocator
 */


ls_shmpool_t *ls_shm_getpool(ls_shm_t *shmhandle, const char *poolname)
{
    return ((LsShm *)shmhandle)->getNamedPool(poolname);
}


ls_shmpool_t *ls_shm_opengpool(const char *shmname, size_t initialsize)
{
    LsShm *pshm;
    if ((pshm = LsShm::open(shmname, (LsShmXSize_t)initialsize)) == NULL)
        return NULL;
    return pshm->getGlobalPool();
}


int ls_shmpool_close(ls_shmpool_t *poolhandle)
{
    ((LsShmPool *)poolhandle)->close();
    return 0;
}


int ls_shmpool_destroy(ls_shmpool_t *poolhandle)
{
    delete poolhandle;
    return 0;
}


ls_shmoff_t ls_shmpool_alloc(ls_shmpool_t *poolhandle, size_t size)
{
    int remap = 0;
    return ((LsShmPool *)poolhandle)->alloc2((LsShmSize_t)size, remap);
}


void ls_shmpool_free(
    ls_shmpool_t *poolhandle, ls_shmoff_t key, size_t size)
{
    ((LsShmPool *)poolhandle)->release2(key, (LsShmSize_t)size);
}


uint8_t *ls_shmpool_off2ptr(ls_shmpool_t *poolhandle, ls_shmoff_t key)
{
    return (uint8_t *)((LsShmPool *)poolhandle)->offset2ptr(key);
}


ls_shmoff_t ls_shmpool_getreg(ls_shmpool_t *poolhandle,
                              const char *name)
{
    LsShmReg *p_reg;
    return ((p_reg = ((LsShmPool *)poolhandle)->getShm()->findReg(
                         name)) == NULL) ?
           0 : p_reg->x_iValue;
}


int ls_shmpool_setreg(
    ls_shmpool_t *poolhandle, const char *name, ls_shmoff_t off)
{
    LsShmReg *p_reg = ((LsShmPool *)poolhandle)->getShm()->addReg(name);
    if ((p_reg == NULL) || (off <= 0))
        return LS_FAIL;
    p_reg->x_iValue = off;
    return 0;
}


/*
 *  LiteSpeed SHM HASH
 */


static void check_defaults(
    size_t *pinitialsize, ls_shmhash_pf *phf, ls_shmhash_vc_pf *pvc)
{
    if (*pinitialsize == 0)
        *pinitialsize = LSSHM_HASHINITSIZE;
    if (*phf == NULL)
        *phf = (ls_shmhash_pf)LsShmHash::hashString;
    if (*pvc == NULL)
        *pvc = (ls_shmhash_vc_pf)LsShmHash::compString;
}


ls_shmhash_t *ls_shmhash_open(ls_shmpool_t *poolhandle,
                              const char *hash_table_name,
                              size_t initialsize,
                              ls_shmhash_pf hf,
                              ls_shmhash_vc_pf vc)
{
    check_defaults(&initialsize, &hf, &vc);
    return ((LsShmPool *)poolhandle)->getNamedHash(
               hash_table_name, (LsShmSize_t)initialsize, hf, vc, 0);
}


ls_shmhash_t *lsi_shmlruhash_open(ls_shmpool_t *poolhandle,
                                  const char *hash_table_name,
                                  size_t initialsize,
                                  ls_shmhash_pf hf,
                                  ls_shmhash_vc_pf vc,
                                  int mode)
{
    check_defaults(&initialsize, &hf, &vc);
    return ((LsShmPool *)poolhandle)->getNamedHash(
               hash_table_name, (LsShmSize_t)initialsize, hf, vc, mode);
//     switch (mode)
//     {
//     case LSSHM_LRU_MODE2:
//     case LSSHM_LRU_MODE3:
//         return ((LsShmPool *)poolhandle)->getNamedHash(
//                    hash_table_name, (LsShmSize_t)initialsize, hf, vc, mode);
//     default:
//         return NULL;
//     }
}


int ls_shmhash_close(ls_shmhash_t *hashhandle)
{
    ((LsShmHash *)hashhandle)->close();
    return 0;
}


int ls_shmhash_destroy(ls_shmhash_t *hashhandle)
{
    delete hashhandle;
    return 0;
}


#ifdef notdef
ls_shmoff_t ls_shmhash_hdroff(ls_shmhash_t *hashhandle)
{
    return ((LsShmHash *)hashhandle)->lruHdrOff();
}
#endif


ls_shmoff_t ls_shmhash_alloc2(ls_shmhash_t *hashhandle, size_t size)
{
    int remap = 0;
    return ((LsShmHash *)hashhandle)->alloc2((LsShmSize_t)size, remap);
}


void ls_shmhash_release2(ls_shmhash_t *hashhandle,
                         ls_shmoff_t key,
                         size_t size)
{
    ((LsShmHash *)hashhandle)->release2(key, (LsShmSize_t)size);
}


uint8_t *ls_shmhash_off2ptr(ls_shmhash_t *hashhandle,
                            ls_shmoff_t key)
{
    return (uint8_t *)
           ((LsShmHash *)hashhandle)->offset2ptr((ls_shmoff_t)key);
}


ls_shmoff_t ls_shmhash_find(ls_shmhash_t *hashhandle,
                            const uint8_t *key, int keylen, int *retsize)
{
    return ((LsShmHash *)hashhandle)->find((const void *)key, keylen, retsize);
}


ls_shmoff_t ls_shmhash_get(ls_shmhash_t *hashhandle,
                           const uint8_t *key, int keylen, int *retsize, int *pFlag)
{
    return ((LsShmHash *)hashhandle)->get(
               (const void *)key, keylen, retsize, pFlag);
}


ls_shmoff_t ls_shmhash_set(ls_shmhash_t *hashhandle,
                           const uint8_t *key, int keylen,
                           const uint8_t *value, int valuelen)
{
    return ((LsShmHash *)hashhandle)->set(
               (const void *)key, keylen, (const void *)value, valuelen);
}


ls_shmoff_t ls_shmhash_insert(ls_shmhash_t *hashhandle,
                              const uint8_t *key, int keylen,
                              const uint8_t *value, int valuelen)
{
    return ((LsShmHash *)hashhandle)->insert(
               (const void *)key, keylen, (const void *)value, valuelen);
}


ls_shmoff_t ls_shmhash_update(ls_shmhash_t *hashhandle,
                              const uint8_t *key, int keylen,
                              const uint8_t *value, int valuelen)
{
    return ((LsShmHash *)hashhandle)->update(
               (const void *)key, keylen, (const void *)value, valuelen);
}


void ls_shmhash_delete(ls_shmhash_t *hashhandle,
                       const uint8_t *key, int keylen)
{
    ((LsShmHash *)hashhandle)->remove((const void *)key, keylen);
}


void ls_shmhash_clear(ls_shmhash_t *hashhandle)
{
    ((LsShmHash *)hashhandle)->clear();
}


// int ls_shmhash_setdata(ls_shmhash_t *hashhandle,
//                         ls_shmoff_t offVal, const uint8_t *value, int valuelen)
// {
//     return ((LsShmHash *)hashhandle)->setLruData(offVal, value, valuelen);
// }
//
//
// int ls_shmhash_getdata(ls_shmhash_t *hashhandle,
//                         ls_shmoff_t offVal, ls_shmoff_t *pvalue, int cnt)
// {
//     return ((LsShmHash *)hashhandle)->getLruData(offVal, pvalue, cnt);
// }
//
//
// int ls_shmhash_getdataptrs(ls_shmhash_t *hashhandle,
//                             ls_shmoff_t offVal, int (*func)(void *pData))
// {
//     return ((LsShmHash *)hashhandle)->getLruDataPtrs(offVal, func);
// }


int ls_shmhash_trim(ls_shmhash_t *hashhandle,
                    time_t tmcutoff, int (*func)(LsShmHash::iterator iter, void *arg),
                    void *arg)
{
    return ((LsShmHash *)hashhandle)->trim(tmcutoff, func, arg);
}


int ls_shmhash_check(ls_shmhash_t *hashhandle)
{
    return ((LsShmHash *)hashhandle)->checkLru();
}


int ls_shmhash_lock(ls_shmhash_t *hashhandle)
{
    return ((LsShmHash *)hashhandle)->lock();
}


int ls_shmhash_unlock(ls_shmhash_t *hashhandle)
{
    return ((LsShmHash *)hashhandle)->unlock();
}


/* Hash table statistic */
int ls_shmhash_stat(ls_shmhash_t *hashhandle, LsHashStat *phashstat)
{
    LsShmHash *pLsShmHash = (LsShmHash *)hashhandle;
    return pLsShmHash->stat(phashstat, NULL, 0);
}


// /*
//  *  LiteSpeed SHM Lock
//  */
// ls_shmlock_t *ls_shmlock_get(ls_shm_t *shmhandle)
// {
//     return ((LsShm *)shmhandle)->allocLock();
// }


int ls_shmlock_remove(ls_shm_t *shmhandle, ls_shmlock_t *lock)
{
    return ((LsShm *)shmhandle)->freeLock((ls_shmlock_t *)lock);
}


#ifdef __cplusplus
};
#endif

