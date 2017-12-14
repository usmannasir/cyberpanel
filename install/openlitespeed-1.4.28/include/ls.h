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
#ifndef LS_MODULE_H
#define LS_MODULE_H

#include <lsr/ls_types.h>
#include <lsr/ls_evtcb.h>
#include <lsr/ls_edio.h>

#include <stdio.h>
#include <sys/stat.h>
#include <sys/uio.h>
#include <inttypes.h>
#include <stdarg.h>


/**
 * @file ls.h
 */


/**
 * @brief Defines the major version number of LSIAPI.
 */
#define LSIAPI_VERSION_MAJOR    1
/**
 * @brief Defines the minor version number of LSIAPI.
 */
#define LSIAPI_VERSION_MINOR    1
/**
 * @brief Defines the version string of LSIAPI.
 */
#define LSIAPI_VERSION_STRING   "1.1"

/**
 * @def LSI_MODULE_SIGNATURE
 * @brief Identifies the module as a LSIAPI module and the version of LSIAPI that the module was compiled with.
 * @details The signature tells the server core first that it is actually a LSIAPI module,
 * and second, what version of the API that the binary was compiled with in order to check
 * whether it is backwards compatible with future versions.
 * @since 1.0
 */
//#define LSIAPI_MODULE_FLAG    0x4C53494D  //"LSIM"
#define LSI_MODULE_SIGNATURE    (int64_t)0x4C53494D00000000LL + \
    (int64_t)(LSIAPI_VERSION_MAJOR << 16) + \
    (int64_t)(LSIAPI_VERSION_MINOR)



/**
 * @def LSI_MAX_RESP_BUFFER_SIZE
 * @brief The max buffer size for is_resp_buffer_available.
 * @since 1.0
 */
#define LSI_MAX_RESP_BUFFER_SIZE     (1024*1024)


#ifdef __cplusplus
extern "C" {
#endif


/**************************************************************************************************
 *                                       API Parameter ENUMs
 **************************************************************************************************/

/**
 * @enum LSI_CFG_LEVEL
 * @brief The parameter level specified in the callback routine, lsi_confparser_t::parse_config,
 * in user configuration parameter parsing.
 * @since 1.0
 */
enum LSI_CFG_LEVEL
{
    /**
     * Server level configuration.
     */
    LSI_CFG_SERVER = 1,
    /**
     * Listener level configuration.
     */
    LSI_CFG_LISTENER = 2,
    /**
     * Virtual Host level configuration.
     */
    LSI_CFG_VHOST = 4,
    /**
     * Context level configuration.
     */
    LSI_CFG_CONTEXT = 8,
};


/**
 * @enum LSI_HOOK_PRIORITY
 * @brief The default running priorities for hook filter functions.
 * @details Used when there are more than one filter at the same hook point.
 * Any number from -1 * LSI_HOOK_PRIORITY_MAX to LSI_HOOK_PRIORITY_MAX can also be used.
 * The lower values will have higher priority, so they will run first.
 * Hook functions with the same order value will be called based on the order in which they appear
 * in the configuration list.
 * @since 1.0
 */
enum LSI_HOOK_PRIORITY
{
    /**
     * Hook priority first predefined value.
     */
    LSI_HOOK_FIRST  = -10,
    /**
     * Hook priority early in the processing phase.
     */
    LSI_HOOK_EARLY  =  0,
    /**
     * Hook Priority at the typical level.
     */
    LSI_HOOK_NORMAL =  10,
    /**
     * Hook priority to run later in the processing phase.
     */
    LSI_HOOK_LATE   =  20,
    /**
     * Hook priority last predefined value.
     */
    LSI_HOOK_LAST   =  30,


    /**
    * The max priority level allowed.
    */
    LSI_HOOK_PRIORITY_MAX = 6000

};


/**
 * @enum LSI_HOOK_FLAG
 * @brief Flags applying to hook functions.
 * @details A filter has two modes, TRANSFORMER and OBSERVER.  Flag if it is a transformer.
 * @details LSI_FLAG_TRANSFORM is a flag for filter hook points, indicating
 *  that the filter may change the content of the input data.
 *  If a filter does not change the input data, in OBSERVER mode, do not
 *  set this flag.
 *  When no TRANSFORMERs are in a filter chain of a hook point, the server will do
 *  optimizations to avoid deep copy by storing the data in the final buffer.
 *  Its use is important for LSI_HKPT_RECV_REQ_BODY and LSI_HKPT_L4_RECVING filter hooks.
 * @since 1.0
 *
 * @note Hook flags are additive. When required, multiple flags should be set.
 */
enum LSI_HOOK_FLAG
{
    /**
     * The filter hook function is a Transformer which modifies the input data.
     * This is for filter type hook points. If no filters are Transformer filters,
     * optimization could be applied by the server core when processing the data.
     */
    LSI_FLAG_TRANSFORM  = 1,

    /**
      * The hook function requires decompressed data.
      * This flag is for LSI_HKPT_RECV_RESP_BODY and LSI_HKPT_SEND_RESP_BODY.
      * If any filter requires decompression, the server core will add the decompression filter at the
      * beginning of the filter chain for compressed data.
      */
    LSI_FLAG_DECOMPRESS_REQUIRED = 2,

    /**
     * This flag is for LSI_HKPT_SEND_RESP_BODY only,
     * and should be added only if a filter needs to process a static file.
     * If no filter is needed to process a static file, sendfile() API will be used.
     */
    LSI_FLAG_PROCESS_STATIC = 4,


    /**
     * This flag enables the hook function.
     * It may be set statically on the global level,
     * or a call to enable_hook may be used.
     */
    LSI_FLAG_ENABLED = 8,


};


/**
 * @enum LSI_DATA_LEVEL
 * @brief Determines the scope of the module's user defined data.
 * @details Used by the level API parameter of various functions.
 * Determines what other functions are allowed to access the data and for how long
 * it will be available.
 * @since 1.0
 */
enum LSI_DATA_LEVEL
{
    /**
     * User data type for an HTTP session.
     */
    LSI_DATA_HTTP = 0,
    /**
     * User data for cached file type.
     */
    LSI_DATA_FILE,
    /**
     * User data type for TCP/IP data.
     */
    LSI_DATA_IP,
    /**
     * User data type for Virtual Hosts.
     */
    LSI_DATA_VHOST,
    /**
     * Module data type for a TCP layer 4 session.
     */
    LSI_DATA_L4,

    /**
     * Placeholder.
     */
    LSI_DATA_COUNT, /** This is NOT an index */
};


/**
 * @enum LSI_HKPT_LEVEL
 * @brief Hook Point level definitions.
 * @details Used in the API index parameter.
 * Determines which stage to hook the callback function to.
 * @since 1.0
 * @see lsi_serverhook_s
 */
enum LSI_HKPT_LEVEL
{
    /**
     * LSI_HKPT_L4_BEGINSESSION is the point when the session begins a tcp connection.
     * A TCP connection is also called layer 4 connection.
     */
    LSI_HKPT_L4_BEGINSESSION = 0,   //<--- must be first of L4

    /**
     * LSI_HKPT_L4_ENDSESSION is the point when the session ends a tcp connection.
     */
    LSI_HKPT_L4_ENDSESSION,

    /**
     * LSI_HKPT_L4_RECVING is the point when a tcp connection is receiving data.
     */
    LSI_HKPT_L4_RECVING,

    /**
     * LSI_HKPT_L4_SENDING is the point when a tcp connection is sending data.
     */
    LSI_HKPT_L4_SENDING,

    //Http level hook points

    /**
     * LSI_HKPT_HTTP_BEGIN is the point when the session begins an http connection.
     */
    LSI_HKPT_HTTP_BEGIN,       //<--- must be first of Http

    /**
     * LSI_HKPT_RCVD_REQ_HEADER is the point when the request header was just received.
     */
    LSI_HKPT_RCVD_REQ_HEADER,

    /**
     * LSI_HKPT_URI_MAP is the point when a URI request is mapped to a context.
     */
    LSI_HKPT_URI_MAP,

    /**
     * LSI_HKPT_HTTP_AUTH is the point when authentication check is performed.
     * It is triggered right after HTTP built-in authentication has been performed,
     * such as HTTP BASIC/DIGEST authentication.
     */
    LSI_HKPT_HTTP_AUTH,

    /**
     * LSI_HKPT_RECV_REQ_BODY is the point when request body data is being received.
     */
    LSI_HKPT_RECV_REQ_BODY,

    /**
     * LSI_HKPT_RCVD_REQ_BODY is the point when request body data was received.
     * This function accesses the body data file through a function pointer.
     */
    LSI_HKPT_RCVD_REQ_BODY,

    /**
     * LSI_HKPT_RECV_RESP_HEADER is the point when the response header was created.
     */
    LSI_HKPT_RCVD_RESP_HEADER,

    /**
     * LSI_HKPT_RECV_RESP_BODY is the point when response body is being received
     * by the backend of the web server.
     */
    LSI_HKPT_RECV_RESP_BODY,

    /**
     * LSI_HKPT_RCVD_RESP_BODY is the point when the whole response body was received
     * by the backend of the web server.
     */
    LSI_HKPT_RCVD_RESP_BODY,

    /**
     * LSI_HKPT_HANDLER_RESTART is the point when the server core needs to restart handler processing
     * by discarding the current response, either sending back an error page, or redirecting to a new
     * URL.  It could be triggered by internal redirect, a module deny access; it is only
     * triggered after handler processing starts for the current request.
     */
    LSI_HKPT_HANDLER_RESTART,

    /**
     * LSI_HKPT_SEND_RESP_HEADER is the point when the response header is ready
     * to be sent by the web server.
     */
    LSI_HKPT_SEND_RESP_HEADER,

    /**
     * LSI_HKPT_SEND_RESP_BODY is the point when the response body is being sent
     * by the web server.
     */
    LSI_HKPT_SEND_RESP_BODY,

    /**
     * LSI_HKPT_HTTP_END is the point when a session is ending an http connection.
     */
    LSI_HKPT_HTTP_END,      //<--- must be last of Http

    /**
     * LSI_HKPT_MAIN_INITED is the point when the main (controller) process
     * has completed its initialization and configuration,
     * before servicing any requests.
     * It occurs once upon startup.
     */
    LSI_HKPT_MAIN_INITED,     //<--- must be first of Server

    /**
     * LSI_HKPT_MAIN_PREFORK is the point when the main (controller) process
     * is about to start (fork) a worker process.
     * This occurs for each worker, and may happen during
     * system startup, or if a worker has been restarted.
     */
    LSI_HKPT_MAIN_PREFORK,

    /**
     * LSI_HKPT_MAIN_POSTFORK is the point after the main (controller) process
     * has started (forked) a worker process.
     * This occurs for each worker, and may happen during
     * system startup, or if a worker has been restarted.
     */
    LSI_HKPT_MAIN_POSTFORK,

    /**
     * LSI_HKPT_WORKER_INIT is the point at the beginning of a worker process
     * starts, before going into its event loop to start serve requests.
     * It is invoked when a worker process forked from main (controller) process,
     * or server started without the main (controller) process (debugging mode).
     * Note that when forked from the main process, a corresponding
     * MAIN_POSTFORK hook will be triggered in the main process, it may
     * occur either before *or* after this hook.
     */
    LSI_HKPT_WORKER_INIT,

    /**
     * LSI_HKPT_WORKER_ATEXIT is the point in a worker process
     * just before exiting.
     * It is the last hook point of a worker process.
     */
    LSI_HKPT_WORKER_ATEXIT,

    /**
     * LSI_HKPT_MAIN_ATEXIT is the point in the main (controller) process
     * just before exiting.
     * It is the last hook point of the server main process.
     */
    LSI_HKPT_MAIN_ATEXIT,

    LSI_HKPT_TOTAL_COUNT,  /** This is NOT an index */
};


/**
 * @enum LSI_LOG_LEVEL
 * @brief The log level definitions.
 * @details Used in the level API parameter of the write log function.
 * All logs with a log level less than or equal to the server defined level will be
 * written to the log.
 * @since 1.0
 */
enum LSI_LOG_LEVEL
{
    /**
     * Error level output turned on.
     */
    LSI_LOG_ERROR  = 3000,
    /**
     * Warnings level output turned on.
     */
    LSI_LOG_WARN   = 4000,
    /**
     * Notice level output turned on.
     */
    LSI_LOG_NOTICE = 5000,
    /**
     * Info level output turned on.
     */
    LSI_LOG_INFO   = 6000,
    /**
     * Debug level output turned on.
     */
    LSI_LOG_DEBUG  = 7000,
    
    LSI_LOG_DEBUG_LOW  = 7020,
    LSI_LOG_DEBUG_MEDIUM = 7050,
    LSI_LOG_DEBUG_HIGH = 7080,
    
    /**
     * Trace level output turned on.
     */
    LSI_LOG_TRACE  = 8000,
};


/**
 * @enum LSI_RETCODE
 * @brief LSIAPI return value definition.
 * @details Used in the return value of API functions and callback functions unless otherwise stipulated.
 * If a function returns an int type value, it should always
 * return LSI_OK for no errors and LSI_ERROR for other cases.
 * For such functions that return a bool type (true / false), 1 means true and 0 means false.
 * @since 1.0
 */
enum LSI_RETCODE
{
    /**
     * Return code for suspend current hookpoint
     */
    LSI_SUSPEND = -3,
    /**
     * Return code to deny access.
     */
    LSI_DENY = -2,
    /**
     * Return code error.
     */
    LSI_ERROR = -1,
    /**
     * Return code success.
     */
    LSI_OK = 0,

};


/**
 * @enum LSI_ONWRITE_RETCODE
 * @brief Write response return values.
 * @details Used as on_write_resp return value.
 * Continue should be used until the response sending is completed.
 * Finished will end the process of the server requesting further data.
 * @since 1.0
 */
enum LSI_ONWRITE_RETCODE
{
    /**
     * Error in the response processing.
     */
    LSI_RSP_ERROR = -1,
    /**
     * No further response data to write.
     */
    LSI_RSP_DONE = 0,
    /**
     * More response body data to write.
     */
    LSI_RSP_MORE,
};


/**
 * @enum LSI_CB_FLAG
 * @brief definition of flags used in hook function input and ouput parameters
 * @details It defines flags for _flag_in and _flag_out of lsi_param_t.
 * LSI_CB_FLAG_IN_XXXX is for _flag_in, LSI_CBFO_BUFFERED is for
 * _flag_out; the flags should be set or removed through a bitwise operator.
 *
 * @since 1.0
 */
enum LSI_CB_FLAGS
{
    /**
     * Indicates that a filter buffered data in its own buffer.
     */
    LSI_CBFO_BUFFERED = 1,

    /**
     * This flag requires the filter to flush its internal buffer to the next filter, then
     * pass this flag to the next filter.
     */
    LSI_CBFI_FLUSH = 1,

    /**
     * This flag tells the filter it is the end of stream; there should be no more data
     * feeding into this filter.  The filter should ignore any input data after this flag is
     * set.  This flag implies LSI_CBFI_FLUSH.  A filter should only set this flag after
     * all buffered data has been sent to the next filter.
     */
    LSI_CBFI_EOF = 2,

    /**
     * This flag is set for LSI_HKPT_SEND_RESP_BODY only if the input data is from
     * a static file; if a filter does not need to check a static file, it can skip processing
     * data if this flag is set.
     */
    LSI_CBFI_STATIC = 4,

    /**
     * This flag is set for LSI_HKPT_RCVD_RESP_BODY only if the request handler does not abort
     * in the middle of processing the response; for example, backend PHP crashes, or HTTP proxy
     * connection to backend has been reset.  If a hook function only needs to process
     * a successful response, it should check for this flag.
     */
    LSI_CBFI_RESPSUCC = 8,

};


/**
 * @enum LSI_REQ_VARIABLE
 * @brief LSIAPI request environment variables.
 * @details Used as API index parameter in env access function get_req_var_by_id.
 * The example reqinfohandler.c shows usage for all of these variables.
 * @since 1.0
 */
enum LSI_REQ_VARIABLE
{
    /**
     * Remote addr environment variable
     */
    LSI_VAR_REMOTE_ADDR = 0,
    /**
     * Remote port environment variable
     */
    LSI_VAR_REMOTE_PORT,
    /**
     * Remote host environment variable
     */
    LSI_VAR_REMOTE_HOST,
    /**
     * Remote user environment variable
     */
    LSI_VAR_REMOTE_USER,
    /**
     * Remote identifier environment variable
     */
    LSI_VAR_REMOTE_IDENT,
    /**
     * Remote method environment variable
     */
    LSI_VAR_REQ_METHOD,
    /**
     * Query string environment variable
     */
    LSI_VAR_QUERY_STRING,
    /**
     * Authentication type environment variable
     */
    LSI_VAR_AUTH_TYPE,
    /**
     * URI path environment variable
     */
    LSI_VAR_PATH_INFO,
    /**
     * Script filename environment variable
     */
    LSI_VAR_SCRIPTFILENAME,
    /**
     * Filename port environment variable
     */
    LSI_VAR_REQUST_FN,
    /**
     * URI environment variable
     */
    LSI_VAR_REQ_URI,
    /**
     * Document root directory environment variable
     */
    LSI_VAR_DOC_ROOT,
    /**
     * Port environment variable
     */
    LSI_VAR_SERVER_ADMIN,
    /**
     * Server name environment variable
     */
    LSI_VAR_SERVER_NAME,
    /**
     * Server address environment variable
     */
    LSI_VAR_SERVER_ADDR,
    /**
     * Server port environment variable
     */
    LSI_VAR_SERVER_PORT,
    /**
     * Server prototype environment variable
     */
    LSI_VAR_SERVER_PROTO,
    /**
     * Server software version environment variable
     */
    LSI_VAR_SERVER_SOFT,
    /**
     * API version environment variable
     */
    LSI_VAR_API_VERSION,
    /**
     * Request line environment variable
     */
    LSI_VAR_REQ_LINE,
    /**
     * Subrequest environment variable
     */
    LSI_VAR_IS_SUBREQ,
    /**
     * Time environment variable
     */
    LSI_VAR_TIME,
    /**
     * Year environment variable
     */
    LSI_VAR_TIME_YEAR,
    /**
     * Month environment variable
     */
    LSI_VAR_TIME_MON,
    /**
     * Day environment variable
     */
    LSI_VAR_TIME_DAY,
    /**
     * Hour environment variable
     */
    LSI_VAR_TIME_HOUR,
    /**
     * Minute environment variable
     */
    LSI_VAR_TIME_MIN,
    /**
     * Seconds environment variable
     */
    LSI_VAR_TIME_SEC,
    /**
     * Weekday environment variable
     */
    LSI_VAR_TIME_WDAY,
    /**
     * Script file name environment variable
     */
    LSI_VAR_SCRIPT_NAME,
    /**
     * Current URI environment variable
     */
    LSI_VAR_CUR_URI,
    /**
     * URI base name environment variable
     */
    LSI_VAR_REQ_BASENAME,
    /**
     * Script user id environment variable
     */
    LSI_VAR_SCRIPT_UID,
    /**
     * Script global id environment variable
     */
    LSI_VAR_SCRIPT_GID,
    /**
     * Script user name environment variable
     */
    LSI_VAR_SCRIPT_USERNAME,
    /**
     * Script group name environment variable
     */
    LSI_VAR_SCRIPT_GRPNAME,
    /**
     * Script mode environment variable
     */
    LSI_VAR_SCRIPT_MODE,
    /**
     * Script base name environment variable
     */
    LSI_VAR_SCRIPT_BASENAME,
    /**
     * Script URI environment variable
     */
    LSI_VAR_SCRIPT_URI,
    /**
     * Original URI environment variable
     */
    LSI_VAR_ORG_REQ_URI,
    /**
     * Original QS environment variable
     */
    LSI_VAR_ORG_QS,
    /**
     * HTTPS environment variable
     */
    LSI_VAR_HTTPS,
    /**
     * SSL version environment variable
     */
    LSI_VAR_SSL_VERSION,
    /**
     * SSL session ID environment variable
     */
    LSI_VAR_SSL_SESSION_ID,
    /**
     * SSL cipher environment variable
     */
    LSI_VAR_SSL_CIPHER,
    /**
     * SSL cipher use key size environment variable
     */
    LSI_VAR_SSL_CIPHER_USEKEYSIZE,
    /**
     * SSL cipher ALG key size environment variable
     */
    LSI_VAR_SSL_CIPHER_ALGKEYSIZE,
    /**
     * SSL client certification environment variable
     */
    LSI_VAR_SSL_CLIENT_CERT,
    /**
     * Geographical IP address environment variable
     */
    LSI_VAR_GEOIP_ADDR,
    /**
     * Translated path environment variable
     */
    LSI_VAR_PATH_TRANSLATED,
    /**
     * Placeholder.
     */
    LSI_VAR_COUNT,    /** This is NOT an index */
};


/**
 * @enum LSI_HEADER_OP
 * @brief The methods used for adding a response header.
 * @details Used in API parameter add_method in response header access functions.
 * If there are no existing headers, any method that is called
 * will have the effect of adding a new header.
 * If there is an existing header, LSI_HEADEROP_SET will
 * add a header and will replace the existing one.
 * LSI_HEADEROP_APPEND will append a comma and the header
 * value to the end of the existing value list.
 * LSI_HEADEROP_MERGE is just like LSI_HEADEROP_APPEND unless
 * the same value exists in the existing header.
 * In this case, it will do nothing.
 * LSI_HEADEROP_ADD will add a new line to the header,
 * whether or not it already exists.
 * @since 1.0
 */
enum LSI_HEADER_OP
{
    /**
     * Set the header.
     */
    LSI_HEADEROP_SET = 0,
    /**
     * Add with a comma to seperate
     */
    LSI_HEADEROP_APPEND,
    /**
     * Append unless it exists
     */
    LSI_HEADEROP_MERGE,
    /**
     * Add a new line
     */
    LSI_HEADEROP_ADD
};


/**
 * @enum LSI_URL_OP
 * @brief The methods used to redirect a request to a new URL.
 * @details LSI_URL_NOCHANGE, LSI_URL_REWRITE and LSI_URL_REDIRECT_* can be combined with
 * LSI_URL_QS_*
 * @since 1.0
 * @see lsi_api_s::set_uri_qs
 */
enum LSI_URL_OP
{
    /**
     * Do not change URI, intended for modifying Query String only.
     */
    LSI_URL_NOCHANGE = 0,

    /**
     * Rewrite to the new URI and use the URI for subsequent processing stages.
     */
    LSI_URL_REWRITE,

    /**
     * Internal redirect; the redirect is performed internally,
     * as if the server received a new request.
     */
    LSI_URL_REDIRECT_INTERNAL,

    /**
     * External redirect with status code 301 Moved Permanently.
     */
    LSI_URL_REDIRECT_301,

    /**
     * External redirect with status code 302 Found.
     */
    LSI_URL_REDIRECT_302,

    /**
     * External redirect with status code 303 See Other.
     */
    LSI_URL_REDIRECT_303,

    /**
     * External redirect with status code 307 Temporary Redirect.
     */
    LSI_URL_REDIRECT_307,

    /**
     * Do not change Query String. Only valid with LSI_URL_REWRITE.
     */
    LSI_URL_QS_NOCHANGE = 0 << 4,

    /**
     * Append Query String. Can be combined with LSI_URL_REWRITE and LSI_URL_REDIRECT_*.
     */
    LSI_URL_QS_APPEND = 1 << 4,

    /**
     * Set Query String. Can be combined with LSI_URL_REWRITE and LSI_URL_REDIRECT_*.
     */
    LSI_URL_QS_SET = 2 << 4,

    /**
     * Delete Query String. Can be combined with LSI_URL_REWRITE and LSI_URL_REDIRECT_*.
     */
    LSI_URL_QS_DELETE = 3 << 4,

    /**
     * indicates that encoding has been applied to URI.
     */
    LSI_URL_ENCODED = 128
};


/**
 * @enum LSI_REQ_HEADER_ID
 * @brief The most common request-header ids.
 * @details Used as the API header id parameter in request header access functions
 * to access components of the request header.
 * @since 1.0
 */
enum LSI_REQ_HEADER_ID
{
    /**
     * "Accept" request header.
     */
    LSI_HDR_ACCEPT = 0,
    /**
     * "Accept-Charset" request header.
     */
    LSI_HDR_ACC_CHARSET,
    /**
     * "Accept-Encoding" request header.
     */
    LSI_HDR_ACC_ENCODING,
    /**
     * "Accept-Language" request header.
     */
    LSI_HDR_ACC_LANG,
    /**
     * "Authorization" request header.
     */
    LSI_HDR_AUTHORIZATION,
    /**
     * "Connection" request header.
     */
    LSI_HDR_CONNECTION,
    /**
     * "Content-Type" request header.
     */
    LSI_HDR_CONTENT_TYPE,
    /**
     * "Content-Length" request header.
     */
    LSI_HDR_CONTENT_LENGTH,
    /**
     * "Cookie" request header.
     */
    LSI_HDR_COOKIE,
    /**
     * "Cookie2" request header.
     */
    LSI_HDR_COOKIE2,
    /**
     * "Host" request header.
     */
    LSI_HDR_HOST,
    /**
     * "Pragma" request header.
     */
    LSI_HDR_PRAGMA,
    /**
     * "Referer" request header.
     */
    LSI_HDR_REFERER,
    /**
     * "User-Agent" request header.
     */
    LSI_HDR_USERAGENT,
    /**
     * "Cache-Control" request header.
     */
    LSI_HDR_CACHE_CTRL,
    /**
     * "If-Modified-Since" request header.
     */
    LSI_HDR_IF_MODIFIED_SINCE,
    /**
     * "If-Match" request header.
     */
    LSI_HDR_IF_MATCH,
    /**
     * "If-No-Match" request header.
     */
    LSI_HDR_IF_NO_MATCH,
    /**
     * "If-Range" request header.
     */
    LSI_HDR_IF_RANGE,
    /**
     * "If-Unmodified-Since" request header.
     */
    LSI_HDR_IF_UNMOD_SINCE,
    /**
     * "Keep-Alive" request header.
     */
    LSI_HDR_KEEP_ALIVE,
    /**
     * "Range" request header.
     */
    LSI_HDR_RANGE,
    /**
     * "X-Forwarded-For" request header.
     */
    LSI_HDR_X_FORWARDED_FOR,
    /**
     * "Via" request header.
     */
    LSI_HDR_VIA,
    /**
     * "Transfer-Encoding" request header.
     */
    LSI_HDR_TRANSFER_ENCODING

};


/**
 * @enum LSI_RESP_HEADER_ID
 * @brief The most common response-header ids.
 * @details Used as the API header id parameter in response header access functions
 * to access components of the response header.
 * @since 1.0
 */
enum LSI_RESP_HEADER_ID
{
    /**
     * Accept ranges id
     */
    LSI_RSPHDR_ACCEPT_RANGES = 0,
    /**
     * Connection id
     */
    LSI_RSPHDR_CONNECTION,
    /**
     * Content type id.
     */
    LSI_RSPHDR_CONTENT_TYPE,
    /**
     * Content length id.
     */
    LSI_RSPHDR_CONTENT_LENGTH,
    /**
     * Content encoding id.
     */
    LSI_RSPHDR_CONTENT_ENCODING,
    /**
     * Content range id.
     */
    LSI_RSPHDR_CONTENT_RANGE,
    /**
     * Contnet disposition id.
     */
    LSI_RSPHDR_CONTENT_DISPOSITION,
    /**
     * Cache control id.
     */
    LSI_RSPHDR_CACHE_CTRL,
    /**
     * Date id.
     */
    LSI_RSPHDR_DATE,
    /**
     * E-tag id.
     */
    LSI_RSPHDR_ETAG,
    /**
     * Expires id.
     */
    LSI_RSPHDR_EXPIRES,
    /**
     * Keep alive message id.
     */
    LSI_RSPHDR_KEEP_ALIVE,
    /**
     * Lasst modified date id.
     */
    LSI_RSPHDR_LAST_MODIFIED,
    /**
     * Location id.
     */
    LSI_RSPHDR_LOCATION,
    /**
     * Litespeed location id.
     */
    LSI_RSPHDR_LITESPEED_LOCATION,
    /**
     * Cashe control id.
     */
    LSI_RSPHDR_LITESPEED_CACHE_CONTROL,
    /**
     * Pragma id.
     */
    LSI_RSPHDR_PRAGMA,
    /**
     * Proxy connection id.
     */
    LSI_RSPHDR_PROXY_CONNECTION,
    /**
     * Server id.
     */
    LSI_RSPHDR_SERVER,
    /**
     * Set cookie id.
     */
    LSI_RSPHDR_SET_COOKIE,
    /**
     * CGI status id.
     */
    LSI_RSPHDR_CGI_STATUS,
    /**
     * Transfer encoding id.
     */
    LSI_RSPHDR_TRANSFER_ENCODING,
    /**
     * Vary id.
     */
    LSI_RSPHDR_VARY,
    /**
     * Authentication id.
     */
    LSI_RSPHDR_WWW_AUTHENTICATE,
    /**
     * LiteSpeed Cache id.
     */
    LSI_RSPHDR_LITESPEED_CACHE,
    /**
     * LiteSpeed Purge id.
     */
    LSI_RSPHDR_LITESPEED_PURGE,
    /**
     * LiteSpeed Tag id.
     */
    LSI_RSPHDR_LITESPEED_TAG,
    /**
     * LiteSpeed Vary id.
     */
    LSI_RSPHDR_LITESPEED_VARY,
    /**
     * Powered by id.
     */
    LSI_RSPHDR_X_POWERED_BY,
    /**
     * Header end id.
     */
    LSI_RSPHDR_END,
    /**
     * Header unknown id.
     */
    LSI_RSPHDR_UNKNOWN = LSI_RSPHDR_END

};


/**
 * @enum LSI_ACL_LEVEL
 * @brief The access control level definitions.
 * @details Used as the value for client access control level when evaulated 
 * against a ACL list.
 * @see   get_client_access_level 
 * @since 1.1
 */
enum LSI_ACL_LEVEL
{
    LSI_ACL_DENY,
    LSI_ACL_ALLOW,
    LSI_ACL_TRUST,
    LSI_ACL_BLOCK
};


/*
 * Forward Declarations
 */

typedef struct lsi_module_s     lsi_module_t;
typedef struct lsi_api_s        lsi_api_t;
typedef struct lsi_param_s      lsi_param_t;
typedef struct lsi_hookinfo_s   lsi_hookchain_t;
typedef struct evtcbhead_s      lsi_session_t;
typedef struct lsi_serverhook_s lsi_serverhook_t;
typedef struct lsi_reqhdlr_s    lsi_reqhdlr_t;
typedef struct lsi_confparser_s lsi_confparser_t;



/**
 * @typedef lsi_callback_pf
 * @brief The callback function and its parameters.
 * @since 1.0
 */
typedef int (*lsi_callback_pf)(lsi_param_t *);

/**
 * @typedef lsi_datarelease_pf
 * @brief The memory release callback function for the user module data.
 * @since 1.0
 */
typedef int (*lsi_datarelease_pf)(void *);

/**
 * @typedef lsi_timercb_pf
 * @brief The timer callback function for the set timer feature.
 * @since 1.0
 */
typedef void (*lsi_timercb_pf)(const void *);



/**************************************************************************************************
 *                                       API Structures
 **************************************************************************************************/


/**
 * @typedef lsi_param_t
 * @brief Callback parameters passed to the callback functions.
 * @since 1.0
 **/
struct lsi_param_s
{
    /**
     * @brief session is a pointer to the session.
     * @since 1.0
     */
    const lsi_session_t      *session;

    /**
     * @brief hook_chain is a pointer to the struct lsi_hookinfo_t.
     * @since 1.0
     */
    const lsi_hookchain_t    *hook_chain;

    /**
     * @brief cur_hook is a pointer to the current hook.
     * @since 1.0
     */
    const void               *cur_hook;

    /**
     * @brief _param is a pointer to the first parameter.
     * @details Refer to the LSIAPI Developer's Guide's
     * Callback Parameter Definition table for a table
     * of expected values for each _param based on use.
     * @since 1.0
     */
    const void         *ptr1;

    /**
     * @brief _param_count is the length of the first parameter.
     * @since 1.0
     */
    int                 len1;

    /**
     * @brief _flag_out is a pointer to the second parameter.
     * @since 1.0
     */
    int                *flag_out;

    /**
     * @brief _flag_in is the length of the second parameter.
     * @since 1.0
     */
    int                 flag_in;
};


/**
 * @typedef lsi_reqhdlr_t
 * @brief Pre-defined handler functions.
 * @since 1.0
 */
struct lsi_reqhdlr_s
{
    /**
     * @brief begin_process is called when the server starts to process a request.
     * @details It is used to define the request handler callback function.
     * @since 1.0
     */
    int (*begin_process)(const lsi_session_t *pSession);

    /**
     * @brief on_read_req_body is called on a READ event with a large request body.
     * @details on_read_req_body is called when a request has a
     * large request body that was not read completely.
     * If not provided, this function should be set to NULL.
     * The default function will execute and return 0.
     * @since 1.0
     */
    int (*on_read_req_body)(const lsi_session_t *pSession);

    /**
     * @brief on_write_resp is called on a WRITE event with a large response body.
     * @details on_write_resp is called when the server gets a large response body
     * where the response did not write completely.
     * If not provided, set it to NULL.
     * The default function will execute and return LSI_RSP_DONE.
     * @since 1.0
     */
    int (*on_write_resp)(const lsi_session_t *pSession);

    /**
     * @brief on_clean_up is called when the server core is done with the handler, asking the
     * handler to perform clean up.
     * @details It is called after a handler called end_resp(), or if the server needs to switch handler;
     * for example, return an error page or perform an internal redirect while the handler is processing the request.
     * @since 1.0
     */
    int (*on_clean_up)(const lsi_session_t *pSession);

};


/**
 * lsi_config_key_s
 * id is assigned by module developer, it can be any unique number larger than 0 .
 * It is not required to be sorted.
 * 
 */
typedef struct lsi_config_key_s
{
    const char *config_key;
    uint16_t id;
    uint16_t level;
} lsi_config_key_t;


/***
 * Be ware, key_index is not the above id.
 * key_index is base 0, which indicate the index in the lsi_config_key_t array.
 * so it will be in order, start with 0, then 1 and so on.
 * 
 */
typedef struct module_param_info_st
{
    uint16_t    key_index; 
    uint16_t    val_len;
    char        *val;
} module_param_info_t;

/**
 * @typedef lsi_confparser_s
 * @brief Contains functions which are used to define parse and release functions for the
 * user defined configuration parameters.
 * @details
 * The parse functions will be called during module load.  The release function will be called on
 * session end.  However, it is recommended that the user always performs a manual release of all
 * allocated memory using the session_end filter hooks.
 * @since 1.0
 */
struct lsi_confparser_s
{
    /**
     * @brief parse_config is a callback function for the server to call to parse the user defined
     * parameters and return a pointer to the user defined configuration data structure.
     * @details
     *
     * @since 1.0
     * @param[in] params - the array which hold the module_param_info_t.
     * @param[in] param_count - the count of module_param_info_t hold in params.
     * @param[in] initial_config - a pointer to the default configuration inherited from the parent level.
     * @param[in] level - applicable level from enum #lsi_confparser_level.
     * @param[in] name - name of the Server/Listener/VHost or URI of the Context.
     * @return a pointer to a the user-defined configuration data, which combines initial_config with
     *         settings in param; if both param and initial_config are NULL, a hard-coded default
     *         configuration value should be returned.
     */
    void  *(*parse_config)(module_param_info_t *params, int param_count,
                           void *initial_config, int level, const char *name);

    /**
     * @brief free_config is a callback function for the server to call to release a pointer to
     * the user defined data.
     * @since 1.0
     * @param[in] config - a pointer to configuration data structure to be released.
     */
    void (*free_config)(void *config);

    /**
     * @brief config_keys is a NULL terminated array of const char *.
     * It is used to filter the module user parameters by the server while parsing the configuration.
     * @since 1.0
     */
    lsi_config_key_t *config_keys;
};


/**
 * @typedef lsi_serverhook_s
 * @brief Global hook point specification.
 * @details An array of these entries, terminated by the LSI_HOOK_END entry,
 * at lsi_module_t::_serverhook defines the global hook points of a module.
 * @since 1.0
 */
struct lsi_serverhook_s
{
    /**
     * @brief specifies the hook point using level definitions from enum #LSI_HKPT_LEVEL.
     * @since 1.0
     */
    int             index;

    /**
     * @brief points to the callback hook function.
     * @since 1.0
     */
    lsi_callback_pf cb;

    /**
     * @brief defines the priority of this hook function within a function chain.
     * @since 1.0
     */
    short           priority;

    /**
     * @brief additive hook point flags using level definitions from enum #LSI_HOOK_FLAG.
     * @since 1.0
     */
    short           flag;

};


/**
 * @def LSI_HOOK_END
 * @brief Termination entry for the array of lsi_serverhook_t entries
 * at lsi_module_t::_serverhook.
 * @since 1.0
 */
#define LSI_HOOK_END    {0, NULL, 0, 0}


#define LSI_MODULE_RESERVED_SIZE    ((3 * sizeof(void *)) \
                                     + ((LSI_HKPT_TOTAL_COUNT + 2) * sizeof(int32_t)) \
                                     + (LSI_DATA_COUNT * sizeof(int16_t)))

#define MODULE_LOG_LEVEL(x)      (*(int32_t *)(x->reserved))


/**
 * @typedef lsi_module_t
 * @brief Defines an LSIAPI module, this struct must be provided in the module code.
 * @since 1.0
 */
struct lsi_module_s
{
    /**
     * @brief identifies an LSIAPI module. It should be set to LSI_MODULE_SIGNATURE.
     * @since 1.0
     */
    int64_t                  signature;

    /**
     * @brief a function pointer that will be called after the module is loaded.
     * Used to initialize module data.
     * @since 1.0
     */
    int (*init_pf)(lsi_module_t *module);

    /**
     * @brief _handler needs to be provided if this module is a request handler.
     * If not present, set to NULL.
     * @since 1.0
     */
    lsi_reqhdlr_t           *reqhandler;

    /**
     * @brief contains functions which are used to parse user defined
     * configuration parameters and to release the memory block.
     * If not present, set to NULL.
     * @since 1.0
     */
    lsi_confparser_t        *config_parser;

    /**
     * @brief information about this module set by the developer;
     * it can contain module version and/or version(s) of libraries used by this module.
     * If not present, set to NULL.
     * @since 1.0
     */
    const char              *about;

    /**
     * @brief information for global server level hook functions.
     * If not present, set to NULL.
     * @since 1.0
     */
    lsi_serverhook_t        *serverhook;

    int32_t                  reserved[(LSI_MODULE_RESERVED_SIZE + 3) / 4 ];
};



/**************************************************************************************************
 *                                       API Functions
 **************************************************************************************************/

/**
 * @typedef lsi_api_t
 * @brief LSIAPI function set.
 * @since 1.0
 **/
struct lsi_api_s
{
    /**************************************************************************************************************
     *                                        SINCE LSIAPI 1.0                                                    *
     * ************************************************************************************************************/

    /**
     * @brief get_server_root is used to get the server root path.
     *
     * @since 1.0
     *
     * @return A \\0-terminated string containing the path to the server root directory.
     */
    const char *(*get_server_root)();

    /**
     * @brief log is used to write the formatted log to the error log associated with a session.
     * @details session ID will be added to the log message automatically when session is not NULL.
     * This function will not add a trailing \\n to the end.
     *
     * @since 1.0
     *
     * @param[in] pSession - current session, log file, and session ID are based on session.
     * @param[in] level - enum defined in log level definitions #LSI_LOG_LEVEL.
     * @param[in] fmt - formatted string.
     */
    void (*log)(const lsi_session_t *pSession, int level, const char *fmt, ...)
#if __GNUC__
        __attribute__((format(printf, 3, 4)))
#endif
        ;
        
    /**
     * @brief vlog is used to write the formatted log to the error log associated with a session
     * @details session ID will be added to the log message automatically when the session is not NULL.
     *
     * @since 1.0
     *
     * @param[in] pSession - current session, log file and session ID are based on session.
     * @param[in] level - enum defined in log level definitions #LSI_LOG_LEVEL.
     * @param[in] fmt - formatted string.
     * @param[in] vararg - the varying argument list.
     * @param[in] no_linefeed - 1 = do not add \\n at the end of message; 0 = add \\n
     */
    void (*vlog)(const lsi_session_t *pSession, int level, const char *fmt,
                 va_list vararg, int no_linefeed);

    /**
     * @brief lograw is used to write additional log messages to the error log file associated with a session.
     * No timestamp, log level, session ID prefix is added; just the data in the buffer is logged into log files.
     * This is usually used for adding more content to previous log messages.
     *
     * @since 1.0
     *
     * @param[in] pSession - log file is based on session; if set to NULL, the default log file is used.
     * @param[in] buf - data to be written to log file.
     * @param[in] len - the size of data to be logged.
     */
    void (*lograw)(const lsi_session_t *pSession, const char *buf, int len);

    /**
     * @brief get_config is used to get the user defined module parameters which are parsed by
     * the callback parse_config and pointed to in the struct lsi_confparser_t.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession, or use NULL for the server level.
     * @param[in] pModule - a pointer to an lsi_module_t struct.
     * @return a pointer to the user-defined configuration data.
     */
    void *(*get_config)(const lsi_session_t *pSession,
                        const lsi_module_t *pModule);


    /**
     * @brief enable_hook is used to set the flag of a hook function in a certain level to enable or disable the function.
     * This should only be used after a session is already created
     * and applies only to this session.
     * There are L4 level and HTTP level session hooks.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession, obtained from
     *   callback parameters.
     * @param[in] pModule - a pointer to the lsi_module_t struct.
     * @param[in] enable - a value that the flag is set to, it is 0 to disable,
     *   otherwise is to enable.
     * @param[in] index - A list of indices to set, as defined in the enum of
     *   Hook Point level definitions #LSI_HKPT_LEVEL.
     * @param[in] iNumIndices - The number of indices to set in index.
     * @return -1 on failure.
     */
    int (*enable_hook)(const lsi_session_t *session, const lsi_module_t *pModule,
                       int enable, int *index, int iNumIndices);



    /**
     * @brief get_hook_flag is used to get the flag of the hook functions in a
     * certain level.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession, obtained from
     *   callback parameters.
     * @param[in] index - A list of indices to set, as defined in the enum of
     *   Hook Point level definitions #LSI_HKPT_LEVEL.
     */
    int (*get_hook_flag)(const lsi_session_t *session, int index);


    int (*get_hook_level)(lsi_param_t *pParam);

    /**
     * @brief get_module is used to retrieve module information associated with a hook point based on callback parameters.
     *
     * @since 1.0
     *
     * @param[in] pParam - a pointer to callback parameters.
     * @return NULL on failure, a pointer to the lsi_module_t data structure on success.
     */
    const lsi_module_t *(*get_module)(lsi_param_t *pParam);

    /**
     * @brief init_module_data is used to initialize module data of a certain level(scope).
     * init_module_data must be called before using set_module_data or get_module_data.
     *
     * @since 1.0
     *
     * @param[in] pModule - a pointer to the current module defined in lsi_module_t struct.
     * @param[in] cb - a pointer to the user-defined callback function that releases the user data.
     * @param[in] level - as defined in the module data level enum #LSI_DATA_LEVEL.
     * @return -1 for wrong level, -2 for already initialized, 0 for success.
     */
    int (*init_module_data)(const lsi_module_t *pModule, lsi_datarelease_pf cb,
                            int level);

    /**
     * @brief Before using FILE type module data, the data must be initialized by
     * calling init_file_type_mdata with the file path.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the lsi_session_t struct.
     * @param[in] pModule - a pointer to an lsi_module_t struct.
     * @param[in] path - a pointer to the path string.
     * @param[in] pathLen - the length of the path string.
     * @return -1 on failure, file descriptor on success.
     */
    int (*init_file_type_mdata)(const lsi_session_t *pSession,
                                const lsi_module_t *pModule, const char *path, int pathLen);

    /**
     * @brief set_module_data is used to set the module data of a session level(scope).
     * sParam is a pointer to the user's own data structure.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the lsi_session_t struct.
     * @param[in] pModule - a pointer to an lsi_module_t struct.
     * @param[in] level - as defined in the module data level enum #LSI_DATA_LEVEL.
     * @param[in] sParam - a pointer to the user defined data.
     * @return -1 for bad level or no release data callback function, 0 on success.
     */
    int (*set_module_data)(const lsi_session_t *pSession,
                           const lsi_module_t *pModule, int level, void *sParam);

    /**
     * @brief get_module_data gets the module data which was set by set_module_data.
     * The return value is a pointer to the user's own data structure.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the lsi_session_t struct.
     * @param[in] pModule - a pointer to an lsi_module_t struct.
     * @param[in] level - as defined in the module data level enum #LSI_DATA_LEVEL.
     * @return NULL on failure, a pointer to the user defined data on success.
     */
    void *(*get_module_data)(const lsi_session_t *pSession,
                             const lsi_module_t *pModule, int level);

    /**
    * @brief get_cb_module_data gets the module data related to the current callback.
    * The return value is a pointer to the user's own data structure.
    *
    * @since 1.0
    *
    * @param[in] pParam - a pointer to callback parameters.
    * @param[in] level - as defined in the module data level enum #LSI_DATA_LEVEL.
    * @return NULL on failure, a pointer to the user defined data on success.
    */
    void *(*get_cb_module_data)(const lsi_param_t *pParam, int level);

    /**
     * @brief free_module_data is to be called when the user needs to free the module data immediately.
     * It is not used by the web server to call the release callback later.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the lsi_session_t struct.
     * @param[in] pModule - a pointer to an lsi_module_t struct.
     * @param[in] level - as defined in the module data level enum #LSI_DATA_LEVEL.
     * @param[in] cb - a pointer to the user-defined callback function that releases the user data.
     */
    void (*free_module_data)(const lsi_session_t *pSession,
                             const lsi_module_t *pModule, int level, lsi_datarelease_pf cb);

    /**
     * @brief stream_writev_next needs to be called in the LSI_HKPT_L4_SENDING hook point level just
     * after it finishes the action and needs to call the next step.
     *
     * @since 1.0
     *
     * @param[in] pParam - the callback parameters to be sent to the current hook callback function.
     * @param[in] iov - the IO vector of data to be written.
     * @param[in] count - the size of the IO vector.
     * @return the return value from the hook filter callback function.
     */
    int (*stream_writev_next)(lsi_param_t *pParam, struct iovec *iov,
                              int count);

    /**
     * @brief stream_read_next needs to be called in filter
     * callback functions registered to the LSI_HKPT_L4_RECVING and LSI_HKPT_RECV_REQ_BODY hook point level
     * to get data from a higher level filter in the chain.
     *
     * @since 1.0
     *
     * @param[in] pParam - the callback parameters to be sent to the current hook callback function.
     * @param[in,out] pBuf - a pointer to a buffer provided to hold the read data.
     * @param[in] size - the buffer size.
     * @return the return value from the hook filter callback function.
     */
    int (*stream_read_next)(lsi_param_t *pParam, char *pBuf, int size);

    /**
     * @brief stream_write_next is used to write the response body to the next function
     * in the filter chain of LSI_HKPT_SEND_RESP_BODY level.
     * This must be called in order to send the response body to the next filter.
     * It returns the size written.
     *
     * @since 1.0
     *
     * @param[in] pParam - a pointer to the callback parameters.
     * @param[in] buf - a pointer to a buffer to be written.
     * @param[in] buflen - the size of the buffer.
     * @return -1 on failure, return value of the hook filter callback function.
     */
    int (*stream_write_next)(lsi_param_t *pParam, const char *buf, int len);


    /**
     * @brief get_req_raw_headers_length can be used to get the length of the total request headers.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return length of the request header.
     */
    int (*get_req_raw_headers_length)(const lsi_session_t *pSession);

    /**
     * @brief get_req_raw_headers can be used to store all of the request headers in a given buffer.
     * If maxlen is too small to contain all the data,
     * it will only copy the amount of the maxlen.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in,out] buf - a pointer to a buffer provided to hold the header strings.
     * @param[in] maxlen - the size of the buffer.
     * @return - the length of the request header.
     */
    int (*get_req_raw_headers)(const lsi_session_t *pSession, char *buf, int maxlen);

    /**
     * @brief get_req_headers_count can be used to get the count of the request headers.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return the number of headers in the whole request header.
     */
    int (*get_req_headers_count)(const lsi_session_t *pSession);

    /**
     * @brief get_req_headers can be used to get all the request headers.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[out] iov_key - the IO vector that contains the keys.
     * @param[out] iov_val - the IO vector that contains the values.
     * @param[in] maxIovCount - size of the IO vectors.
     * @return the count of headers in the IO vectors.
     */
    int (*get_req_headers)(const lsi_session_t *pSession, struct iovec *iov_key,
                           struct iovec *iov_val, int maxIovCount);

    /**
     * @brief get_req_header can be used to get a request header based on the given key.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] key - a pointer to a string describing the header label, (key).
     * @param[in] keylen - the size of the string.
     * @param[in,out] valLen - a pointer to the length of the returned string.
     * @return a pointer to the request header key value string.
     */
    const char *(*get_req_header)(const lsi_session_t *pSession, const char *key,
                                  int keyLen, int *valLen);

    /**
     * @brief get_req_header_by_id can be used to get a request header based on the given header id
     * defined in LSI_REQ_HEADER_ID
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] id - header id defined in LSI_REQ_HEADER_ID.
     * @param[in,out] valLen - a pointer to the length of the returned string.
     * @return a pointer to the request header key value string.
     */
    const char *(*get_req_header_by_id)(const lsi_session_t *pSession, int id,
                                        int *valLen);

    /**
     * @brief get_req_org_uri is used to get the original URI as delivered in the request,
     * before any processing has taken place.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in,out] buf - a pointer to the buffer for the URI string.
     * @param[in] buf_size - max size of the buffer.
     *
     * @return length of the URI string.
     */
    int (*get_req_org_uri)(const lsi_session_t *pSession, char *buf, int buf_size);

    /**
     * @brief get_req_uri can be used to get the URI of a HTTP session.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in,out] uri_len - a pointer to int; if not NULL, the length of the URI is returned.
     * @return pointer to the URI string. The string is readonly.
     */
    const char *(*get_req_uri)(const lsi_session_t *pSession, int *uri_len);

    /**
     * @brief get_mapped_context_uri can be used to get the context URI of an HTTP session.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in,out] length - the length of the returned string.
     * @return pointer to the context URI string.
     */
    const char *(*get_mapped_context_uri)(const lsi_session_t *pSession,
                                          int *length);

    /**
     * @brief is_req_handler_registered can be used to test if a request handler
     * of a session was already registered or not.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return 1 on true, and 0 on false.
     */
    int (*is_req_handler_registered)(const lsi_session_t *pSession);

    /**
     * @brief register_req_handler can be used to dynamically register a handler.
     * The scriptLen is the length of the script.  To call this function,
     * the module needs to provide the lsi_reqhdlr_t (not set to NULL).
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] pModule - a pointer to an lsi_module_t struct.
     * @param[in] scriptLen - the length of the script name string.
     * @return -1 on failure, 0 on success.
     */
    int (*register_req_handler)(const lsi_session_t *pSession, lsi_module_t *pModule,
                                int scriptLen);

    /**
     * @brief set_handler_write_state can change the calling of on_write_resp() of a module handler.
     * If the state is 0, the calling will be suspended;
     * otherwise, if it is 1, it will continue to call when not finished.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] state - 0 to suspend the calling; 1 to continue.
     * @return
     *
     */
    int (*set_handler_write_state)(const lsi_session_t *pSession, int state);

    /**
     * @brief set_timer sets a timer.
     *
     * @since 1.0
     *
     * @param[in] timeout_ms - Timeout in ms.
     * @param[in] repeat - 1 to repeat, 0 for no repeat.
     * @param[in] timer_cb - Callback function to be called on timeout.
     * @param[in] timer_cb_param - Optional parameter for the
     *      callback function.
     * @return Timer ID if successful, LS_FAIL if it failed.
     *
     */
    int (*set_timer)(unsigned int timeout_ms, int repeat,
                     lsi_timercb_pf timer_cb, const void *timer_cb_param);

    /**
     * @brief remove_timer removes a timer.
     *
     * @since 1.0
     *
     * @param[in] time_id - timer id
     * @return 0.
     *
     */
    int (*remove_timer)(int time_id);


    /***
     * Reurn 0 if error, otherwise return non-zero
     */
    long (*create_event)(evtcb_pf cb, const lsi_session_t *pSession,
                         long lParam, void *pParam);
    long (*create_session_resume_event)(const lsi_session_t *session,
                                        lsi_module_t *pModule);

    
    
    long (*get_event_obj)(evtcb_pf cb, const lsi_session_t *pSession,
                         long lParam, void *pParam);
    
    void (*cancel_event)(const lsi_session_t *pSession, long event_obj);
    void (*schedule_event)(long event_obj, int nowait);


    /**
     * get_req_cookies is used to get all the request cookies.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in,out] len - a pointer to the length of the cookies string.
     * @return a pointer to the cookie key string.
     */
    const char *(*get_req_cookies)(const lsi_session_t *pSession, int *len);

    /**
     * @brief get_req_cookie_count is used to get the request cookies count.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return the number of cookies.
     */
    int (*get_req_cookie_count)(const lsi_session_t *pSession);

    /**
     * @brief get_cookie_value is to get a cookie based on the cookie name.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] cookie_name - a pointer to the cookie name string.
     * @param[in] nameLen - the length of the cookie name string.
     * @param[in,out] valLen - a pointer to the length of the cookie string.
     * @return a pointer to the cookie string.
     */
    const char *(*get_cookie_value)(const lsi_session_t *pSession,
                                    const char *cookie_name, int nameLen, int *valLen);

    /**
     * @brief get_cookie_by_index is to get a cookie based on index.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] index - a index of the list of cookies parsed for current request.
     * @param[out] cookie - a pointer to the cookie name string.
     * @return 1 if cookie is avaialble, 0 if index is out of range.
     */
    int (*get_cookie_by_index)(const lsi_session_t *pSession, int index, ls_strpair_t *cookie);

    /**
     * @brief get_client_ip is used to get the request ip address.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in,out] len - a pointer to the length of the IP string.
     * @return a pointer to the IP string.
     */
    const char *(*get_client_ip)(const lsi_session_t *pSession, int *len);

    /**
     * @brief get_req_query_string is used to get the request query string.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in,out] len - a pointer to the length of the query string.
     * @return a pointer to the query string.
     */
    const char *(*get_req_query_string)(const lsi_session_t *pSession, int *len);

    /**
     * @brief get_req_var_by_id is used to get the value of a server variable and
     * environment variable by the env type. The caller is responsible for managing the
     * buffer holding the value returned.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] id - enum #LSI_REQ_VARIABLE defined as LSIAPI request variable ID.
     * @param[in,out] val - a pointer to the allocated buffer holding value string.
     * @param[in] maxValLen - the maximum size of the variable value string.
     * @return the length of the variable value string.
     */
    int (*get_req_var_by_id)(const lsi_session_t *pSession, int id, char *val,
                             int maxValLen);

    /**
     * @brief get_req_env is used to get the value of a server variable and
     * environment variable based on the name.  It will also get the env that is set by set_req_env.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] name - a pointer to the variable name string.
     * @param[in] nameLen - the length of the variable name string.
     * @param[in,out] val - a pointer to the variable value string.
     * @param[in] maxValLen - the maximum size of the variable value string.
     * @return the length of the variable value string.
     */
    int (*get_req_env)(const lsi_session_t *pSession, const char *name,
                       unsigned int nameLen, char *val, int maxValLen);

    /**
     * @brief set_req_env is used to set a request environment variable.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] name - a pointer to the variable name string.
     * @param[in] nameLen - the length of the variable name string.
     * @param[in] val - a pointer to the variable value string.
     * @param[in] valLen - the size of the variable value string.
     */
    void (*set_req_env)(const lsi_session_t *pSession, const char *name,
                        unsigned int nameLen, const char *val, int valLen);

    /**
     * @brief register_env_handler is used to register a callback with a set_req_env defined by an env_name,
     * so that when such an env is set by set_req_env or rewrite rule,
     * the registered callback will be called.
     *
     * @since 1.0
     *
     * @param[in] env_name - the string containing the environment variable name.
     * @param[in] env_name_len - the length of the string.
     * @param[in] cb - a pointer to the user-defined callback function associated with the environment variable.
     * @return Not used.
     */
    int (*register_env_handler)(const char *env_name,
                                unsigned int env_name_len, lsi_callback_pf cb);

    /**
     * @brief get_uri_file_path will get the real file path mapped to the request URI.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] uri - a pointer to the URI string.
     * @param[in] uri_len - the length of the URI string.
     * @param[in,out] path - a pointer to the path string.
     * @param[in] max_len - the max length of the path string.
     * @return the length of the path string.
     */
    int (*get_uri_file_path)(const lsi_session_t *pSession, const char *uri,
                             int uri_len, char *path, int max_len);

    /**
     * @brief set_uri_qs changes the URI and Query String of the current session; perform internal/external redirect.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] action - action to be taken to URI and Query String, defined by #LSI_URL_OP:
     * - LSI_URL_NOCHANGE - do not change the URI.
     * - LSI_URL_REWRITE - rewrite a new URI and use for processing.
     * - LSI_URL_REDIRECT_INTERNAL - internal redirect, as if the server received a new request.
     * - LSI_URL_REDIRECT_{301,302,303,307} - external redirect.
     * .
     * combined with one of the Query String qualifiers:
     * - LSI_URL_QS_NOCHANGE - do not change the Query String (LSI_URL_REWRITE only).
     * - LSI_URL_QS_APPEND - append to the Query String.
     * - LSI_URL_QS_SET - set the Query String.
     * - LSI_URL_QS_DELETE - delete the Query String.
     * .
     * and optionally LSI_URL_ENCODED if encoding has been applied to the URI.
     * @param[in] uri - a pointer to the URI string.
     * @param[in] len - the length of the URI string.
     * @param[in] qs -  a pointer to the Query String.
     * @param[in] qs_len - the length of the Query String.
     * @return -1 on failure, 0 on success.
     * @note LSI_URL_QS_NOCHANGE is only valid with LSI_URL_REWRITE, in which case qs and qs_len MUST be NULL.
     * In all other cases, a NULL specified Query String has the effect of deleting the resultant Query String completely.
     * In all cases of redirection, if the Query String is part of the target URL, qs and qs_len must be specified,
     * since the original Query String is NOT carried over.
     *
     * \b Example of external redirection, changing the URI and setting a new Query String:
     * @code
     *
       static int handlerBeginProcess( lsi_session_t *pSession )
       {
          ...
          g_api->set_uri_qs( pSession,
            LSI_URL_REDIRECT_307|LSI_URL_QS_SET, "/new_location", 13, "ABC", 3 );
          ...
       }
     * @endcode
     * would result in a response header similar to:
     * @code
       ...
       HTTP/1.1 307 Temporary Redirect
       ...
       Server: LiteSpeed
       Location: http://localhost:8088/new_location?ABC
       ...
       @endcode
       \n
     */
    int (*set_uri_qs)(const lsi_session_t *pSession, int action, const char *uri,
                      int uri_len, const char *qs, int qs_len);

    /**
     * @brief get_req_content_length is used to get the content length of the request.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return content length.
     */
    int64_t (*get_req_content_length)(const lsi_session_t *pSession);

    /**
     * @brief read_req_body is used to get the request body to a given buffer.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in,out] buf - a pointer to a buffer provided to hold the header strings.
     * @param[in] buflen - size of the buffer.
     * @return length of the request body.
     */
    int (*read_req_body)(const lsi_session_t *pSession, char *buf, int bufLen);

    /**
     * @brief is_req_body_finished is used to ensure that all the request body data
     * has been accounted for.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return 0 false, 1 true.
     */
    int (*is_req_body_finished)(const lsi_session_t *pSession);

    /**
     * @brief set_req_wait_full_body is used to make the server wait to call
     * begin_process until after the full request body is received.
     * @details If the user calls this function within begin_process, the
     * server will call on_read_req_body only after the full request body is received.
     * Please refer to the
     * LiteSpeed Module Developer's Guide for a more in-depth explanation of the
     * purpose of this function.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return
     */
    int (*set_req_wait_full_body)(const lsi_session_t *pSession);



    int (*parse_req_args)(const lsi_session_t *session, int parse_req_body,
                          int uploadPassByPath, const char *uploadTmpDir,
                          int uploadTmpFilePermission);

    /**
     * @brief set_resp_wait_full_body is used to make the server wait for
     * the whole response body before starting to send response back to the client.
     * @details If this function is called before the server sends back any response
     * data, the server will wait for the whole response body. If it is called after the server
     * begins sending back response data, the server will stop sending more data to the client
     * until the whole response body has been received.
     * Please refer to the
     * LiteSpeed Module Developer's Guide for a more in-depth explanation of the
     * purpose of this function.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return
     */
    int (*set_resp_wait_full_body)(const lsi_session_t *pSession);

    /**
     * return 0 for no body
     *    1 for one part
     *    else for multipart
     *
     */
    int (*get_req_args_count)(const lsi_session_t *session);

    int (*get_req_arg_by_idx)(const lsi_session_t *session, int index, 
                              ls_strpair_t *pArg, char **filePath);

    int (*get_qs_args_count)(const lsi_session_t *session);

    int (*get_qs_arg_by_idx)(const lsi_session_t *session, int index, 
                              ls_strpair_t *pArg);
    
    int (*get_post_args_count)(const lsi_session_t *session);

    int (*get_post_arg_by_idx)(const lsi_session_t *session, int index, 
                              ls_strpair_t *pArg, char **filePath);
    
    int (*is_post_file_upload)(const lsi_session_t *session, int index);





    /**
     * @brief set_status_code is used to set the response status code of an HTTP session.
     * It can be used in hook point and handler processing functions,
     * but MUST be called before the response header has been sent.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] code - the http response status code.
     */
    void (*set_status_code)(const lsi_session_t *pSession, int code);

    /**
     * @brief get_status_code is used to get the response status code of an HTTP session.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return the http response status code.
     */
    int (*get_status_code)(const lsi_session_t *pSession);

    /**
     * @brief is_resp_buffer_available is used to check if the response buffer
     * is available to fill in data.  This function should be called before
     * append_resp_body or append_resp_bodyv is called.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return -1 on failure, 0 false, 1 true.
     */
    int (*is_resp_buffer_available)(const lsi_session_t *pSession);

    /**
     * @brief is_resp_buffer_gzipped is used to check if the response buffer is gzipped (compressed).
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return 0 false, 1 true.
     */
    int (*is_resp_buffer_gzippped)(const lsi_session_t *pSession);

    /**
     * @brief set_resp_buffer_gzip_flag is used to set the response buffer gzip flag.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] set - gzip flag; set 1 if gzipped (compressed), 0 to clear the flag.
     * @return 0 if success, -1 if failure.
     */
    int (*set_resp_buffer_gzip_flag)(const lsi_session_t *pSession, int set);

    /**
     * @brief append_resp_body is used to append a buffer to the response body.
     * It can ONLY be used by handler functions.
     * The data will go through filters for post processing.
     * This function should NEVER be called from a filter post processing the data.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] buf - a pointer to a buffer to be written.
     * @param[in] buflen - the size of the buffer.
     * @return the length of the request body.
     */
    int (*append_resp_body)(const lsi_session_t *pSession, const char *buf, int len);

    /**
     * @brief append_resp_bodyv is used to append an iovec to the response body.
     * It can ONLY be used by handler functions.
     * The data will go through filters for post processing.
     * this function should NEVER be called from a filter post processing the data.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] iov - the IO vector of data to be written.
     * @param[in] count - the size of the IO vector.
     * @return -1 on failure, return value of the hook filter callback function.
     */
    int (*append_resp_bodyv)(const lsi_session_t *pSession, const struct iovec *iov,
                             int count);

    /**
     * @brief send_file is used to send a file as the response body.
     * It can be used in handler processing functions.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] path - a pointer to the path string.
     * @param[in] start - file start offset.
     * @param[in] size - remaining size.
     * @return -1 or error codes from various layers of calls on failure, 0 on success.
     */
    int (*send_file)(const lsi_session_t *pSession, const char *path, int64_t start,
                     int64_t size);

    /**
    * @brief send_file is used to send a file as the response body.
    * It can be used in handler processing functions.
    *
    * @since 1.0
    *
    * @param[in] pSession - a pointer to the HttpSession.
    * @param[in] fd - file descriptor of the file to send.
    * @param[in] start - file start offset.
    * @param[in] size - remaining size.
    * @return -1 or error codes from various layers of calls on failure, 0 on success.
    */
    int (*send_file2)(const lsi_session_t *pSession, int fd, int64_t start,
                      int64_t size);

    /**
     * @brief flush flushes the connection and sends the data.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     */
    void (*flush)(const lsi_session_t *pSession);

    /**
     * @brief end_resp is called when the response sending is complete.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     */
    void (*end_resp)(const lsi_session_t *pSession);

    /**
     * @brief set_resp_content_length sets the Content Length of the response.
     * If len is -1, the response will be set to chunk encoding.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] len - the content length.
     * @return 0.
     */
    int (*set_resp_content_length)(const lsi_session_t *pSession, int64_t len);

    /**
     * @brief set_resp_header is used to set a response header.
     * If the header does not exist, it will add a new header.
     * If the header exists, it will add the header based on
     * the add_method - replace, append, merge and add new line.
     * It can be used in LSI_HKPT_RECV_RESP_HEADER and handler processing functions.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] header_id - enum #LSI_RESP_HEADER_ID defined as response-header id.
     * @param[in] name - a pointer to the header id name string.
     * @param[in] nameLen - the length of the header id name string.
     * @param[in] val - a pointer to the header string to be set.
     * @param[in] valLen - the length of the header value string.
     * @param[in] add_method - enum #LSI_HEADER_OP defined for the method of adding.
     * @return 0.
     */
    int (*set_resp_header)(const lsi_session_t *pSession, unsigned int header_id,
                           const char *name, int nameLen, const char *val, int valLen,
                           int add_method);

    /**
     * @brief set_resp_header2 is used to parse the headers first then perform set_resp_header.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] headers - a pointer to the header string to be set.
     * @param[in] len - the length of the header value string.
     * @param[in] add_method - enum #LSI_HEADER_OP defined for the method of adding.
     * @return 0.
     */
    int (*set_resp_header2)(const lsi_session_t *pSession, const char *headers,
                            int len, int add_method);

    /**
     * @brief set_resp_cookies is used to set response cookies.
     * @details The name, value, and domain are required.  If they do not exist,
     * the function will fail.
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] pName - a pointer to a cookie name.
     * @param[in] pValue - a pointer to a cookie value.
     * @param[in] path - a pointer to the path of the requested object.
     * @param[in] domain - a pointer to the domain of the requested object.
     * @param[in] expires - an expiration date for when to delete the cookie.
     * @param[in] secure - a flag that determines if communication should be
     * encrypted.
     * @param[in] httponly - a flag that determines if the cookie should be
     * limited to HTTP and HTTPS requests.
     * @return 0 if successful, else -1 if there was an error.
     */
    int (*set_resp_cookies)(const lsi_session_t *pSession, const char *pName,
                            const char *pVal,
                            const char *path, const char *domain, int expires,
                            int secure, int httponly);

    /**
     * @brief get_resp_header is used to get a response header's value in an iovec array.
     * It will try to use header_id to search the header first.
     * If header_id is not LSI_RSPHDR_UNKNOWN, the name and nameLen will NOT be checked,
     * and they can be set to NULL and 0.
     * Otherwise, if header_id is LSI_RSPHDR_UNKNOWN, then it will search through name and nameLen.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] header_id - enum #LSI_RESP_HEADER_ID defined as response-header id.
     * @param[in] name - a pointer to the header id name string.
     * @param[in] nameLen - the length of the header id name string.
     * @param[out] iov - the IO vector that contains the headers.
     * @param[in] maxIovCount - size of the IO vector.
     * @return the count of headers in the IO vector.
     */
    int (*get_resp_header)(const lsi_session_t *pSession, unsigned int header_id,
                           const char *name, int nameLen, struct iovec *iov, int maxIovCount);

    /**
     * @brief get_resp_headers_count is used to get the count of the response headers.
     * Multiple line headers will be counted as different headers.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return the number of headers in the whole response header.
     */
    int (*get_resp_headers_count)(const lsi_session_t *pSession);

    unsigned int (*get_resp_header_id)(const lsi_session_t *pSession,
                                       const char *name);

    /**
     * @brief get_resp_headers is used to get the whole response headers and store them to the iovec array.
     * If maxIovCount is smaller than the count of the headers,
     * it will only store the first maxIovCount headers.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] iov - the IO vector that contains the headers.
     * @param[in] maxIovCount - size of the IO vector.
     * @return the count of all the headers.
     */
    int (*get_resp_headers)(const lsi_session_t *pSession, struct iovec *iov_key,
                            struct iovec *iov_val, int maxIovCount);

    /**
     * @brief remove_resp_header is used to remove a response header.
     * The header_id should match the name and nameLen if it isn't -1.
     * Providing the header_id will make finding of the header quicker.  It can be used in
     * LSI_HKPT_RECV_RESP_HEADER and handler processing functions.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] header_id - enum #LSI_RESP_HEADER_ID defined as response-header id.
     * @param[in] name - a pointer to the header id name string.
     * @param[in] nameLen - the length of the header id name string.
     * @return 0.
     */
    int (*remove_resp_header)(const lsi_session_t *pSession, unsigned int header_id,
                              const char *name, int nameLen);

    /**
     * @brief get_file_path_by_uri is used to get the corresponding file path based on request URI.
     * @details The difference between this function with simply append URI to document root is that this function
     * takes context configuration into consideration. If a context points to a directory outside the document root,
     * this function can return the correct file path based on the context path.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] uri - the URI.
     * @param[in] uri_len - size of the URI.
     * @param[in,out] path - the buffer holding the result path.
     * @param[in] max_len - size of the path buffer.
     *
     * @return if success, return the size of path, if error, return -1.
     */
    int (*get_file_path_by_uri)(const lsi_session_t *pSession, const char *uri,
                                int uri_len, char *path, int max_len);

    /**
     * @brief get_mime_type_by_suffix is used to get corresponding MIME type based on file suffix.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] suffix - the file suffix, without the leading dot.
     *
     * @return the readonly MIME type string.
     */
    const char *(*get_mime_type_by_suffix)(const lsi_session_t *pSession,
                                           const char *suffix);

    /**
     * @brief set_force_mime_type is used to force the server core to use a MIME type with request in current session.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] mime - the MIME type string.
     *
     * @return 0 if success, -1 if failure.
     */
    int (*set_force_mime_type)(const lsi_session_t *pSession, const char *mime);

    /**
     * @brief get_req_file_path is used to get the static file path associated with request in current session.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in,out] pathLen - the length of the path.
     *
     * @return the file path string if success, NULL if no static file associated.
     */
    const char *(*get_req_file_path)(const lsi_session_t *pSession, int *pathLen);

    /**
     * @brief get_req_handler_type is used to get the type name of a handler assigned to this request.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     *
     * @return type name string, if no handler assigned, return NULL.
     */
    const char *(*get_req_handler_type)(const lsi_session_t *pSession);

    /**
     * @brief is_access_log_on returns if access logging is enabled for this session.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     *
     * @return 1 if access logging is enabled, 0 if access logging is disabled.
     */
    int (*is_access_log_on)(const lsi_session_t *pSession);

    /**
     * @brief set_access_log turns access logging on or off.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] on_off - set to 1 to turn on access logging, set to 0 to turn off access logging.
     */
    void (*set_access_log)(const lsi_session_t *pSession, int on_off);

    /**
     * @brief get_access_log_string returns a string for access log based on the log_pattern.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] log_pattern - the log pattern to be used; for details, please refer to Apache's custom log format.
     * @param[in,out] buf - the buffer holding the log string.
     * @param[in] bufLen - the length of buf.
     *
     * @return the length of the final log string, -1 if error.
     */
    int (*get_access_log_string)(const lsi_session_t *pSession,
                                 const char *log_pattern, char *buf, int bufLen);

    /**
     * @brief get_file_stat is used to get the status of a file.
     * @details The routine uses the system call stat(2).
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] path - the file path name.
     * @param[in] pathLen - the length of the path name.
     * @param[out] st - the structure to hold the returned file status.
     *
     * @return -1 on failure, 0 on success.
     */
    int (*get_file_stat)(const lsi_session_t *pSession, const char *path,
                         int pathLen, struct stat *st);

    /**
     * @brief is_resp_handler_aborted is used to check if the handler has been aborted.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return -1 if session does not exist, else 0.
     */
    int (*is_resp_handler_aborted)(const lsi_session_t *pSession);

    /**
     * @brief get_resp_body_buf returns a buffer that holds response body of current session.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     *
     * @return the pointer to the response body buffer, NULL if response body is not available.
     */
    void *(*get_resp_body_buf)(const lsi_session_t *pSession);

    /**
     * @brief get_req_body_buf returns a buffer that holds request body of current session.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     *
     * @return the pointer to the request body buffer, NULL if request body is not available.
     */
    void *(*get_req_body_buf)(const lsi_session_t *pSession);

    void *(*get_new_body_buf)(int64_t iInitialSize);

    /**
     * @brief get_body_buf_size returns the size of the specified body buffer.
     *
     * @since 1.0
     *
     * @param[in] pBuf - the body buffer.
     * @return the size of the body buffer, else -1 on error.
     */
    int64_t (*get_body_buf_size)(void *pBuf);

    /**
     * @brief is_body_buf_eof is used determine if the specified \e offset
     *   is the body buffer end of file.
     *
     * @since 1.0
     *
     * @param[in] pBuf - the body buffer.
     * @param[in] offset - the offset in the body buffer.
     * @return 0 false, 1 true; if \e pBuf is NULL, 1 is returned.
     */
    int (*is_body_buf_eof)(void *pBuf, int64_t offset);

    /**
     * @brief acquire_body_buf_block
     *  is used to acquire (retrieve) a portion of the body buffer.
     *
     * @since 1.0
     *
     * @param[in] pBuf - the body buffer.
     * @param[in] offset - the offset in the body buffer.
     * @param[out] size - a pointer which upon return contains the number of bytes acquired.
     * @return a pointer to the body buffer block, else NULL on error.
     *
     * @note If the \e offset is past the end of file,
     *  \e size contains zero and a null string is returned.
     */
    const char *(*acquire_body_buf_block)(void *pBuf, int64_t offset,
                                          int *size);

    /**
     * @brief release_body_buf_block
     *  is used to release a portion of the body buffer back to the system.
     * @details The entire block containing \e offset is released.
     *  If the current buffer read/write pointer is within this block,
     *  the block is \e not released.
     *
     * @since 1.0
     *
     * @param[in] pBuf - the body buffer.
     * @param[in] offset - the offset in the body buffer.
     * @return void.
     */
    void (*release_body_buf_block)(void *pBuf, int64_t offset);

    /**
     * @brief reset_body_buf
     *  resets a body buffer to be used again.
     * @details Set iWriteFlag to 1 to reset the writing offset as well as
     * the reading offset.  Otherwise, this should be 0.
     *
     * @since 1.0
     *
     * @param[in] pBuf - the body buffer.
     * @param[in] iWriteFlag - The flag specifying whether or not to reset
     *      the writing offset as well.
     * @return void.
     */
    void (*reset_body_buf)(void *pBuf, int iWriteFlag);

    /**
     * @brief append_body_buf appends (writes) data to the end of a body buffer.
     *
     * @since 1.0
     *
     * @param[in] pBuf - the body buffer.
     * @param[in] pBlock - the data buffer to append.
     * @param[in] size - the size (bytes) of the data buffer to append.
     * @return the number of bytes appended, else -1 on error.
     */
    int (*append_body_buf)(void *pBuf, const char *pBlock, int size);

    int (*set_req_body_buf)(const lsi_session_t *session, void *pBuf);

    /**
     * @brief get_body_buf_fd is used to get a file descriptor if request or response body is saved in a file-backed MMAP buffer.
     * The file descriptor should not be closed in the module.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return -1 on failure, request body file fd on success.
     */
    int (*get_body_buf_fd)(void *pBuf);

    /**
     * @brief end_resp_headers is called by a module handler when the response headers are complete.
     * @details calling this function is optional. Calling this function will trigger the
     * LSI_HKPT_RECV_RESP_HEADER hook point; if not called, LSI_HKPT_RECV_RESP_HEADER will be
     * tiggerered when adding content to response body.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     */
    void (*end_resp_headers)(const lsi_session_t *pSession);

    /**
     * @brief is_resp_headers_sent checks if the response headers are already
     * sent.
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return 1 if the headers were sent already, else 0 if not.
     */
    int (*is_resp_headers_sent)(const lsi_session_t *pSession);

    /**
     * @brief get_module_name returns the name of the module.
     *
     * @since 1.0
     *
     * @param[in] pModule - a pointer to lsi_module_t.
     * @return a const pointer to the name of the module, readonly.
     */
    const char *(*get_module_name)(const lsi_module_t *pModule);

    /**
     * @brief get_multiplexer gets the event multiplexer for the main event loop.
     *
     * @since 1.0
     * @return a pointer to the multiplexer used by the main event loop.
     */
    void *(*get_multiplexer)();

    ls_edio_t *(*edio_reg)(int fd, edio_evt_cb evt_cb,
                           edio_timer_cb timer_cb, short events, void *pParam);

    void (*edio_remove)(ls_edio_t *pHandle);

    void (*edio_modify)(ls_edio_t *pHandle, short events, int add_remove);


    //return 0 is YES, and 1 is deny
    int (*get_client_access_level)(const lsi_session_t *session);

    /**
     * @brief is_suspended returns if a session is in suspended mode.
     *
     * @since 1.0
     * @param[in] pSession - a pointer to the HttpSession.
     * @return 0 false, -1 invalid pSession, none-zero true.
     */
    int (*is_suspended)(const lsi_session_t *session);

    /**
     * @brief resume continues processing of the suspended session.
     *    this should be at the end of a function call
     *
     * @since 1.0
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in] retcode - the result that a hook function returns as if there is no suspend/resume happened.
     * @return -1 failed to resume, 0 successful.
     */
    int (*resume)(const lsi_session_t *session, int retcode);

    int (* exec_ext_cmd)(const lsi_session_t *pSession, const char *cmd, int len,
                         evtcb_pf cb, const long lParam, void *pParam);

    char *(* get_ext_cmd_res_buf)(const lsi_session_t *pSession, int *length);



#ifdef notdef
    int (*is_subrequest)(const lsi_session_t *session);
#endif

    /**
     * @brief get_cur_time gets the current system time.
     *
     * @since 1.0
     *
     * @param[in,out] usec - if not NULL,
     *  upon return contains the microseconds of the current time.
     * @return the seconds of the current time
     *  (the number of seconds since the Epoch, time(2)).
     */
    time_t (*get_cur_time)(int32_t *usec);

    /**
     * @brief get_vhost_count gets the count of Virtual Hosts in the system.
     *
     * @since 1.0
     *
     * @return the count of Virtual Hosts.
     */
    int (*get_vhost_count)();

    /**
     * @brief get_vhost gets a Virtual Host object.
     *
     * @since 1.0
     *
     * @param[in] index - the index of the Virtual Host, starting from 0.
     * @return a pointer to the Virtual Host object.
     */
    const void *(*get_vhost)(int index);

    /**
     * @brief set_vhost_module_data
     *  is used to set the module data for a Virtual Host.
     * @details The routine is similar to set_module_data,
     *  but may be used without reference to a session.
     *
     * @since 1.0
     *
     * @param[in] vhost - a pointer to the Virtual Host.
     * @param[in] pModule - a pointer to an lsi_module_t struct.
     * @param[in] data - a pointer to the user defined data.
     * @return -1 on failure, 0 on success.
     *
     * @see set_module_data
     */
    int (* set_vhost_module_data)(const void *vhost,
                                  const lsi_module_t *pModule, void *data);

    /**
     * @brief get_vhost_module_data
     *  gets the module data which was set by set_vhost_module_data.
     * The return value is a pointer to the user's own data structure.
     * @details The routine is similar to get_module_data,
     *  but may be used without reference to a session.
     *
     * @since 1.0
     *
     * @param[in] vhost - a pointer to the Virtual Host.
     * @param[in] pModule - a pointer to an lsi_module_t struct.
     * @return NULL on failure, a pointer to the user defined data on success.
     *
     * @see get_module_data
     */
    void       *(* get_vhost_module_data)(const void *vhost,
                                          const lsi_module_t *pModule);

    /**
     * @brief get_vhost_module_param
     *  gets the user defined module parameters which are parsed by
     *  the callback parse_config and pointed to in the struct lsi_confparser_t.
     *
     * @since 1.0
     *
     * @param[in] vhost - a pointer to the Virtual Host.
     * @param[in] pModule - a pointer to an lsi_module_t struct.
     * @return NULL on failure,
     *  a pointer to the user-defined configuration data on success.
     *
     * @see get_config
     */
    void       *(* get_vhost_module_param)(const void *vhost,
                                           const lsi_module_t *pModule);

    /**
     * @brief get_session_pool gets the session pool to allow modules to allocate from.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @return a pointer to the session pool.
     */
    ls_xpool_t *(*get_session_pool)(const lsi_session_t *pSession);

    /**
     * @brief get_local_sockaddr
     *  gets the socket address in a character string format.
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[out] pIp - a pointer to the returned address string.
     * @param[in] maxLen - the size of the buffer at \e pIp.
     * @return the length of the string on success,
     *  else 0 for system errors, or -1 for bad parameters.
     */
    int (* get_local_sockaddr)(const lsi_session_t *pSession, char *pIp, int maxLen);


    /**
     * @brief handoff_fd return a duplicated file descriptor associated with current session and
     *    all data received on this file descriptor, including parsed request headers
     *    and data has not been processed.
     *    After this function call the server core will stop processing current session and closed
     *    the original file descriptor. The session object will become invalid.
     *
     *
     * @since 1.0
     *
     * @param[in] pSession - a pointer to the HttpSession.
     * @param[in,out] pData - a pointer to a pointer pointing to the buffer holding data received so far
     *     The buffer is allocated by server core, must be released by the caller of this function with free().
     * @param[in,out] pDataLen - a pointer to the variable receive the size of the buffer.
     * @return a file descriptor if success, -1 if failed. the file descriptor is dupped from the original
     *         file descriptor, it should be closed by the caller of this function when done.
     */
    int (*handoff_fd)(const lsi_session_t *pSession, char **pData, int *pDataLen);

    /** @since 1.0
     * @param[in] level - lsi_confparser_level
     * @param[in] pVarible - varible of the Server/Listener/VHost or URI of the Context
     * @param[in] buf - a buffer to store the result
     * @param[in] max_len - length of the buf
     * @return return the length written to the buf
     */
    int (*expand_current_server_varible)(int level, const char *pVarible,
                                         char *buf, int max_len);

    /**
     * @brief module_log is used to write the formatted log to the error log associated with a module.
     * @details session ID will be added to the log message automatically when session is not NULL.
     * This function will not add a trailing \\n to the end.
     *
     * @since 1.0
     *
     * @param[in] pModule - pointer to module object, module name is logged.
     * @param[in] pSession - current session, log file, and session ID are based on session.
     * @param[in] level - enum defined in log level definitions #LSI_LOG_LEVEL.
     * @param[in] fmt - formatted string.
     */
    void (*module_log)(const lsi_module_t *pModule, const lsi_session_t *pSession, 
                       int level, const char *fmt, ...)
#if __GNUC__
        __attribute__((format(printf, 4, 5)))
#endif
        ;

    /**
     * @brief c_log is used to write the formatted log to the error log associated with a component.
     * @details session ID will be added to the log message automatically when session is not NULL.
     * This function will not add a trailing \\n to the end.
     *
     * @since 1.0
     *
     * @param[in] pComponentName - pointer to the name of the component.
     * @param[in] pSession - current session, log file, and session ID are based on session.
     * @param[in] level - enum defined in log level definitions #LSI_LOG_LEVEL.
     * @param[in] fmt - formatted string.
     */
    void (*c_log)(const char *pComponentName, const lsi_session_t *pSession, 
                       int level, const char *fmt, ...)
#if __GNUC__
        __attribute__((format(printf, 4, 5)))
#endif
        ;
        
    /**
     *
     * @brief _log_level_ptr is the address of variable that stores the level 
     *    of logging that server core uses,
     *    the variable controls the level of details of logging messages.
     *    its value is defined in LSI_LOG_LEVEL, 
     *    range is from LSI_LOG_ERROR to LSI_LOG_TRACE.
     *
     */    
    const int *_log_level_ptr;

};

/**
 *
 * @brief  make LSIAPI functions globally available.
 * @details g_api is a global variable, it can be accessed from all modules to make API calls.
 *
 * @since 1.0
 */
extern const lsi_api_t *g_api;


#define LSI_LOG_ENABLED(level) (*g_api->_log_level_ptr >= level)


#define LSI_LOG(level, session, ...) \
    do { \
        if (LSI_LOG_ENABLED(level)) g_api->log(session, level, __VA_ARGS__); \
    } while(0) 

#define LSI_LOGRAW(...) g_api->lograw(__VA_ARGS__)

#define LSI_LOGIO(session, ...) LSI_LOG(LSI_LOG_TRACE, session, __VA_ARGS__)

#define LSI_DBGH(session, ...) LSI_LOG(LSI_LOG_DEBUG_HIGH, session, __VA_ARGS__)

#define LSI_DBGM(session, ...) LSI_LOG(LSI_LOG_DEBUG_MEDIUM, session, __VA_ARGS__)

#define LSI_DBGL(session, ...) LSI_LOG(LSI_LOG_DEBUG_LOW, session, __VA_ARGS__)

#define LSI_DBG(session, ...) LSI_LOG(LSI_LOG_DEBUG,  session, __VA_ARGS__)
#define LSI_INF(session, ...) LSI_LOG(LSI_LOG_INFO,   session, __VA_ARGS__)
#define LSI_NOT(session, ...) LSI_LOG(LSI_LOG_NOTICE, session, __VA_ARGS__)
#define LSI_WRN(session, ...) LSI_LOG(LSI_LOG_WARN,   session, __VA_ARGS__)
#define LSI_ERR(session, ...) LSI_LOG(LSI_LOG_ERROR,  session, __VA_ARGS__)


#define LSM_LOG_ENABLED(m, l) \
    (*g_api->_log_level_ptr >= l && MODULE_LOG_LEVEL(m) >= l)


#define LSM_LOG(mod, level, session, ...) \
    do { \
        if (LSM_LOG_ENABLED(mod, level)) \
            g_api->module_log(mod, session, level, __VA_ARGS__); \
    } while(0) 

#define LSM_LOGRAW(...) g_api->lograw(__VA_ARGS__)

#define LSM_LOGIO(m, s, ...) LSM_LOG(m, LSI_LOG_TRACE, s, __VA_ARGS__)

#define LSM_DBGH(m, s, ...) LSM_LOG(m, LSI_LOG_DEBUG_HIGH, s, __VA_ARGS__)

#define LSM_DBGM(m, s, ...) LSM_LOG(m, LSI_LOG_DEBUG_MEDIUM, s, __VA_ARGS__)

#define LSM_DBGL(m, s, ...) LSM_LOG(m, LSI_LOG_DEBUG_LOW, s, __VA_ARGS__)

#define LSM_DBG(m, s, ...) LSM_LOG(m, LSI_LOG_DEBUG,  s, __VA_ARGS__)
#define LSM_INF(m, s, ...) LSM_LOG(m, LSI_LOG_INFO,   s, __VA_ARGS__)
#define LSM_NOT(m, s, ...) LSM_LOG(m, LSI_LOG_NOTICE, s, __VA_ARGS__)
#define LSM_WRN(m, s, ...) LSM_LOG(m, LSI_LOG_WARN,   s, __VA_ARGS__)
#define LSM_ERR(m, s, ...) LSM_LOG(m, LSI_LOG_ERROR,  s, __VA_ARGS__)


#define DECL_COMPONENT_LOG(id) \
    static const char *s_comp_log_id = id; 

#define LSC_LOG_ENABLED(l) \
    (*g_api->_log_level_ptr >= l)


#define LSC_LOG(level, session, ...) \
    do { \
        if (LSC_LOG_ENABLED(level)) \
            g_api->c_log(s_comp_log_id, session, level, __VA_ARGS__); \
    } while(0) 

#define LSC_LOGRAW(...) g_api->lograw(__VA_ARGS__)

#define LSC_LOGIO(s, ...) LSC_LOG(LSI_LOG_TRACE, s, __VA_ARGS__)

#define LSC_DBGH(s, ...) LSC_LOG(LSI_LOG_DEBUG_HIGH, s, __VA_ARGS__)

#define LSC_DBGM(s, ...) LSC_LOG(LSI_LOG_DEBUG_MEDIUM, s, __VA_ARGS__)

#define LSC_DBGL(s, ...) LSC_LOG(LSI_LOG_DEBUG_LOW, s, __VA_ARGS__)

#define LSC_DBG(s, ...) LSC_LOG(LSI_LOG_DEBUG,  s, __VA_ARGS__)
#define LSC_INF(s, ...) LSC_LOG(LSI_LOG_INFO,   s, __VA_ARGS__)
#define LSC_NOT(s, ...) LSC_LOG(LSI_LOG_NOTICE, s, __VA_ARGS__)
#define LSC_WRN(s, ...) LSC_LOG(LSI_LOG_WARN,   s, __VA_ARGS__)
#define LSC_ERR(s, ...) LSC_LOG(LSI_LOG_ERROR,  s, __VA_ARGS__)

#ifdef __cplusplus
}
#endif


#endif //LS_MODULE_H
