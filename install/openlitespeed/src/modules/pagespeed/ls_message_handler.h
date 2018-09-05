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
#ifndef LSI_MESSAGE_HANDLER_H_
#define LSI_MESSAGE_HANDLER_H_

#include "pagespeed.h"

#include <cstdarg>

#include "pagespeed/kernel/base/basictypes.h"
#include "pagespeed/kernel/base/message_handler.h"
#include "pagespeed/kernel/base/string.h"
#include "pagespeed/kernel/base/string_util.h"
#include "pagespeed/system/system_message_handler.h"


namespace net_instaweb
{

class AbstractMutex;
class Timer;

// Implementation of a message handler that uses log_error()
// logging to emit messages, with a fallback to GoogleMessageHandler
class LsMessageHandler : public SystemMessageHandler
{
public:
    explicit LsMessageHandler(Timer *timer, AbstractMutex *mutex);

    // Installs a signal handler for common crash signals that tries to print
    // out a backtrace.
    static void InstallCrashHandler();


protected:
    virtual void MessageVImpl(MessageType type, const char *msg, va_list args);

    virtual void FileMessageVImpl(MessageType type, const char *filename,
                                  int line, const char *msg, va_list args);

private:
    LSI_LOG_LEVEL GetLsiLogLevel(MessageType type);

};

}  // namespace net_instaweb

#endif  // LSI_MESSAGE_HANDLER_H_


