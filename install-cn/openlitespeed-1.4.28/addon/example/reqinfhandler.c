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

#include "../include/ls.h"

#include <lsr/ls_xpool.h>

#include <stdlib.h>
#include <string.h>
#include <openssl/md5.h>

/**
 * Define the module name, MUST BE the same as .so file name;
 * i.e., if MNAME is testmodule, then the .so must be testmodule.so.
 *
 * How to test this sample
 * 1, build it, put the file reqinfhandler.so in $LSWS_HOME/modules
 * 2, in web admin console configuration, enable this module
 * 3, visit http(s)://.../reqinfo(/echo|/md5|/upload) with/without request body
 */

#define MNAME       reqinfhandler
lsi_module_t MNAME;

static char testuri[] = "/reqinfo";

#define CONTENT_HEAD    "<html><head><title>Server request varibles</title></head><body>\r\n"
#define CONTENT_FORMAT  "<tr><td>%s</td><td>%s</td></tr>\r\n"
#define CONTENT_TAIL    "</body></html>\r\n"

typedef struct mydata_s
{
    int type;
    FILE *fp;
    MD5_CTX ctx;
    int req_body_len;           // length in "Content-Length"
    int rcvd_req_body_len;      // recved
    int rcvd_done;              // finished or due to connection error
    int resp_done;
} mydata_t;

// The following matches the index, DO NOT change the order
const char *req_array[] =
{
    "REMOTE_ADDR",
    "REMOTE_PORT",
    "REMOTE_HOST",
    "REMOTE_USER",
    "REMOTE_IDENT",
    "REQUEST_METHOD",
    "QUERY_STRING",
    "AUTH_TYPE",
    "PATH_INFO",
    "SCRIPT_FILENAME",
    "REQUEST_FILENAME",
    "REQUEST_URI",
    "DOCUMENT_ROOT",
    "SERVER_ADMIN",
    "SERVER_NAME",
    "SERVER_ADDR",
    "SERVER_PORT",
    "SERVER_PROTOCOL",
    "SERVER_SOFTWARE",
    "API_VERSION",
    "THE_REQUEST",
    "IS_SUBREQ",
    "TIME",
    "TIME_YEAR",
    "TIME_MON",
    "TIME_DAY",
    "TIME_HOUR",
    "TIME_MIN",
    "TIME_SEC",
    "TIME_WDAY",
    "SCRIPT_NAME",
    "CURRENT_URI",
    "REQUEST_BASENAME",
    "SCRIPT_UID",
    "SCRIPT_GID",
    "SCRIPT_USERNAME",
    "SCRIPT_GROUPNAME",
    "SCRIPT_MODE",
    "SCRIPT_BASENAME",
    "SCRIPT_URI",
    "ORG_REQ_URI",
    "HTTPS",
    "SSL_VERSION",
    "SSL_SESSION_ID",
    "SSL_CIPHER",
    "SSL_CIPHER_USEKEYSIZE",
    "SSL_CIPHER_ALGKEYSIZE",
    "SSL_CLIENT_CERT",
    "GEOIP_ADDR",
    "PATH_TRANSLATED",
};

// The following is used by name value, you can change the order
const char *env_array[] =
{
    "PATH",

    "REMOTE_ADDR",
    "REMOTE_PORT",
    "REMOTE_HOST",
    "REMOTE_USER",
    "REMOTE_IDENT",
    "REQUEST_METHOD",
    "QUERY_STRING",
    "AUTH_TYPE",
    "PATH_INFO",
    "SCRIPT_FILENAME",
    "REQUEST_FILENAME",
    "REQUEST_URI",
    "DOCUMENT_ROOT",
    "SERVER_ADMIN",
    "SERVER_NAME",
    "SERVER_ADDR",
    "SERVER_PORT",
    "SERVER_PROTOCOL",
    "SERVER_SOFTWARE",
    "API_VERSION",
    "THE_REQUEST",
    "IS_SUBREQ",
    "TIME",
    "TIME_YEAR",
    "TIME_MON",
    "TIME_DAY",
    "TIME_HOUR",
    "TIME_MIN",
    "TIME_SEC",
    "TIME_WDAY",
    "SCRIPT_NAME",
    "CURRENT_URI",
    "REQUEST_BASENAME",
    "SCRIPT_UID",
    "SCRIPT_GID",
    "SCRIPT_USERNAME",
    "SCRIPT_GROUPNAME",
    "SCRIPT_MODE",
    "SCRIPT_BASENAME",
    "SCRIPT_URI",
    "ORG_REQ_URI",
    "HTTPS",
    "SSL_VERSION",
    "SSL_SESSION_ID",
    "SSL_CIPHER",
    "SSL_CIPHER_USEKEYSIZE",
    "SSL_CIPHER_ALGKEYSIZE",
    "SSL_CLIENT_CERT",
    "GEOIP_ADDR",
    "PATH_TRANSLATED",
};

const char *reqhdr_array[] =
{
    "Accept",
    "Accept-Charset",
    "Accept-Encoding",
    "Accept-Language",
    "Accept-Datetime",
    "Authorization",
    "Cache-Control",
    "Connection",
    "Content-Type",
    "Content-Length",
    "Content-MD5",
    "Cookie",
    "Date",
    "Expect",
    "From",
    "Host",
    "Pragma",
    "Proxy-Authorization"
    "If-Match",
    "If-Modified-Since",
    "If-None-Match",
    "If-Range",
    "If-Unmodified-Since",
    "Max-Forwards",
    "Origin",
    "Referer",
    "User-Agent",
    "Range",
    "Upgrade",
    "Via",
    "X-Forwarded-For",
};


static int free_mydata(void *data)
{
    mydata_t *mydata = (mydata_t *)data;
    if (mydata != NULL)
    {
        // free (mydata); Do not need to free with session pool,
        //   will be freed at the end of the session.
        g_api->log(NULL, LSI_LOG_DEBUG, "#### reqinfomodule free_mydata\n");
    }
    return 0;
}


static int initdata(lsi_param_t *param)
{
    mydata_t *mydata = (mydata_t *)g_api->get_module_data(param->session,
                       &MNAME, LSI_DATA_HTTP);
    ls_xpool_t *pPool = g_api->get_session_pool(param->session);
    mydata = (mydata_t *)ls_xpool_alloc(pPool, sizeof(mydata_t));
    memset(mydata, 0, sizeof(mydata_t));
    g_api->log(NULL, LSI_LOG_DEBUG, "#### reqinfomodule initdata\n");
    g_api->set_module_data(param->session, &MNAME, LSI_DATA_HTTP,
                           (void *)mydata);
    return 0;
}


// 0:no body or no deal, 1,echo, 2: md5, 3, save to file
static int get_reqbody_dealertype(const lsi_session_t *session)
{
    char path[512];
    int n;
    if (g_api->get_req_content_length(session) > 0)
    {
        n = g_api->get_req_var_by_id(session, LSI_VAR_PATH_INFO, path, 512);
        if (n >= 5 && strncasecmp(path, "/echo", 5) == 0)
            return 1;
        else if (n >= 4 && strncasecmp(path, "/md5", 4) == 0)
            return 2;
        else if (n >= 7 && strncasecmp(path, "/upload", 7) == 0)
            return 3;
    }

    // All other cases, no deal
    return 0;
}


static inline void append(const lsi_session_t *session, const char *s, int n)
{
    if (n == 0)
        n = strlen(s);
    g_api->append_resp_body(session, (char *)s, n);
}


static int on_read(const lsi_session_t *session)
{
    unsigned char md5[16];
    char buf[8192];
    int ret, i;
    int readbytes = 0, written = 0;
    mydata_t *mydata = (mydata_t *)g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);
    if (mydata == NULL || mydata->type == 0)
    {
        g_api->end_resp(session);
        return 0;
    }

    while ((ret = g_api->read_req_body(session, buf, sizeof(buf))) > 0)
    {
        mydata->rcvd_req_body_len += ret;
        readbytes += ret;

        if (mydata->type == 1)
        {
            append(session, buf, ret);
            written += ret;
        }
        else if (mydata->type == 2)
            MD5_Update(&mydata->ctx, buf, ret);
        else
            fwrite(buf, 1, ret, mydata->fp);

        if (mydata->rcvd_req_body_len >= mydata->req_body_len)
        {
            mydata->rcvd_done = 1;
            break;
        }
    }
    if (ret == 0)
        mydata->rcvd_done = 1;

    if (mydata->rcvd_done == 1)
    {
        if (mydata->type == 2)
        {
            MD5_Final(md5, &mydata->ctx);
            for (i = 0; i < 16; ++i)
                sprintf(buf + i * 2, "%02X", md5[i]);
            append(session, "MD5 is<br>", 10);
            append(session, buf, 32);
            written += 42;
        }
        else if (mydata->type == 3)
        {
            if (mydata->fp != NULL)
            {
                fclose(mydata->fp);
                mydata->fp = NULL;
                append(session, "File uploaded.<br>", 18);
                written += 18;
            }
        }
        mydata->resp_done = 1;
    }

    if (written > 0)
        g_api->flush(session);
    g_api->set_handler_write_state(session, 1);
    //g_api->end_resp(session);
    return readbytes;
}


static int begin_process(const lsi_session_t *session)
{
#define VALMAXSIZE 4096
#define LINEMAXSIZE (VALMAXSIZE + 50)
    char val[VALMAXSIZE], line[LINEMAXSIZE] = {0};
    int n;
    int i;
    const char *p;
    char *buf;
    mydata_t *mydata = (mydata_t *)g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);
    ls_xpool_t *pPool = g_api->get_session_pool(session);

    //Create response body
    append(session, CONTENT_HEAD, 0);

    //Original request header
    n = g_api->get_req_raw_headers_length(session);
    buf = (char *)ls_xpool_alloc(pPool, n + 1);
    memset(buf, 0, n + 1);
    n = g_api->get_req_raw_headers(session, buf, n + 1);
    append(session, "Original request<table border=1><tr><td><pre>\r\n", 0);
    append(session, buf, n);
    append(session, "\r\n</pre></td></tr>\r\n", 0);
    ls_xpool_free(pPool, buf);

    append(session, "\r\n</table><br>Request headers<br><table border=1>\r\n",
           0);
    for (i = 0; i < sizeof(reqhdr_array) / sizeof(char *); ++i)
    {
        p = g_api->get_req_header(session, reqhdr_array[i],
                                  strlen(reqhdr_array[i]), &n);
        if ((p != NULL) && p[0] != 0 && n > 0)
        {
            memcpy(val, p, n);
            val[n] = '\0';
            n = snprintf(line, LINEMAXSIZE - 1, CONTENT_FORMAT, reqhdr_array[i],
                         val);
            append(session, line, n);
        }
    }


    append(session,
           "\r\n</table><br>Server req env<br><table border=1>\r\n", 0);
    //Server req env
    for (i = LSI_VAR_REMOTE_ADDR; i < LSI_VAR_COUNT; ++i)
    {
        n = g_api->get_req_var_by_id(session, i, val, VALMAXSIZE);
        if (n > 0)
        {
            val[n] = '\0';
            n = snprintf(line, LINEMAXSIZE - 1, CONTENT_FORMAT, req_array[i],
                         val);
            append(session, line, n);
        }
    }

    append(session, "\r\n</table><br>env varibles<br><table border=1>\r\n", 0);
    for (i = 0; i < sizeof(env_array) / sizeof(char *); ++i)
    {
        //env varibles
        n = g_api->get_req_env(session, env_array[i], strlen(env_array[i]), val,
                               VALMAXSIZE);
        if (n > 0)
        {
            val[n] = '\0';
            n = snprintf(line, LINEMAXSIZE - 1, CONTENT_FORMAT, env_array[i],
                         val);
            append(session, line, n);
        }
    }


    p = g_api->get_req_cookies(session, &n);
    if ((p != NULL) && p[0] != 0 && n > 0)
    {
        append(session,
               "\r\n</table><br>Request cookies<br><table border=1>\r\n", 0);
        append(session, "<tr><td>Cookie</td><td>", 0);
        append(session, p, n);
        append(session, "</td></tr>", 0);
    }

    n = g_api->get_req_cookie_count(session);
    if (n > 0)
    {
        //try get a certen cookie
        p = g_api->get_cookie_value(session, "LSWSWEBUI", 9, &n);
        if ((p != NULL) && n > 0)
        {
            append(session, "<tr><td>cookie_LSWSWEBUI</td><td>", 0);
            append(session, p, n);
            append(session, "</td></tr>", 0);
        }
    }
    append(session, "</table>", 0);

    n = get_reqbody_dealertype(session);

    mydata->req_body_len = g_api->get_req_content_length(session);
    mydata->rcvd_req_body_len = 0;
    mydata->type = n;
    sprintf(line,
            "Will deal with the req body.Type = %d, req body lenghth = %d<br>",
            n, mydata->req_body_len);

    append(session, line, 0);
    if (mydata->type == 0)
    {
        append(session, CONTENT_TAIL, 0);
        mydata->rcvd_done = 1;
        mydata->resp_done = 1;
    }

    g_api->set_status_code(session, 200);

    if (mydata->type == 3)  // Save to file
        mydata->fp = fopen("/tmp/uploadfile", "wb");
    else if (mydata->type == 2)   // Md5
        MD5_Init(&mydata->ctx);

    g_api->flush(session);

//     if ( mydata->type != 0)
    on_read(session);

    //g_api->end_resp(session);
    return 0;
}


static int on_write(const lsi_session_t *session)
{
    mydata_t *mydata = (mydata_t *)g_api->get_module_data(session, &MNAME,
                       LSI_DATA_HTTP);
    return (mydata == NULL || mydata->type == 0 || mydata->resp_done == 1) ?
           LSI_RSP_DONE : LSI_RSP_MORE;
}


static int rcvd_req_header_cbf(lsi_param_t *param)
{
    const char *uri;
    int len;
    uri = g_api->get_req_uri(param->session, &len);
    if ((uri != NULL) && (len >= sizeof(testuri) - 1)
        && (strncasecmp(uri, testuri, sizeof(testuri) - 1) == 0))
        g_api->register_req_handler(param->session, &MNAME, sizeof(testuri) - 1);
    return LSI_OK;
}


static int init_module(lsi_module_t *module)
{
    g_api->init_module_data(module, free_mydata, LSI_DATA_HTTP);
    return 0;
}


static int clean_up(const lsi_session_t *session)
{
    g_api->free_module_data(session, &MNAME, LSI_DATA_HTTP,
                            free_mydata);
    return 0;
}


static lsi_serverhook_t server_hooks[] =
{
    { LSI_HKPT_HTTP_BEGIN, initdata, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED },
    //{ LSI_HKPT_HTTP_END, resetdata, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED },
    { LSI_HKPT_RCVD_REQ_HEADER, rcvd_req_header_cbf, LSI_HOOK_NORMAL, LSI_FLAG_ENABLED },
    LSI_HOOK_END   //Must put this at the end position
};

static lsi_reqhdlr_t myhandler = { begin_process, on_read, on_write, clean_up };

lsi_module_t MNAME =
{
    LSI_MODULE_SIGNATURE, init_module, &myhandler, NULL, "", server_hooks
};

