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
#include <ls_uamatcher.h>
#include <string.h>

LsUAMatcher::LsUAMatcher()
{
    m_pHash = ls_hash_new(50, ls_hash_hfcistring, ls_hash_cmpcistring, NULL);
    m_pUAMatcher = new net_instaweb::UserAgentMatcher();
}

LsUAMatcher::~LsUAMatcher()
{
    ls_hash_iter it;
    for (it = ls_hash_begin(m_pHash); it != ls_hash_end(m_pHash); 
         it = ls_hash_next(m_pHash, it))
    {
        ua_hash_item *pItem = (ua_hash_item *)ls_hash_getdata(it);
        free(pItem->ua);
        delete pItem;
    }
    
    ls_hash_delete(m_pHash);
    delete m_pUAMatcher;
}

UA_DEVICE_TYPE LsUAMatcher::getDeviceType(uint32_t code)
{
    UA_DEVICE_TYPE type = ua_unknown_device;
    return (UA_DEVICE_TYPE)(type + (int)(code & 0x03));
}

uint32_t LsUAMatcher::getUaCode(const char *ua_str)
{
    uint32_t code = 0;
    ls_hash_iter it;
    if ((it = ls_hash_find(m_pHash, (void *)ua_str)) != NULL)
    {
        ua_hash_item *pItem = (ua_hash_item *)ls_hash_getdata(it);
        code = pItem->code;
    }
    else
    {
        ua_hash_item *pItem = new ua_hash_item;
        pItem->ua = ::strdup(ua_str);
        pItem->code = 0;
        StringPiece ua = ua_str;
        
        UserAgentMatcher::DeviceType type = m_pUAMatcher->GetDeviceTypeForUA(ua);
        switch(type)
        {
            case UserAgentMatcher::kMobile:
                pItem->code |= ua_device_mobile;
                break;
            case UserAgentMatcher::kTablet:
                pItem->code |= ua_device_tablet;
                break;
            case UserAgentMatcher::kDesktop:
                pItem->code |= ua_device_desktop;
                break;
            default:
                //pItem->code |= ua_unknown_device;
                break;
        }
        
        if (m_pUAMatcher->SupportsImageInlining(ua))
            pItem->code |= ua_supports_image_inlining;

        if (m_pUAMatcher->SupportsLazyloadImages(ua))
            pItem->code |= ua_supports_lazyload_images;
                
        if (m_pUAMatcher->SupportsJsDefer(ua, true))
            pItem->code |= ua_defer_js_whitelist;
              
        if (m_pUAMatcher->LegacyWebp(ua))
            pItem->code |= ua_legacy_webp;

//         if (m_pUAMatcher->InsightsWebp(ua))
//             pItem->code |= ua_pagespeed_insights;
            
        if (m_pUAMatcher->SupportsWebpLosslessAlpha(ua))
            pItem->code |= ua_supports_webp_lossless_alpha;
                
        if (m_pUAMatcher->SupportsWebpAnimated(ua))
            pItem->code |= ua_supports_webp_animated;  
                
        if (m_pUAMatcher->SupportsDnsPrefetch(ua))
            pItem->code |= ua_supports_dns_prefetch;
                
        if (m_pUAMatcher->IsAndroidUserAgent(ua))
            pItem->code |= ua_android;

        if (m_pUAMatcher->IsiOSUserAgent(ua))
            pItem->code |= ua_ios;
                
        if (m_pUAMatcher->SupportsMobilization(ua))
            pItem->code |= ua_mobilization_user_agents;
                
        if (m_pUAMatcher->IsIe(ua_str))
            pItem->code |= ua_ie_user_agents;
        code = pItem->code;
        
        ls_hash_insert(m_pHash, (void *)pItem->ua, (void *)pItem);
    }
    
    return code;
}

//Test case
void UAMatcherTest()
{
    LsUAMatcher &match = LsUAMatcher::getInstance();
    
    //imageinline
    uint32_t code1 = match.getUaCode("*iPhone*");
    //DEBUG to check if it got from stored hashtable
    code1 = match.getUaCode("*iPhone*");
    
    uint32_t code2 = match.getUaCode("*Chrome/*");
    uint32_t code3 = match.getUaCode("*Firefox/*");
    uint32_t code4 = match.getUaCode("*Safari*");
    uint32_t code5 = match.getUaCode("webp");
    assert(match.testbit(code1, ua_supports_image_inlining));
    assert(match.testbit(code2, ua_supports_image_inlining));
    assert(match.testbit(code3, ua_supports_image_inlining));
    assert(match.testbit(code4, ua_supports_image_inlining));
    assert(match.testbit(code5, ua_supports_image_inlining));
    
    assert(match.getDeviceType(code1) == ua_device_mobile);
    //assert(match.getDeviceType("*Android 3.*") == ua_device_mobile);
    assert(match.getDeviceType("*Kindle Fire*") == ua_device_tablet);
    assert(match.getDeviceType("*iPad*") == ua_device_tablet);
    
    
    uint32_t code6 = match.getUaCode("*iPhone*");
    uint32_t code7 = match.getUaCode("*Chrome/*");
    uint32_t code8 = match.getUaCode("*Firefox/*");
    assert(code1 == code6);
    assert(code2 == code7);
    assert(code3 == code8);
    
    code1 = match.getUaCode("*iPhone*");
    assert(match.testbit(code1, ua_ios));
    code1 = match.getUaCode("*iPad*");
    assert(match.testbit(code1, ua_ios));
    code1 = match.getUaCode("*Android 3.*");
    assert(match.testbit(code1, ua_android));
    
    
    
    
    code1 = match.getUaCode("*iPhone*");
    assert(match.testbit(code1, ua_supports_lazyload_images));
    
    uint32_t code9 = match.getUaCode("*Opera Mini*");
    assert(!match.testbit(code9, ua_supports_lazyload_images));
    
    
    assert(match.testbit(code7, ua_supports_dns_prefetch));
    assert(match.testbit(code8, ua_supports_dns_prefetch));
    assert(!match.testbit(code9, ua_supports_dns_prefetch));
    
    
    
    
    
    
}




