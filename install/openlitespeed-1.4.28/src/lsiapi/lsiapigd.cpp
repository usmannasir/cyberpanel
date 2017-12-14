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
#include "lsiapigd.h"

#include <lsdef.h>
#include <lsr/xxhash.h>
#include <main/mainserverconfig.h>
#include <util/datetime.h>
#include <util/gpath.h>

#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>


/**
 * @def LSI_MAX_FILE_PATH_LEN
 * @brief The max file path length.
 * @since 1.0
 */
#define LSI_MAX_FILE_PATH_LEN        4096




/**
 * @enum lsi_container_type
 * @brief Data container types.
 * @details Used in the API type parameter.
 * Determines whether the data is contained in memory or in a file.
 * @since 1.0
 */
enum lsi_container_type
{
    /**
     * Memory container type for user global data.
     */
    LSI_CONTAINER_MEMORY = 0,

    /**
     * File container type for user global data.
     */
    LSI_CONTAINER_FILE,

    /**
     * Placeholder.
     */
    LSI_CONTAINER_COUNT,
};

static hash_key_t  lsi_global_data_hash_fn(const void *val)
{
    const gdata_key_t *key = (const gdata_key_t *)val;
    const char *p = (const char *)key->key_str;
    int count = key->key_str_len;

    return XXH32((const char *)p, count, 0);
}


// static int  lsi_global_data_cmp(const void *pVal1, const void *pVal2)
// {
//     const gdata_key_t *pKey1 = (const gdata_key_t *)pVal1;
//     const gdata_key_t *pKey2 = (const gdata_key_t *)pVal2;
//     if (!pKey1 || !pKey2 || pKey1->key_str_len != pKey2->key_str_len)
//         return LS_FAIL;
//
//     return memcmp(pKey1->key_str, pKey2->key_str, pKey1->key_str_len);
// }


// void init_gdata_hashes()
// {
//     for (int i = 0; i < LSI_CONTAINER_COUNT; ++i)
//         LsiapiBridge::g_aGDataContainer[i] = new GDataContainer(30,
//                 lsi_global_data_hash_fn, lsi_global_data_cmp);
// }


// void release_gdata_container(GDataHash *containerInfo)
// {
//     GDataHash::iterator iter;
//     for (iter = containerInfo->begin(); iter != containerInfo->end();
//          iter = containerInfo->next(iter))
//     {
//         iter.second()->release_cb(iter.second()->value);
//         free(iter.second()->key.key_str);
//     }
// }


// void uninit_gdata_hashes()
// {
//     GDataContainer *pLsiGDataContHashT = NULL;
//     lsi_gdata_cont_t *containerInfo = NULL;
//     GDataContainer::iterator iter;
//     int i;
//     for (i = 0; i < LSI_CONTAINER_COUNT; ++i)
//     {
//         pLsiGDataContHashT = LsiapiBridge::g_aGDataContainer[i];
//         for (iter = pLsiGDataContHashT->begin(); iter != pLsiGDataContHashT->end();
//              iter = pLsiGDataContHashT->next(iter))
//         {
//             containerInfo = iter.second();
//             release_gdata_container(containerInfo->container);
//             free(containerInfo->key.key_str);
//             delete containerInfo->container;
//             free(containerInfo);
//         }
//         delete LsiapiBridge::g_aGDataContainer[i];
//     }
// }


/***
 *
 *
 * Below is the gdata functions
 * IF NEED TO UPDAT THE HASH FUNCTION, THEN THE BELOW FUNCTION NEED TO BE UPDATED!!!
 *
 *
 */
static int buildFileDataLocation(char *pBuf, int len,
                                 const gdata_key_t &key, const char *gDataTag, int type)
{
    long tmp = lsi_global_data_hash_fn(&key);
    unsigned char *achHash = (unsigned char *)&tmp;
    int n = snprintf(pBuf, len, "%sgdata/%s%d/%x%x/%x%x/%d.tmp",
                     MainServerConfig::getInstance().getServerRoot(),
                     gDataTag, type, achHash[0], achHash[1], achHash[2],
                     achHash[3], key.key_str_len);
    return n;
}


GDataHash::iterator get_gdata_iterator(GDataHash *container,
                                       const char *key, int key_len)
{
    gdata_key_t key_st = {(char *)key, key_len};
    GDataHash::iterator iter = container->find(&key_st);
    return iter;
}


//For memory type, file_path is useless
//renew_gdata_TTL will not update teh acc time and teh Acc time should be updated when accessing.
static void renew_gdata_TTL(GDataHash::iterator iter, int TTL, int type,
                            const char *file_path)
{
    gdata_item_t *pItem = iter.second();
    pItem->tmcreate = DateTime::s_curTime;
    pItem->tmexpire = TTL + pItem->tmcreate;

    //if type is file, modify it
    if (type == LSI_CONTAINER_FILE && file_path != NULL)
    {
        struct stat st;
        FILE *fp = fopen(file_path, "r+b");
        if (fp)
        {
            fwrite(&pItem->tmexpire, 1, sizeof(time_t), fp);
            fclose(fp);
            stat(file_path, &st);
            pItem->tmcreate = st.st_mtime;
        }
    }
}


void erase_gdata_elem(lsi_gdata_cont_t *containerInfo,
                      GDataHash::iterator iter)
{
    gdata_item_t *pItem = iter.second();
    if (containerInfo->type == LSI_CONTAINER_FILE)
    {
        char file_path[LSI_MAX_FILE_PATH_LEN] = {0};
        buildFileDataLocation(file_path, LSI_MAX_FILE_PATH_LEN, pItem->key, "i",
                              containerInfo->type);
        unlink(file_path);
    }

    if (pItem->release_cb)
        pItem->release_cb(pItem->value);
    free(pItem->key.key_str);
    free(pItem);
    containerInfo->container->erase(iter);
}


static FILE *open_file_to_write_n_check_dir(const char *file_path)
{
    FILE *fp = fopen(file_path, "wb");
    if (!fp)
    {
        GPath::createMissingPath((char *)file_path, 0700);
        fp = fopen(file_path, "wb");
    }
    return fp;
}


static int recover_file_gdata(lsi_gdata_cont_t *containerInfo,
                              const char *key, int key_len, const char *file_path,
                              GDataHash::iterator &iter, lsi_datarelease_pf release_cb,
                              lsi_deserialize_pf deserialize_cb)
{
    //If no deserialize presented, can not recover!
    if (!deserialize_cb)
        return LS_FAIL;

//    gdata_item_val_st *data = NULL;
    struct stat st;
    if (stat(file_path, &st) == -1)
        return LS_FAIL;

    int need_del_file = 0;
    time_t tmCur = DateTime::s_curTime;
    time_t tmExpire = tmCur;
    int fd = -1;

    if (containerInfo->tmcreate > st.st_mtime)
        need_del_file = 1;
    else
    {
        fd = open(file_path, O_RDONLY);
        if (fd != -1)
        {
            read(fd, &tmExpire, 4);
            if (tmExpire <= tmCur)
            {
                close(fd);
                need_del_file = 1;
            }
        }
        else
            need_del_file = 1;
    }

    //if tmExpire < st.st_mtime, it is an error, just clean it
    if (need_del_file || tmExpire < st.st_mtime)
    {
        unlink(file_path);
        return LS_FAIL;
    }

    GDataHash *pCont = containerInfo->container;
    gdata_item_t *pItem = NULL;
    if (iter == pCont->end())
    {
        char *p = (char *)malloc(key_len);
        if (!p)
        {
            close(fd);
            return LS_FAIL;
        }

        pItem = (gdata_item_t *)malloc(sizeof(gdata_item_t));
        memcpy(p, key, key_len);
        pItem->key.key_str = p;
        pItem->key.key_str_len = key_len;
        iter = pCont->insert(&pItem->key, pItem);
    }
    else
        pItem = iter.second();

    char *buf = NULL;
    off_t length = st.st_size;

    buf = (char *) mmap(NULL, length, PROT_READ, MAP_PRIVATE, fd, 0);
    if (buf == MAP_FAILED)
    {
        close(fd);
        return LS_FAIL;
    }

    void *val = deserialize_cb(buf + sizeof(time_t), length - sizeof(time_t));
    pItem->value = val;
    pItem->release_cb = release_cb;
    pItem->tmcreate = st.st_mtime;
    pItem->tmexpire = tmExpire;
    pItem->tmaccess = tmCur;

    munmap(buf, length);
    close(fd);
    return 0;
}


#define GDATA_FILE_NOCHECK_TIMEOUT      5

//Should use gdata_container_val_st instead of GDataHash
//cahe FILE mtim should always be NEWer or the same (>=) than cache buffer
LSIAPI void *get_gdata(lsi_gdata_cont_t *containerInfo, const char *key,
                       int key_len, lsi_datarelease_pf release_cb,
                       int renew_TTL, lsi_deserialize_pf deserialize_cb)
{
    GDataHash *pCont = containerInfo->container;
    GDataHash::iterator iter = get_gdata_iterator(pCont, key, key_len);
    gdata_item_t *pItem = NULL;
    int TTL = 0;
    time_t  tm = DateTime::s_curTime;
    char file_path[LSI_MAX_FILE_PATH_LEN] = {0};

    if (iter == pCont->end())
    {
        if (containerInfo->type == LSI_CONTAINER_MEMORY)
            return NULL;

        gdata_key_t key_st = {(char *)key, key_len};
        buildFileDataLocation(file_path, LSI_MAX_FILE_PATH_LEN, key_st, "i",
                              containerInfo->type);
        if (recover_file_gdata(containerInfo, key, key_len, file_path, iter,
                               release_cb, deserialize_cb) != 0)
        {
            unlink(file_path);
            return NULL;
        }
        pItem = iter.second();
        pItem->tmaccess = tm;
        return pItem->value;
    }

    //item exists
    pItem = iter.second();
    //container emptied
    if (pItem->tmcreate < containerInfo->tmcreate)
    {
        erase_gdata_elem(containerInfo, iter);
        return NULL;
    }

    TTL = pItem->tmexpire - pItem->tmcreate;
    if (containerInfo->type == LSI_CONTAINER_MEMORY)
    {
        if (renew_TTL)
            renew_gdata_TTL(iter, TTL, LSI_CONTAINER_MEMORY, NULL);
        pItem->tmaccess = tm;
        return pItem->value;
    }
    //if last access time is still same as tm
    if (pItem->tmaccess == tm)
    {
        pItem->tmaccess = tm;
        return pItem->value;
    }

    buildFileDataLocation(file_path, LSI_MAX_FILE_PATH_LEN, pItem->key, "i",
                          containerInfo->type);

    if (renew_TTL)
    {
        renew_gdata_TTL(iter, TTL, LSI_CONTAINER_FILE, file_path);
        pItem->tmaccess = tm;
        return pItem->value;
    }

    if (tm > GDATA_FILE_NOCHECK_TIMEOUT + pItem->tmaccess)
    {
        struct stat st;
        if (stat(file_path, &st) == -1)
        {
            erase_gdata_elem(containerInfo, iter);
            return NULL;
        }
        else if (pItem->tmcreate != st.st_mtime)
        {
            pItem->release_cb(pItem->value);
            if (recover_file_gdata(containerInfo, key, key_len, file_path,
                                   iter, release_cb, deserialize_cb) != 0)
            {
                erase_gdata_elem(containerInfo, iter);
                return NULL;
            }
        }
    }

    pItem->tmaccess = tm;
    return pItem->value;
}


LSIAPI int delete_gdata(lsi_gdata_cont_t *containerInfo, const char *key,
                        int key_len)
{
    GDataHash::iterator iter = get_gdata_iterator(containerInfo->container,
                               key, key_len);
    GDataHash *pCont = containerInfo->container;
    if (iter != pCont->end())
        erase_gdata_elem(containerInfo, iter);

    return 0;
}


LSIAPI int set_gdata(lsi_gdata_cont_t *containerInfo, const char *key,
                     int key_len, void *val, int TTL, lsi_datarelease_pf release_cb,
                     int force_update, lsi_serialize_pf serialize_cb)
{
    gdata_item_t *data = NULL;
    char file_path[LSI_MAX_FILE_PATH_LEN] = {0};
    GDataHash *pCont = containerInfo->container;
    GDataHash::iterator iter = get_gdata_iterator(pCont, key, key_len);

    if (iter != pCont->end())
    {
        if (!force_update)
            return 1;
        else
        {
            data = iter.second();
            //Release the prevoius value with the prevoius callback
            if (data->release_cb)
                data->release_cb(data->value);
        }
    }
    else
    {
        if (key_len <= 0)
            return LS_FAIL;

        char *p = (char *)malloc(key_len);
        if (!p)
            return LS_FAIL;

        data = (gdata_item_t *)malloc(sizeof(gdata_item_t));
        memcpy(p, key, key_len);
        data->key.key_str = p;
        data->key.key_str_len = key_len;
        iter = pCont->insert(&data->key, data);
    }

    data->value = val;
    data->release_cb = release_cb;
    data->tmcreate = DateTime::s_curTime;
    if (TTL < 0)
        TTL = 3600 * 24 * 365;
    data->tmexpire = TTL + data->tmcreate;
    data->tmaccess = data->tmcreate;

    if (containerInfo->type == LSI_CONTAINER_FILE)
    {
        buildFileDataLocation(file_path, LSI_MAX_FILE_PATH_LEN, data->key, "i",
                              containerInfo->type);
        FILE *fp = open_file_to_write_n_check_dir(file_path);
        if (!fp)
            return LS_FAIL;

        struct stat st;
        int length = 0;
        char *buf = serialize_cb(val, &length);
        fwrite(&data->tmexpire, 1, sizeof(time_t), fp);
        fwrite(buf, 1, length, fp);
        fclose(fp);
        free(buf); //serialize_cb MUST USE alloc, malloc or realloc to get memory, so here use free to release it

        stat(file_path, &st);
        iter.second()->tmcreate = st.st_mtime;
    }


    return 0;
}


LSIAPI lsi_gdata_cont_t *get_gdata_container(int type, const char *key,
        int key_len)
{
    return NULL; //Not in use any more
//     if ((type != LSI_CONTAINER_MEMORY  && type != LSI_CONTAINER_FILE)
//         || key_len <= 0 || key == NULL)
//         return NULL;
//
//     GDataContainer *pLsiGDataContHashT = LsiapiBridge::g_aGDataContainer[type];
//     lsi_gdata_cont_t *containerInfo = NULL;
//     char file_path[LSI_MAX_FILE_PATH_LEN] = {0};
//
//     //find if exist, otherwise create it
//     gdata_key_t key_st = {(char *)key, key_len};
//     GDataContainer::iterator iter = pLsiGDataContHashT->find(&key_st);
//     if (iter != pLsiGDataContHashT->end())
//         containerInfo = iter.second();
//     else
//     {
//         char *p = (char *)malloc(key_len);
//         if (!p)
//             return NULL;
//
//         GDataHash *pContainer = new GDataHash(30, lsi_global_data_hash_fn,
//                                               lsi_global_data_cmp);
//         memcpy(p, key, key_len);
//
//         time_t tm = DateTime::s_curTime;
//         containerInfo = (lsi_gdata_cont_t *)malloc(sizeof(lsi_gdata_cont_t));
//         containerInfo->key.key_str = p;
//         containerInfo->key.key_str_len = key_len;
//         containerInfo->container = pContainer;
//         containerInfo->tmcreate = tm;
//         containerInfo->type = type;
//         pLsiGDataContHashT->insert(&containerInfo->key, containerInfo);
//
//         //If cache file exist, use the ceate time recorded
//         buildFileDataLocation(file_path, LSI_MAX_FILE_PATH_LEN, containerInfo->key,
//                               "c", type);
//
//         FILE *fp = fopen(file_path, "rb");
//         if (fp)
//         {
//             fread((char *)&tm, 1, 4, fp);
//             fclose(fp);
//             containerInfo->tmcreate = tm;
//         }
//         else
//         {
//             fp = open_file_to_write_n_check_dir(file_path);
//             if (fp)
//             {
//                 fwrite((char *)&tm, 1, 4, fp);
//                 fclose(fp);
//             }
//         }
//     }
//     return containerInfo;
}


//empty will re-set the create time, and all items create time older than the container will be pruged when call purge_gdata_container
LSIAPI int empty_gdata_container(lsi_gdata_cont_t *containerInfo)
{
    containerInfo->tmcreate = DateTime::s_curTime;
    char file_path[LSI_MAX_FILE_PATH_LEN] = {0};
    time_t tm = DateTime::s_curTime;

    buildFileDataLocation(file_path, LSI_MAX_FILE_PATH_LEN, containerInfo->key,
                          "c", containerInfo->type);
    FILE *fp = open_file_to_write_n_check_dir(file_path);
    if (!fp)
        return LS_FAIL;
    fwrite((char *)&tm, 1, 4, fp);
    fclose(fp);
    return 0;
}


//purge will delete the item and also will remove the file if exist
LSIAPI int purge_gdata_container(lsi_gdata_cont_t *containerInfo)
{
    GDataHash *pCont = containerInfo->container;
    for (GDataHash::iterator iter = pCont->begin(); iter != pCont->end();
         iter = pCont->next(iter))
        erase_gdata_elem(containerInfo, iter);
    return 0;
}




