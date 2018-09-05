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
#include "ls_message_handler.h"

#include <signal.h>


#include "pagespeed/kernel/base/abstract_mutex.h"
#include "pagespeed/kernel/base/debug.h"
#include "pagespeed/kernel/sharedmem/shared_circular_buffer.h"
#include "pagespeed/kernel/base/string_util.h"
#include "pagespeed/kernel/base/posix_timer.h"
#include "pagespeed/kernel/base/time_util.h"

extern "C" {
    static void signal_handler(int sig)
    {
        alarm(2);
        g_api->log(NULL, LSI_LOG_ERROR, "Trapped signal [%d]\n%s\n",
                   sig, net_instaweb::StackTraceString().c_str());
        kill(getpid(), SIGKILL);
    }
}  // extern "C"

namespace net_instaweb
{

LsMessageHandler::LsMessageHandler(Timer *timer, AbstractMutex *mutex)
    : SystemMessageHandler(timer, mutex)
{
}

// Installs a signal handler for common crash signals, that tries to print
// out a backtrace.
void LsMessageHandler::InstallCrashHandler()
{
    signal(SIGTRAP, signal_handler);    // On check failures
    signal(SIGABRT, signal_handler);
    signal(SIGFPE, signal_handler);
    signal(SIGSEGV, signal_handler);
}

LSI_LOG_LEVEL LsMessageHandler::GetLsiLogLevel(MessageType type)
{
    switch (type)
    {
    case kInfo:
        return LSI_LOG_INFO;

    case kWarning:
        return LSI_LOG_WARN;

    case kError:
    case kFatal:
        return LSI_LOG_ERROR;

    default:
        return LSI_LOG_DEBUG;
    }
}

void LsMessageHandler::MessageVImpl(MessageType type, const char *msg,
                                     va_list args)
{
    LSI_LOG_LEVEL logLevel = GetLsiLogLevel(type);
    GoogleString formatted_message = Format(msg, args);
    g_api->log(NULL, logLevel, "[%s] %s\n", ModuleName,
                formatted_message.c_str());

    // Prepare a log message for the SharedCircularBuffer only.
    AddMessageToBuffer(type, formatted_message);
}

void LsMessageHandler::FileMessageVImpl(MessageType type,
        const char *file,
        int line, const char *msg, va_list args)
{
    LSI_LOG_LEVEL logLevel = GetLsiLogLevel(type);
    GoogleString formatted_message = Format(msg, args);
    g_api->log(NULL, logLevel, "[%s %s] %s:%d:%s", ModuleName,
               kModPagespeedVersion, file, line, formatted_message.c_str());
}

}  // namespace net_instaweb

