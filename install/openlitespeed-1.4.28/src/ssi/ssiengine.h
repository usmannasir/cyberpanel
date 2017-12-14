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
#ifndef SSIENGINE_H
#define SSIENGINE_H


#include <http/httphandler.h>

class HttpSession;
class ExprToken;
class Expression;
class SSIScript;
class SSIComponent;
class SSIRuntime;
class SubstItem;
class SSI_If;

class SSIEngine : public HttpHandler
{
public:
    SSIEngine();

    ~SSIEngine();

    virtual const char *getName() const;


    static int startExecute(HttpSession *pSession,
                            SSIScript *pScript);
    static int resumeExecute(HttpSession *pSession);

    static int appendLocation(HttpSession *pSession, const char *pLocation,
                              int len);

    static void printError(HttpSession *pSession, char *pError);

private:
    static int updateSSIConfig(HttpSession *pSession, SSIComponent *pComponent,
                               SSIRuntime *pRuntime);

    static int processEcho(HttpSession *pSession, SSIComponent *pComponent);

    static int processExec(HttpSession *pSession, SSIComponent *pComponent);

    static int processFileAttr(HttpSession *pSession,
                               SSIComponent *pComponent);

    static int processInclude(HttpSession *pSession, SSIComponent *pComponent);

    static int processPrintEnv(HttpSession *pSession);

    static int processSet(HttpSession *pSession, SSIComponent *pComponent);

    static int processSubReq(HttpSession *pSession, SubstItem *pItem);

    static int executeComponent(HttpSession *pSession,
                                SSIComponent *pComponent);

    static int endExecute(HttpSession *pSession);

    static int evalOperator(HttpSession *pSession, ExprToken *&pTok);
    static int evalExpr(HttpSession *pSession, SubstItem *pItem);

    static int processIf(HttpSession *pSession, SSI_If *pComponent);


};

#endif
