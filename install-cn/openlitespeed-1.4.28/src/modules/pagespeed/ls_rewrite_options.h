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
#ifndef LSI_REWRITE_OPTIONS_H_
#define LSI_REWRITE_OPTIONS_H_

#include "pagespeed.h"
#include <lsdef.h>

#include <vector>


#include "net/instaweb/rewriter/public/rewrite_options.h"
#include "pagespeed/kernel/base/message_handler.h"
#include "pagespeed/kernel/base/ref_counted_ptr.h"
#include "pagespeed/kernel/base/stl_util.h"          // for STLDeleteElements
#include "pagespeed/system/system_rewrite_options.h"

namespace net_instaweb
{
class LsiRewriteDriverFactory;

class LsiRewriteOptions : public SystemRewriteOptions
{
public:
    static void Initialize();
    static void Terminate();

    LsiRewriteOptions(const StringPiece &description,
                      ThreadSystem *thread_system);
    explicit LsiRewriteOptions(ThreadSystem *thread_system);
    virtual ~LsiRewriteOptions() { }

    const char *ParseAndSetOptions(
        StringPiece *args, int n_args, MessageHandler *handler,
        LsiRewriteDriverFactory *driver_factory, OptionScope scope);

    virtual LsiRewriteOptions *Clone() const;

    static const LsiRewriteOptions *DynamicCast(const RewriteOptions
            *instance);
    static LsiRewriteOptions *DynamicCast(RewriteOptions *instance);

    const GoogleString &GetStatisticsPath() const
    {
        return m_sStatisticsPath.value();
    }
    const GoogleString &GetGlobalStatisticsPath() const
    {
        return m_sGlobalStatisticsPath.value();
    }
    const GoogleString &GetConsolePath() const
    {
        return m_sConsolePath.value();
    }
    const GoogleString &GetMessagesPath() const
    {
        return m_sMessagesPath.value();
    }
    const GoogleString &GetAdminPath() const
    {
        return m_sAdminPath.value();
    }
    const GoogleString &GetGlobalAdminPath() const
    {
        return m_sGlobalAdminPath.value();
    }

private:
    OptionSettingResult ParseAndSetOptions0(
        StringPiece directive, GoogleString *msg, MessageHandler *handler);

    virtual OptionSettingResult ParseAndSetOptionFromName1(
        StringPiece name, StringPiece arg,
        GoogleString *msg, MessageHandler *handler);

    static Properties *m_pProperties;
    static void AddProperties();
    void Init();

    // Add an option to lsi_properties_
    template<class OptionClass>
    static void AddLsiOption(typename OptionClass::ValueType default_value,
                             OptionClass LsiRewriteOptions::*offset,
                             const char *id,
                             StringPiece option_name,
                             OptionScope scope,
                             const char *help,
                             bool safe_to_print)
    {
        AddProperty(default_value, offset, id, option_name, scope, help,
                    safe_to_print, m_pProperties);
    }

    Option<GoogleString> m_sStatisticsPath;
    Option<GoogleString> m_sGlobalStatisticsPath;
    Option<GoogleString> m_sConsolePath;
    Option<GoogleString> m_sMessagesPath;
    Option<GoogleString> m_sAdminPath;
    Option<GoogleString> m_sGlobalAdminPath;

    // Helper for ParseAndSetOptions.  Returns whether the two directives equal,
    // ignoring case.
    bool IsDirective(StringPiece config_directive,
                     StringPiece compare_directive);

    // Returns a given option's scope.
    RewriteOptions::OptionScope GetOptionScope(StringPiece option_name);


    LS_NO_COPY_ASSIGN(LsiRewriteOptions);
};

}  // namespace net_instaweb

#endif  // LSI_REWRITE_OPTIONS_H_

