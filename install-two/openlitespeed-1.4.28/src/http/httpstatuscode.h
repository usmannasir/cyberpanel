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
#ifndef HTTPSTATUSCODE_H
#define HTTPSTATUSCODE_H


#include <lsdef.h>
#include <util/tsingleton.h>

#include <assert.h>
#include <stddef.h>

enum
{
    SC_100 = 1,
    SC_101 ,
    SC_102 ,

    SC_200 ,
    SC_201 ,
    SC_202 ,
    SC_203 ,
    SC_204 ,
    SC_205 ,
    SC_206 ,
    SC_207 ,
    SC_208 ,

    SC_300 ,
    SC_301 ,
    SC_302 ,
    SC_303 ,
    SC_304 ,
    SC_305 ,
    SC_306 ,
    SC_307 ,
    SC_308 ,

    SC_400 ,
    SC_401 ,
    SC_402 ,
    SC_403 ,
    SC_404 ,
    SC_405 ,
    SC_406 ,
    SC_407 ,
    SC_408 ,
    SC_409 ,
    SC_410 ,
    SC_411 ,
    SC_412 ,
    SC_413 ,
    SC_414 ,
    SC_415 ,
    SC_416 ,
    SC_417 ,
    SC_418 ,
    SC_419 ,
    SC_420 ,
    SC_421 ,
    SC_422 ,
    SC_423 ,
    SC_424 ,

    SC_500 ,
    SC_501 ,
    SC_502 ,
    SC_503 ,
    SC_504 ,
    SC_505 ,
    SC_506 ,
    SC_507 ,
    SC_508 ,
    SC_509 ,
    SC_510 ,
    SC_END
};

class StatusCode
{
    friend class HttpStatusCode;

    const char *m_status;
    int          status_size;
    char        *m_pHeaderBody;
    int          m_iBodySize;
public:

    StatusCode(int code, const char *pStatus, const char *body);
    ~StatusCode();
    LS_NO_COPY_ASSIGN(StatusCode);
};

typedef int http_sc_t;

class HttpStatusCode : public TSingleton<HttpStatusCode>
{
    friend class TSingleton<HttpStatusCode>;

    static int  s_codeToIndex[7];

    StatusCode *m_aSC[ SC_END ];

    HttpStatusCode();
    ~HttpStatusCode();
public:
    enum
    {
        _100_Continue ,
        _101_Switching_Protocols = 101,
        _102_Processing = 102,
        _200_OK = 200,
        _201_Created = 201,
        _202_Accepted = 202,
        _203_Non_Authoritative = 203,
        _204_No_Content = 204,
        _205_Reset_Content = 205,
        _206_Partial_Content = 206,
        _207_Multi_Status = 207,
        _208_Already_Reported = 208,
        _300_Multiple_Choices = 300,
        _301_Moved_Permanently = 301,
        _302_Found = 302,
        _303_See_Other = 303,
        _304_Not_Modified = 304,
        _305_Use_Proxy = 305,
        _307_Temporary_Redirect = 307,
        _308_Permanent_Redirect = 308,
        _400_Bad_Request = 400,
        _401_Unauthorized = 401,
        _402_Payment_Required = 402,
        _403_Forbidden = 403,
        _404_Not_Found = 404,
        _405_Method_Not_Allowed = 405,
        _406_Not_Acceptable = 406,
        _407_Proxy_Auth_Required = 407,
        _408_Request_Timeout = 408,
        _409_Conflict = 409,
        _410_Gone = 410,
        _411_Length_Required = 411,
        _412_Precondition_Failed = 412,
        _413_Entity_Too_Large = 413,
        _414_URI_Too_Large = 414,
        _415_Unsupported_Media_Type = 415,
        _416_Range_Not_Satisfiable = 416,
        _417_Expectation_Failed = 417,
        _418_reauthentication_required = 418,
        _419_proxy_reauthentication_required = 419,
        _420_Policy_Not_Fulfilled = 420,
        _421_Bad_Mapping = 421,
        _422_Unprocessable_Entity = 422,
        _423_Locked = 423,
        _424_Failed_Dependency = 424,
        _500_Internal_Error = 500,
        _501_Not_Implemented = 501,
        _502_Bad_Gateway = 502,
        _503_Service_Unavailable = 503,
        _504_Gateway_Timeout = 504,
        _505_Not_Supported = 505,
        _506_Loop_Detected = 506,
        _507_Insufficient_Storage = 507,
        _509_Bandwidth_Limit_Exceeded = 509,
        _510_Not_Extended = 510

    };

    const char *getCodeString(http_sc_t code)
    {
        return m_aSC[code]->m_status;
    }
    int getCodeStringLen(http_sc_t code)
    {
        return m_aSC[code]->status_size;
    }
    const char *getHeaders(http_sc_t code)
    {
        return m_aSC[code]->m_pHeaderBody;
    }
    const char *getRealHtml(http_sc_t code)
    {
        return (m_aSC[code]->m_pHeaderBody) ? m_aSC[code]->m_pHeaderBody : NULL;
    }
    int getBodyLen(http_sc_t code)
    {
        return m_aSC[code]->m_iBodySize;
    }

    int codeToIndex(const char *code);

    int codeToIndex(unsigned int real_code)
    {
        int index = real_code % 100;
        int offset = real_code / 100;
        if ((offset < 6)
            && (index < s_codeToIndex[offset + 1] - s_codeToIndex[offset]))
            return s_codeToIndex[offset] + index;
        else
            return LS_FAIL;
    }

    int indexToCode(unsigned int index)
    {
        if (index < 1 || index >= SC_END)
            return LS_FAIL;

        int iStage;
        for (iStage = 2; iStage < 7; ++iStage)
        {
            if (index < (unsigned int)s_codeToIndex[iStage])
                break;
        }
        --iStage;
        return iStage * 100 + index - s_codeToIndex[iStage];
    }


    bool fatalError(http_sc_t code)
    {
        return ((code == SC_400) || (code >= SC_500)
                || (code == SC_408)
                || ((code >= SC_411) && (code <= SC_415))
               );
    }

    LS_NO_COPY_ASSIGN(HttpStatusCode);
};

#endif
