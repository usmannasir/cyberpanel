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
#define _GNU_SOURCE
#include "../include/ls.h"
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/**
 * Define the module name, MUST BE the same as .so file name;
 * i.e., if MNAME is testmodule, then the .so must be testmodule.so.
 *
 * How to test this sample
 * 1, Build the module, put reqobservmodule.so in $LSWS_HOME/modules
 * 2, Create a file with the bad words.
 * 3, Run curl and upload the file and access a dynamically generated page,
 * curl -F "file=@/home/.../filewithbadwords" http://localhost:8088/phpinfo.php
 * 4, If filewithbadwords contain at least one word in blockWords,
 *    will get 403, otherwise will get 200
 */

#define MNAME       reqobservmodule
lsi_module_t MNAME;

// Test if the request body contains below words, if so 403
const char *block_words[] =
{
    "badword1",
    "badword2",
    "badword3",
};

lsi_module_t MNAME;


static int has_bad_word(const char *s, size_t len)
{
    int i;
    int ret = 0;
    for (i = 0; i < sizeof(block_words) / sizeof(char *); ++i)
    {
        if (memmem(s, len, block_words[i], strlen(block_words[i])) != NULL)
        {
            ret = 1;
            break;
        }
    }
    return ret;
}


int check_req_whole_body(lsi_param_t *param)
{
    off_t offset = 0;
    const char *pbuf;
    int len = 0;
    int ret ;
    void *preqbodybuf = g_api->get_req_body_buf(param->session);
    while (!g_api->is_body_buf_eof(preqbodybuf, offset))
    {
        pbuf = g_api->acquire_body_buf_block(preqbodybuf, offset, &len);
        if (pbuf == NULL)
            break;
        // this is for demonstration purpose, if bad words is at
        // the block boundery, will not be detected.
        // you should do better in a real-world application.
        ret = has_bad_word(pbuf, len);
        g_api->release_body_buf_block(preqbodybuf, offset);
        if (ret != 0)
            return LSI_ERROR;
        offset += len;
    }
    return LSI_OK;
}


static int init_module(lsi_module_t *pModule)
{
    return 0;
}


static lsi_serverhook_t server_hooks[] =
{
    { LSI_HKPT_RCVD_REQ_BODY, check_req_whole_body, LSI_HOOK_EARLY, LSI_FLAG_ENABLED },
    LSI_HOOK_END   //Must put this at the end position
};

lsi_module_t MNAME =
{
    LSI_MODULE_SIGNATURE, init_module, NULL, NULL, "", server_hooks
};

