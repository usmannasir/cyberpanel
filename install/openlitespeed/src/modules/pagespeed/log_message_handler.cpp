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
#include "pagespeed.h"
#include "log_message_handler.h"
#include <unistd.h>
#include <limits>
#include <string>
#include "base/debug/debugger.h"
#include "base/debug/stack_trace.h"
#include "base/logging.h"
#include "pagespeed/kernel/base/string_util.h"





LSI_LOG_LEVEL GetLogLevel(int severity)
{
    switch (severity)
    {
    case logging::LOG_INFO:
        return LSI_LOG_INFO;

    case logging::LOG_WARNING:
        return LSI_LOG_WARN;

    case logging::LOG_ERROR:
    case logging::LOG_FATAL:
        return LSI_LOG_ERROR;

    case logging::LOG_ERROR_REPORT:
        return LSI_LOG_NOTICE;

    default:
        return LSI_LOG_DEBUG;
    }
}

bool LogMessageHandler(int severity, const char *file, int line,
                       size_t message_start, const GoogleString &str)
{
    LSI_LOG_LEVEL logLevel = GetLogLevel(severity);
    GoogleString message = str;

    if (severity == logging::LOG_FATAL)
        severity = logging::LOG_ERROR;


    if (severity == logging::LOG_FATAL)
    {
        if (base::debug::BeingDebugged())
            base::debug::BreakDebugger();
        else
        {
            base::debug::StackTrace trace;
            std::ostringstream stream;
            trace.OutputToStream(&stream);
            message.append(stream.str());
        }
    }

    // Trim the newline off the end of the message string.
    size_t last_msg_character_index = message.length() - 1;

    if (message[last_msg_character_index] == '\n')
        message.resize(last_msg_character_index);

    g_api->log(NULL, logLevel, "[pagespeed] %s\n",
               message.c_str());

    if (severity == logging::LOG_FATAL)
    {
        // Crash the process to generate a dump.
        base::debug::BreakDebugger();
    }

    return true;
}

void InstallLogMessageHandler()
{
    logging::SetLogMessageHandler(&LogMessageHandler);
}
