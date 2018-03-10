
#ifndef LS_SHM_H
#define LS_SHM_H
#include <stddef.h>
#include <stdint.h>
#include <time.h>

/**
 * @file
 * LiteSpeed Shared Memory Allocation, Hash and Lock
 */


#ifdef __cplusplus
extern "C" {
#endif


typedef struct ls_shm_s      ls_shm_t;
typedef struct ls_shmpool_s  ls_shmpool_t;
typedef struct ls_shmhash_s  ls_shmhash_t;


typedef uint32_t ls_shmoff_t;
typedef uint32_t lsi_hash_key_t;

/**
 * @typedef ls_shmhash_pf
 * @brief The hash callback function generates and returns a hash key.
 * @since 1.0
 */
typedef lsi_hash_key_t (*ls_shmhash_pf)(const void *, size_t len);

/**
 * @typedef ls_shmhash_vc_pf
 * @brief The hash compare callback function compares two hash keys.
 * @since 1.0
 */
typedef int (*ls_shmhash_vc_pf)(const void *pVal1, const void *pVal2,
                                size_t len);

/**
 * @def LSI_SHM_MAX_NAME_LEN
 * @brief Shared Memory maximum characters in name of Shared Memory Pool or Hash Table
 * (ls_shm_opengpool and ls_shmhash_init).
 * @since 1.0
 */
#define LSI_SHM_MAX_NAME_LEN    (11)

/**
 * @def LSI_SHM_MAX_ALLOC_SIZE
 * @brief Shared Memory maximum total memory allocatable (~2GB)
 * @since 1.0
 */
#define LSI_SHM_MAX_ALLOC_SIZE  (2000000000)

/**
 * @def LSI_SHM_INIT
 * @brief Shared Memory flag bit requesting initialization.
 * @since 1.0
 */
#define LSI_SHM_INIT    (0x0001)

/**
 * @def LSI_SHM_SETTOP
 * @brief Shared Memory flag bit requesting setting top of linked list.
 * @since 1.0
 */
#define LSI_SHM_SETTOP  (0x0002)

/**
 * @def LSI_SHM_CREATED
 * @brief Shared Memory flag bit indicating newly created.
 * @since 1.0
 */
#define LSI_SHM_CREATED (0x0001)

/**
 * @brief ls_shm_opengpool initializes a shared memory pool.
 * @details If the pool does not exist, a new one is created.
 *
 * @since 1.0
 *
 * @param[in] pName - the name of the shared memory pool.
 * This name should not exceed #LSI_SHM_MAX_NAME_LEN characters in length.
 * If NULL, the system default name and size are used.
 * @param[in] initSize - the initial size in bytes of the shared memory pool.
 * If 0, the system default size is used.  The shared memory size grows as needed.
 * The maximum total allocatable shared memory is defined by #LSI_SHM_MAX_ALLOC_SIZE.
 * @return a pointer to the Shared Memory Pool object, to be used with subsequent ls_shmpool_* functions.
 * @note ls_shm_opengpool is generally the first routine called to access the shared memory pool system.
 *   The handle returned is used in all related routines to access and modify shared memory.
 *   The user should always maintain data in terms of shared memory offsets,
 *   and convert to pointers only when accessing or modifying the data, since offsets
 *   to the data remain constant but pointers may change at any time if shared memory is remapped.
 * @code
 *
 ls_shmpool_t *pShmpool;
 ls_shmoff_t dataOffset;

 {
     char *ptr;

     ...

     pShmpool = ls_shm_opengpool( "SHMPool", 0 );
     if ( pShmpool == NULL )
         error;

     ...

     dataOffset = ls_shmpool_alloc( pShmpool, 16 );
     if ( dataOffset == 0 )
         error;
     ptr = (char *)ls_shmpool_off2ptr( pShmpool, dataOffset );
     if ( ptr == NULL )
         error;
     strcpy( ptr, "Hello World" );

     ...
 }

 {
     ...

     printf( "%s\n", (char *)ls_shmpool_off2ptr( pShmpool, dataOffset ) );
     ls_shmpool_free( pShmpool, dataOffset, 16 );

     ...
 }
 * @endcode
 * @see ls_shmpool_alloc, ls_shmpool_free, ls_shmpool_off2ptr
 */
ls_shmpool_t *ls_shm_opengpool(const char *pName, const size_t initSize);

/**
 * @brief ls_shmpool_alloc allocates a shared memory block from the shared memory pool.
 *
 * @since 1.0
 *
 * @param[in] pShmpool - a pointer to the Shared Memory Pool object (from ls_shm_opengpool).
 * @param[in] size - the size in bytes of the memory block to allocate.
 * @return the offset of the allocated memory in the pool, else 0 on error.
 * @note the allocated memory is uninitialized,
 * even if returned offsets are the same as in previous allocations.
 * @see ls_shm_opengpool, ls_shmpool_free, ls_shmpool_off2ptr
 */
ls_shmoff_t ls_shmpool_alloc(ls_shmpool_t *pShmpool, size_t size);

/**
 * @brief ls_shmpool_free frees a shared memory block back to the shared memory pool.
 *
 * @since 1.0
 *
 * @param[in] pShmpool - a pointer to the Shared Memory Pool object (from ls_shm_opengpool).
 * @param[in] offset - the offset of the memory block to free, returned from a previous call to ls_shmpool_alloc.
 * @param[in] size - the size of this memory block which MUST be the same as was allocated for this offset.
 * @return void.
 * @warning it is the responsibility of the user to ensure that offset and size are valid,
 *   that offset was returned from a previous call to ls_shmpool_alloc,
 *   and that size is the same block size used in the allocation.
 *   Bad things will happen with invalid parameters, which also includes calling ls_shmpool_free for an already freed block.
 * @see ls_shm_opengpool, ls_shmpool_alloc
 */
void ls_shmpool_free(ls_shmpool_t *pShmpool, ls_shmoff_t offset,
                     size_t size);

/**
 * @brief ls_shmpool_off2ptr converts a shared memory pool offset to a user space pointer.
 *
 * @since 1.0
 *
 * @param[in] pShmpool - a pointer to the Shared Memory Pool object (from ls_shm_opengpool).
 * @param[in] offset - an offset in the shared memory pool.
 * @return a pointer in the user's space for the shared memory offset, else NULL on error.
 * @note the user should always maintain data in terms of shared memory offsets,
 *   and convert to pointers only when accessing or modifying the data, since offsets
 *   to the data remain constant but pointers may change at any time if shared memory is remapped.
 * @warning it is the responsibility of the user to ensure that offset is valid.
 * @see ls_shm_opengpool, ls_shmhash_off2ptr
 */
uint8_t *ls_shmpool_off2ptr(ls_shmpool_t *pShmpool,
                            ls_shmoff_t offset);

#ifdef notdef
//helper functions for atomic operations on SHM data
void (*shm_atom_incr_int8)(ls_shmoff_t offset, int8_t  inc_by);
void (*shm_atom_incr_int16)(ls_shmoff_t offset, int16_t inc_by);
void (*shm_atom_incr_int32)(ls_shmoff_t offset, int32_t inc_by);
void (*shm_atom_incr_int64)(ls_shmoff_t offset, int64_t inc_by);
#endif

/**
 * @brief ls_shmhash_init initializes a shared memory hash table.
 * @details If the hash table does not exist, a new one is created.
 *
 * @since 1.0
 *
 * @param[in] pShmpool - a pointer to a Shared Memory Pool object (from ls_shm_opengpool).
 * If NULL, a Shared Memory Pool object with the name specified by pName is used.
 * @param[in] pName - the name of the hash table.
 * This name should not exceed #LSI_SHM_MAX_NAME_LEN characters in length.
 * If NULL, the system default name is used.
 * @param[in] initSize - the initial size (in entries/buckets) of the hash table index.
 * If 0, the system default number is used.
 * @param[in] hash_pf - a function to be used for hash key generation (optional).
 * If NULL, a default hash function is used.
 * @param[in] comp_pf - a function to be used for key comparison (optional).
 * If NULL, the default compare function is used (strcmp(3)).
 * @return a pointer to the Shared Memory Hash Table object, to be used with subsequent ls_shmhash_* functions.
 * @note shm_hash_init initializes the hash table system after a shared memory pool has been initialized.
 *   The handle returned is used in all related routines to access and modify shared memory.
 *   The user should always maintain data in terms of shared memory offsets,
 *   and convert to pointers only when accessing or modifying the data, since offsets
 *   to the data remain constant but pointers may change at any time if shared memory is remapped.
 * @code
 *
 ls_shmpool_t *pShmpool;
 ls_shmhash_t *pShmhash;
 char myKey[] = "myKey";
 ls_shmoff_t valOffset;

 {
     int valLen;
     char *valPtr;

     ...

     pShmpool = ls_shm_opengpool( "SHMPool", 0 );
     if ( pShmpool == NULL )
         error;
     pShmhash = ls_shmhash_open( pShmpool, "SHMHash", 0, NULL, NULL );
     if ( pShmhash == NULL )
         error;

     ...

     valOffset = ls_shmhash_find(
         pShmhash, (const uint8_t *)myKey, sizeof(myKey) - 1, &valLen );
     if ( valOffset == 0 )
         error;
     valPtr = (char *)ls_shmhash_off2ptr( pShmhash, valOffset );
     if ( valPtr == NULL )
         error;
     printf( "[%.*s]\n", valLen, valPtr );    // if values are printable characters

     ...
 }
 * @endcode
 * @see ls_shm_opengpool, ls_shmhash_insert, ls_shmhash_find, ls_shmhash_get, ls_shmhash_set, ls_shmhash_update, ls_shmhash_clear
 */
ls_shmhash_t *ls_shmhash_open(ls_shmpool_t *pShmpool,
                              const char *pName, size_t initSize, ls_shmhash_pf hash_pf,
                              ls_shmhash_vc_pf comp_pf);

// set to new value regardless whether key is in table or not.
/**
 * @brief ls_shmhash_set sets a value in the hash table.
 * @details The new value is set whether or not the key currently exists in the table;
 *   i.e., either add a new entry or update an existing one.
 *
 * @since 1.0
 *
 * @param[in] pShmhash - a pointer to the Shared Memory Hash Table object (from ls_shmhash_init).
 * @param[in] pKey - the hash table entry key.
 * @param[in] keyLen - the length of the key at pKey.
 * @param[in] pValue - the new value to set in the hash table entry.
 * @param[in] valLen - the length of the value at pValue.
 * @return the offset to the entry value in the hash table, else 0 on error.
 * @see ls_shmhash_init, ls_shmhash_insert, ls_shmhash_find, ls_shmhash_get, ls_shmhash_update, ls_shmhash_off2ptr
 */
ls_shmoff_t ls_shmhash_set(ls_shmhash_t *pShmhash,
                           const uint8_t *pKey, int keyLen, const uint8_t *pValue, int valLen);

// key must NOT be in table already
/**
 * @brief ls_shmhash_insert adds a new entry to the hash table.
 * @details The key must NOT currently exist in the table.
 *
 * @since 1.0
 *
 * @param[in] pShmhash - a pointer to the Shared Memory Hash Table object (from ls_shmhash_init).
 * @param[in] pKey - the hash table entry key.
 * @param[in] keyLen - the length of the key at pKey.
 * @param[in] pValue - the new value to set in the hash table entry.
 * @param[in] valLen - the length of the value at pValue.
 * @return the offset to the entry value in the hash table, else 0 on error.
 * @see ls_shmhash_init, ls_shmhash_find, ls_shmhash_get, ls_shmhash_set, ls_shmhash_update, ls_shmhash_off2ptr
 */
ls_shmoff_t ls_shmhash_insert(ls_shmhash_t *pShmhash,
                              const uint8_t *pKey, int keyLen, const uint8_t *pValue, int valLen);

// key must be in table already
/**
 * @brief ls_shmhash_update updates a value in the hash table.
 * @details The key MUST currently exist in the table.
 *
 * @since 1.0
 *
 * @param[in] pShmhash - a pointer to the Shared Memory Hash Table object (from ls_shmhash_init).
 * @param[in] pKey - the hash table entry key.
 * @param[in] keyLen - the length of the key at pKey.
 * @param[in] pValue - the new value to set in the hash table entry.
 * @param[in] valLen - the length of the value at pValue.
 * @return the offset to the entry value in the hash table, else 0 on error.
 * @see ls_shmhash_init, ls_shmhash_insert, ls_shmhash_find, ls_shmhash_get, ls_shmhash_set, ls_shmhash_off2ptr
 */
ls_shmoff_t ls_shmhash_update(ls_shmhash_t *pShmhash,
                              const uint8_t *pKey, int keyLen, const uint8_t *pValue, int valLen);

/**
 * @brief ls_shmhash_find finds a value in the hash table.
 * @details The key MUST currently exist in the table.
 *
 * @since 1.0
 *
 * @param[in] pShmhash - a pointer to the Shared Memory Hash Table object (from ls_shmhash_init).
 * @param[in] pKey - the hash table entry key.
 * @param[in] keyLen - the length of the key at pKey.
 * @param[out] pvalLen - the length of the value for this entry.
 * @return the offset to the entry value in the hash table, else 0 on error.
 * @see ls_shmhash_init, ls_shmhash_insert, ls_shmhash_get, ls_shmhash_set, ls_shmhash_update, ls_shmhash_off2ptr
 */
ls_shmoff_t ls_shmhash_find(ls_shmhash_t *pShmhash,
                            const uint8_t *pKey, int keyLen, int *pvalLen);

/**
 * @brief ls_shmhash_get gets an entry from the hash table.
 * @details An entry is returned whether or not the key currently exists in the table;
 *   i.e., if the key exists, it is returned (find), else a new one is created (add).
 *
 * @since 1.0
 *
 * @param[in] pShmhash - a pointer to the Shared Memory Hash Table object (from ls_shmhash_init).
 * @param[in] pKey - the hash table entry key.
 * @param[in] keyLen - the length of the key at pKey.
 * @param[in,out] pvalLen - the length of the value for this entry.
 * @param[in,out] pFlags - various flags (parameters and returns).
 * - #LSI_SHM_INIT (in) - initialize (clear) entry IF and only if newly created.
 * - #LSI_SHM_SETTOP (in) - set entry to the top of the linked list.
 * - #LSI_SHM_CREATED (out) - a new entry was created.
 * @return the offset to the entry value in the hash table, else 0 on error.
 * @note the parameter specified by the user at pvalLen is used only if a new entry is created (#LSI_SHM_CREATED is set);
 *   else, the length of the existing entry value is returned through this pointer.
 *   This parameter cannot change the size of an existing entry.
 * @see ls_shmhash_init, ls_shmhash_insert, ls_shmhash_find, ls_shmhash_set, ls_shmhash_update, ls_shmhash_off2ptr
 */
ls_shmoff_t ls_shmhash_get(ls_shmhash_t *pShmhash,
                           const uint8_t *pKey, int keyLen, int *pvalLen, int *pFlags);

/**
 * @brief ls_shmhash_delete deletes/removes a hash table entry.
 *
 * @since 1.0
 *
 * @param[in] pShmhash - a pointer to the Shared Memory Hash Table object (from ls_shmhash_init).
 * @param[in] pKey - the hash table entry key.
 * @param[in] keyLen - the length of the key at pKey.
 * @return void.
 * @see ls_shmhash_init, ls_shmhash_clear
 */
void ls_shmhash_delete(ls_shmhash_t *pShmhash, const uint8_t *pKey,
                       int keyLen);

/**
 * @brief ls_shmhash_clear deletes all hash table entries for the given hash table.
 *
 * @since 1.0
 *
 * @param[in] pShmhash - a pointer to the Shared Memory Hash Table object (from ls_shmhash_init).
 * @return void.
 * @see ls_shmhash_init, ls_shmhash_delete
 */
void ls_shmhash_clear(ls_shmhash_t *pShmhash);

#ifdef notdef
int ls_shmhash_destroy(ls_shmhash_t *pShmhash);
#endif

/**
 * @brief ls_shmhash_off2ptr converts a hash table offset to a user space pointer.
 *
 * @since 1.0
 *
 * @param[in] pShmhash - a pointer to the Shared Memory Hash Table object (from ls_shmhash_init).
 * @param[in] offset - an offset in the shared memory hash table.
 * @return a pointer in the user's space for the shared memory offset, else NULL on error.
 * @note the user should always maintain data in terms of shared memory offsets,
 *   and convert to pointers only when accessing or modifying the data, since offsets
 *   to the data remain constant but pointers may change at any time if shared memory is remapped.
 * @warning it is the responsibility of the user to ensure that offset is valid.
 * @see ls_shmhash_init, ls_shmpool_off2ptr
 */
uint8_t *ls_shmhash_off2ptr(ls_shmhash_t *pShmhash,
                            ls_shmoff_t offset);


/*
 *   LiteSpeed SHM memory container
 */
ls_shm_t       *ls_shm_open(const char *shmname, size_t initialsize);
int             ls_shm_close(ls_shm_t
                             *shmhandle);    /* close connection */
int             ls_shm_destroy(ls_shm_t *shmhandle);  /* remove hash map */
ls_shmpool_t   *ls_shm_getpool(ls_shm_t *shmhandle, const char *poolname);

ls_shmoff_t     ls_shmpool_getreg(ls_shmpool_t *poolhandle,
                                  const char *name);
int             ls_shmpool_setreg(ls_shmpool_t *poolhandle,
                                  const char *name, ls_shmoff_t off);

int             ls_shmhash_close(ls_shmhash_t *hashhandle);
int             ls_shmhash_destroy(ls_shmhash_t *hashhandle);


ls_shmhash_t   *lsi_shmlruhash_open(ls_shmpool_t *poolhandle,
                                    const char *hash_table_name,
                                    size_t initialsize,
                                    ls_shmhash_pf hf,
                                    ls_shmhash_vc_pf vc,
                                    int mode);

/* Hash Shared memory access */
ls_shmoff_t     ls_shmhash_hdroff(ls_shmhash_t *hashhandle);
ls_shmoff_t     ls_shmhash_alloc2(ls_shmhash_t *hashhandle,
                                  size_t size);
void            ls_shmhash_release2(ls_shmhash_t *hashhandle,
                                    ls_shmoff_t key,
                                    size_t size);
/* Hash Element memory access */
int             ls_shmhash_setdata(ls_shmhash_t *hashhandle,
                                   ls_shmoff_t offVal, const uint8_t *value, int valuelen);
int             ls_shmhash_getdata(ls_shmhash_t *hashhandle,
                                   ls_shmoff_t offVal, ls_shmoff_t *pvalue, int cnt);
int             ls_shmhash_getdataptrs(ls_shmhash_t *hashhandle,
                                       ls_shmoff_t offVal, int (*func)(void *pData));
//int             ls_shmhash_trim(ls_shmhash_t *hashhandle,
//                                 time_t tmcutoff, int (*func)(LsShmHash::iterator iter, void *arg), void *arg);
int             ls_shmhash_check(ls_shmhash_t *hashhandle);
int             ls_shmhash_lock(ls_shmhash_t *hashhandle);
int             ls_shmhash_unlock(ls_shmhash_t *hashhandle);


/*
 * Hash table statistics
 */
//int             ls_shmhash_stat(ls_shmhash_t *hashhandle,
//                                 LsHashStat *phashstat);

/*  LOCK related
 *  All shared memory pool come with lock.
 *  get    = return first available lock
 *  remove = return the given lock
 */
//ls_shmlock_t   *ls_shmlock_get(ls_shm_t *handle);
//int             ls_shmlock_remove(ls_shm_t *handle, ls_shmlock_t *lock);



#ifdef __cplusplus
}
#endif

#endif





