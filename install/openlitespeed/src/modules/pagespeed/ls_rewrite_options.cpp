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
#include "ls_rewrite_options.h"
#include "ls_rewrite_driver_factory.h"
#include "out/Release/obj/gen/net/instaweb/public/version.h"
#include "net/instaweb/rewriter/public/file_load_policy.h"
#include "net/instaweb/rewriter/public/rewrite_options.h"
#include "pagespeed/kernel/base/message_handler.h"
#include "pagespeed/kernel/base/timer.h"
#include "pagespeed/system/system_caches.h"

namespace net_instaweb
{
const char kStatisticsPath[] = "StatisticsPath";
const char kGlobalStatisticsPath[] = "GlobalStatisticsPath";
const char kConsolePath[] = "ConsolePath";
const char kMessagesPath[] = "MessagesPath";
const char kAdminPath[] = "AdminPath";
const char kGlobalAdminPath[] = "GlobalAdminPath";

const char *const server_only_options[] =
{
    "FetcherTimeoutMs",
    "FetchProxy",
    "ForceCaching",
    "GeneratedFilePrefix",
    "ImgMaxRewritesAtOnce",
    "InheritVHostConfig",
    "InstallCrashHandler",
    "MessageBufferSize",
    "NumRewriteThreads",
    "NumExpensiveRewriteThreads",
    "StaticAssetPrefix",
    "TrackOriginalContentLength",
    "UsePerVHostStatistics",
    "BlockingRewriteRefererUrls",
    "CreateSharedMemoryMetadataCache",
    "LoadFromFile",
    "LoadFromFileMatch",
    "LoadFromFileRule",
    "LoadFromFileRuleMatch"
};

// Options that can only be used in the main (http) option scope.
const char *const main_only_options[] =
{
};



RewriteOptions::Properties *LsRewriteOptions::m_pProperties = NULL;

LsRewriteOptions::LsRewriteOptions(const StringPiece &description,
                                     ThreadSystem *thread_system)
    : SystemRewriteOptions(description, thread_system)
{
    Init();
}

LsRewriteOptions::LsRewriteOptions(ThreadSystem *thread_system)
    : SystemRewriteOptions(thread_system)
{
    Init();
}

void LsRewriteOptions::Init()
{
    DCHECK(m_pProperties != NULL)
            << "Call LsiRewriteOptions::Initialize() before construction";
    InitializeOptions(m_pProperties);
}

void LsRewriteOptions::AddProperties()
{
    // ls-specific options.
    AddLsiOption(
        "", &LsRewriteOptions::m_sStatisticsPath, "nsp", kStatisticsPath,
        kServerScope, "Set the statistics path. Ex: /lsi_pagespeed_statistics",
        false);
    AddLsiOption(
        "", &LsRewriteOptions::m_sGlobalStatisticsPath, "ngsp",
        kGlobalStatisticsPath, kProcessScope,
        "Set the global statistics path. Ex: /lsi_pagespeed_global_statistics",
        false);
    AddLsiOption(
        "", &LsRewriteOptions::m_sConsolePath, "ncp", kConsolePath, kServerScope,
        "Set the console path. Ex: /pagespeed_console",
        false);
    AddLsiOption(
        "", &LsRewriteOptions::m_sMessagesPath, "nmp", kMessagesPath,
        kServerScope, "Set the messages path.  Ex: /lsi_pagespeed_message",
        false);
    AddLsiOption(
        "", &LsRewriteOptions::m_sAdminPath, "nap", kAdminPath,
        kServerScope, "Set the admin path.  Ex: /pagespeed_admin",
        false);
    AddLsiOption(
        "", &LsRewriteOptions::m_sGlobalAdminPath, "ngap", kGlobalAdminPath,
        kProcessScope, "Set the global admin path.  Ex: /pagespeed_global_admin",
        false);

    MergeSubclassProperties(m_pProperties);

    // Default properties are global but to set them the current API requires
    // a RewriteOptions instance and we're in a static method.
    LsRewriteOptions dummy_config(NULL);
    dummy_config.set_default_x_header_value(kModPagespeedVersion);
}

void LsRewriteOptions::Initialize()
{
    if (Properties::Initialize(&m_pProperties))
    {
        SystemRewriteOptions::Initialize();
        AddProperties();
    }
}

void LsRewriteOptions::Terminate()
{
    if (Properties::Terminate(&m_pProperties))
        SystemRewriteOptions::Terminate();
}

bool LsRewriteOptions::IsDirective(StringPiece config_directive,
                                    StringPiece compare_directive)
{
    return StringCaseEqual(config_directive, compare_directive);
}

RewriteOptions::OptionScope LsRewriteOptions::GetOptionScope(
    StringPiece option_name)
{
    unsigned int i;
    unsigned int size = sizeof(main_only_options) / sizeof(char *);

    for (i = 0; i < size; i++)
    {
        if (StringCaseEqual(main_only_options[i], option_name))
            return kProcessScopeStrict;
    }

    size = sizeof(server_only_options) / sizeof(char *);

    for (i = 0; i < size; i++)
    {
        if (StringCaseEqual(server_only_options[i], option_name))
            return kServerScope;
    }

    // This could be made more efficient if RewriteOptions provided a map allowing
    // access of options by their name. It's not too much of a worry at present
    // since this is just during initialization.
    for (OptionBaseVector::const_iterator it = all_options().begin();
         it != all_options().end(); ++it)
    {
        RewriteOptions::OptionBase *option = *it;

        if (option->option_name() == option_name)
        {
            // We treat kProcessScope as kProcessScopeStrict, failing to start if an
            // option is out of place.
            return option->scope() == kProcessScope ? kProcessScopeStrict
                   : option->scope();
        }
    }

    return kDirectoryScope;
}

RewriteOptions::OptionSettingResult LsRewriteOptions::ParseAndSetOptions0(
    StringPiece directive, GoogleString *msg, MessageHandler *handler)
{
    if (IsDirective(directive, "on"))
        set_enabled(RewriteOptions::kEnabledOn);
    else if (IsDirective(directive, "off"))
        set_enabled(RewriteOptions::kEnabledOff);
    else if (IsDirective(directive, "unplugged"))
        set_enabled(RewriteOptions::kEnabledUnplugged);
    else
        return RewriteOptions::kOptionNameUnknown;

    return RewriteOptions::kOptionOk;
}

RewriteOptions::OptionSettingResult
LsRewriteOptions::ParseAndSetOptionFromName1(
    StringPiece name, StringPiece arg,
    GoogleString *msg, MessageHandler *handler)
{
    // FileCachePath needs error checking.
    if (StringCaseEqual(name, kFileCachePath))
    {
        if (!StringCaseStartsWith(arg, "/"))
        {
            *msg = "must start with a slash";
            return RewriteOptions::kOptionValueInvalid;
        }
    }

    return SystemRewriteOptions::ParseAndSetOptionFromName1(
               name, arg, msg, handler);
}

template <class DriverFactoryT>
RewriteOptions::OptionSettingResult ParseAndSetOptionHelper(
    StringPiece option_value,
    DriverFactoryT *driver_factory,
    void (DriverFactoryT::*set_option_method)(bool))
{
    bool parsed_value;

    if (StringCaseEqual(option_value, "on") ||
        StringCaseEqual(option_value, "true"))
        parsed_value = true;
    else if (StringCaseEqual(option_value, "off") ||
             StringCaseEqual(option_value, "false"))
        parsed_value = false;
    else
        return RewriteOptions::kOptionValueInvalid;

    (driver_factory->*set_option_method)(parsed_value);
    return RewriteOptions::kOptionOk;
}

const char *ps_error_string_for_option(StringPiece directive,
                                       StringPiece warning)
{
    GoogleString msg =
        StrCat("\"", directive, "\" ", warning);
    g_api->log(NULL, LSI_LOG_WARN, "[%s] %s\n", ModuleName, msg.c_str());
    return msg.c_str();
}

// Very similar to apache/mod_instaweb::ParseDirective.
const char *LsRewriteOptions::ParseAndSetOptions(
    StringPiece *args, int n_args, MessageHandler *handler,
    LsRewriteDriverFactory *driver_factory,
    RewriteOptions::OptionScope scope)
{
    CHECK_GE(n_args, 1);

    StringPiece directive = args[0];
    if (GetOptionScope(directive) > scope)
    {
        return ps_error_string_for_option(
                   directive, "cannot be set at this scope.");
    }

    GoogleString msg;
    OptionSettingResult result;

    if (n_args == 1)
        result = ParseAndSetOptions0(directive, &msg, handler);
    else if (n_args == 2)
    {
        StringPiece arg = args[1];
        result = ParseAndSetOptionFromName1(directive, arg, &msg, handler);
        if (result == RewriteOptions::kOptionNameUnknown)
        {
            result = driver_factory->ParseAndSetOption1(
                         directive,
                         arg,
                         scope >= RewriteOptions::kProcessScope,
                         &msg,
                         handler);
        }

    }
    else if (n_args == 3)
    {
        result = ParseAndSetOptionFromName2(directive, args[1], args[2],
                                            &msg, handler);

        if (result == RewriteOptions::kOptionNameUnknown)
        {
            result = driver_factory->ParseAndSetOption2(
                         directive,
                         args[1],
                         args[2],
                         scope >= RewriteOptions::kProcessScope,
                         &msg,
                         handler);
        }
    }
    else if (n_args == 4)
    {
        result = ParseAndSetOptionFromName3(
                     directive, args[1], args[2], args[3], &msg, handler);
    }
    else
        result = RewriteOptions::kOptionNameUnknown;

    switch (result)
    {
    case RewriteOptions::kOptionOk:
        return 0;

    case RewriteOptions::kOptionNameUnknown:
        return ps_error_string_for_option(
                   directive, "not recognized or too many arguments");

    case RewriteOptions::kOptionValueInvalid:
        {
            GoogleString full_directive;

            for (int i = 0 ; i < n_args ; i++)
                StrAppend(&full_directive, i == 0 ? "" : " ", args[i]);

            return ps_error_string_for_option(full_directive, msg);
        }
    }

    CHECK(false);
    return NULL;
}

LsRewriteOptions *LsRewriteOptions::Clone() const
{
    LsRewriteOptions *options = new LsRewriteOptions(
        StrCat("cloned from ", description()), thread_system());
    options->Merge(*this);
    return options;
}

const LsRewriteOptions *LsRewriteOptions::DynamicCast(
    const RewriteOptions *instance)
{
    return dynamic_cast<const LsRewriteOptions *>(instance);
}

LsRewriteOptions *LsRewriteOptions::DynamicCast(RewriteOptions *instance)
{
    return dynamic_cast<LsRewriteOptions *>(instance);
}

}  // namespace net_instaweb

