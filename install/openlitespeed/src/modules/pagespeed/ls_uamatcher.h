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
#ifndef LS_UA_MATCHER_H_
#define LS_UA_MATCHER_H_

#include <util/tsingleton.h>
#include <lsdef.h>
#include <lsr/ls_hash.h>
#include <pagespeed/kernel/http/user_agent_matcher.h>


using namespace net_instaweb;


enum UA_DEVICE_TYPE
{
//two bit for device type
    ua_unknown_device =    0,
    ua_device_mobile,
    ua_device_tablet,//   2
    ua_device_desktop,//  3
};

// 1<<2 not used
#define ua_android                          1<<3
#define ua_ios                              1<<4
#define ua_ie_user_agents                   1<<5
#define ua_mobilization_user_agents         1<<6

#define ua_supports_image_inlining          1<<7
#define ua_supports_lazyload_images         1<<8
#define ua_defer_js_whitelist               1<<9
#define ua_legacy_webp                      1<<10

//Latest version of PSOL has it, cuurent supportted not
//#define ua_pagespeed_insights               1<<11

#define ua_supports_webp_lossless_alpha     1<<12
#define ua_supports_webp_animated           1<<13
#define ua_supports_dns_prefetch            1<<14

struct ua_hash_item {
    char       *ua; //deep copy
    uint32_t    code;
};

class LsUAMatcher : public TSingleton<LsUAMatcher>
{
    friend class TSingleton<LsUAMatcher>;
public:
    LsUAMatcher();
    ~LsUAMatcher();
    
    uint32_t getUaCode(const char *ua_str);
    
    UA_DEVICE_TYPE getDeviceType(uint32_t code);
    UA_DEVICE_TYPE getDeviceType(const char *ua_str)
    {
        return getDeviceType(getUaCode(ua_str));
    }
    
    
    bool testbit(uint32_t code, int flagBit)
    {
        return (code & flagBit ? true : false);
    }

private:
    UserAgentMatcher    *m_pUAMatcher;
    ls_hash_t           *m_pHash;

    LS_NO_COPY_ASSIGN(LsUAMatcher);
};


#endif  // LS_UA_MATCHER_H_
