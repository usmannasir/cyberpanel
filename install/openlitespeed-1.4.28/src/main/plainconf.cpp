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
/**
 * For reference of the usage of plain text configuration, please see wiki
 */

#include "plainconf.h"

#include <util/autobuf.h>
#include <util/gpointerlist.h>
#include <util/hashstringmap.h>
#include <log4cxx/logger.h>
#include <log4cxx/logsession.h>
#include <util/xmlnode.h>
#include <libgen.h>

#include <dirent.h>
#include <errno.h>
#include <fnmatch.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

//#define TEST_OUTPUT_PLAIN_CONF

//Special case
//:: means module and module name

#define UNKNOWN_KEYWORDS        "unknownkeywords"
//All the keywords are lower case
//TODO: !! means the item marked need to be rempved in later version
plainconfKeywords plainconf::sKeywords[] =
{
    {"accesscontrol",                            NULL},
    {"accessdenydir",                            NULL},
    {"accesslog",                                NULL},
    {"add",                                      NULL},
    {"adddefaultcharset",                        NULL},
    {"addmimetype",                              NULL},
    {"address",                                  NULL},
    {"adminconfig",                              NULL},
    {"adminemails",                              NULL},
    {"adminroot",                                NULL},
    {"allow",                                    NULL},
    {"allowbrowse",                              NULL},
    {"allowdirectaccess",                        NULL},
    {"allowedhosts",                             NULL},
    {"allowsetuid",                              NULL},
    {"allowsymbollink",                          NULL},
    {"authname",                                 NULL},
    {"authorizer",                               NULL},
    {"autofix503",                               NULL},
    {"autoindex",                                NULL},
    {"autoindexuri",                             NULL},
    {"autorestart",                              NULL},
    {"autostart",                                NULL},
    {"awstats",                                  NULL},
    {"awstatsuri",                               NULL},
    {"backlog",                                  NULL},
    {"banperiod",                                NULL},
    {"base",                                     NULL},
    {"binding",                                  NULL},
    {"brstaticcompresslevel",                    NULL},
    {"byteslog",                                 NULL},
    {"cacertfile",                               NULL},
    {"cacertpath",                               NULL},
    {"certchain",                                NULL},
    {"certfile",                                 NULL},
    {"certfile2",                                 NULL},
    {"certfile3",                                 NULL},
    {"cgidsock",                                 NULL},
    {"cgirlimit",                                NULL},
    {"checksymbollink",                          NULL},
    {"chrootmode",                               NULL},
    {"chrootpath",                               NULL},
    {"ciphers",                                  NULL},
    {"clientverify",                             NULL},
    {"compressarchive",                          NULL},
    {"compressibletypes",                        NULL},
    {"configfile",                               NULL},
    {"conntimeout",                              NULL},
    {"context",                                  NULL},
    {"contextlist",                              NULL},  //!!
    {"cpuhardlimit",                             NULL},
    {"cpusoftlimit",                             NULL},
    {"crlfile",                                  NULL},
    {"crlpath",                                  NULL},
    {"customerrorpages",                         NULL},  //!!
    {"debuglevel",                               NULL},
    {"defaultcharsetcustomized",                 NULL},
    {"defaulttype",                              NULL},
    {"deny",                                     NULL},
    {"disablewebadmin",                          NULL},
    {"dhparam",                                  NULL},
    {"dir",                                      NULL},
    {"docroot",                                  NULL},
    {"domain",                                   NULL},
    {"dynreqpersec",                             NULL},
    {"enable",                                   NULL},
    {"enableaiolog",                             NULL},
    {"enablebr",                                 NULL},
    {"enablebrcompress",                         NULL},
    {"enablechroot",                             NULL},
    {"enablecoredump",                           NULL},
    {"enabled",                                  NULL},
    {"enabledhe",                                NULL},
    {"enabledyngzipcompress",                    NULL},
    {"enableecdhe",                              NULL},
    {"enableexpires",                            NULL},
    {"enablegzip",                               NULL},
    {"enablegzipcompress",                       NULL},
    {"enablehotlinkctrl",                        NULL},
    {"enableh2c",                                NULL},
    {"enableipgeo",                              NULL},
    {"enableiptoloc",                            NULL},
    {"enablescript",                             NULL},
    {"enablespdy",                               NULL},
    {"enablestapling",                           NULL},
    {"enablestderrlog",                          NULL},
    {"env",                                      NULL},
    {"errcode",                                  NULL},
    {"errorlog",                                 NULL},
    {"errorpage",                                NULL},
    {"eventdispatcher",                          NULL},
    {"expires",                                  NULL},
    {"expiresbytype",                            NULL},
    {"expiresdefault",                           NULL},
    {"externalredirect",                         NULL},
    {"extgroup",                                 NULL},
    {"extmaxidletime",                           NULL},
    {"extprocessor",                             NULL},
    {"extprocessorlist",                         NULL},  //!!
    {"extraheaders",                             NULL},
    {"extuser",                                  NULL},
    {"fileaccesscontrol",                        NULL},
    {"filename",                                 NULL},
    {"followsymbollink",                         NULL},
    {"forcegid",                                 NULL},
    {"forcetype",                                NULL},
    {"geoipdb",                                  NULL},
    {"geoipdbcache",                             NULL},
    {"geoipdbfile",                              NULL},
    {"graceperiod",                              NULL},
    {"group",                                    NULL},
    {"groupdb",                                  NULL},
    {"gzipautoupdatestatic",                     NULL},
    {"gzipcachedir",                             NULL},
    {"gzipcompresslevel",                        NULL},
    {"gzipmaxfilesize",                          NULL},
    {"gzipminfilesize",                          NULL},
    {"gzipstaticcompresslevel",                  NULL},
    {"handler",                                  NULL},
    {"hardlimit",                                NULL},
    {"hotlinkctrl",                              NULL},
    {"htaccess",                                 NULL},
    {"httpdworkers",                             NULL},
    {"httpserverconfig",                         NULL},
    {"inbandwidth",                              NULL},
    {"include",                                  NULL},
    {"index",                                    NULL},
    {"inherit",                                  NULL},
    {"indexfiles",                               NULL},
    {"inittimeout",                              NULL},
    {"internal",                              NULL},
    {"inmembufsize",                             NULL},
    {"instances",                                NULL},
    {"iptogeo",                                  NULL},
    {"iptolocdb",                                 NULL},
    {"iptolocdbcache",                            NULL},
    {"iptolocdbfile",                             NULL},
    {"keepalivetimeout",                         NULL},
    {"keepdays",                                 NULL},
    {"keyfile",                                  NULL},
    {"keyfile2",                                  NULL},
    {"keyfile3",                                  NULL},
    {"listener",                                 NULL},
    {"listenerlist",                             NULL}, //!!
    {"listeners",                                NULL},
    {"location",                                 NULL},
    {"log",                                      NULL},//!!
    {"logformat",                                NULL},
    {"logging",                                  NULL},  //!!
    {"logheaders",                               NULL},
    {"loglevel",                                 NULL},
    {"logreferer",                               NULL},
    {"loguseragent",                             NULL},
    {"map",                                      NULL},
    {"maxcachedfilesize",                        NULL},
    {"maxcachesize",                             NULL},
    {"maxcgiinstances",                          NULL},
    {"maxconnections",                           NULL},
    {"maxconns",                                 NULL},
    {"maxdynrespheadersize",                     NULL},
    {"maxdynrespsize",                           NULL},
    {"maxkeepalivereq",                          NULL},
    {"maxmmapfilesize",                          NULL},
    {"maxreqbodysize",                           NULL},
    {"maxreqheadersize",                         NULL},
    {"maxrequrllen",                             NULL},
    {"maxsslconnections",                        NULL},
    {"member",                                   NULL},
    {"memhardlimit",                             NULL},
    {"memsoftlimit",                             NULL},
    {"mime",                                     NULL},
    {"mingid",                                   NULL},
    {"minuid",                                   NULL},
    {"module",                                   NULL},
    {"modulelist",                               NULL},//!!
    {"name",                                     NULL},
    {"note",                                     NULL},
    {"ocspcacerts",                              NULL},
    {"ocsprespmaxage",                           NULL},
    {"ocspresponder",                            NULL},
    {"onlyself",                                 NULL},
    {"outbandwidth",                             NULL},
    {"param",                                    NULL},
    {"path",                                     NULL},
    {"pckeepalivetimeout",                       NULL},
    {"perclientconnlimit",                       NULL},
    {"persistconn",                              NULL},
    {"pipedlogger",                              NULL},
    {"priority",                                 NULL},
    {"prochardlimit",                            NULL},
    {"procsoftlimit",                            NULL},
    {"railsdefaults",                            NULL},
    {"railsenv",                                 NULL},
    {"rcvbufsize",                               NULL},
    {"realm",                                    NULL},
    {"realmlist",                                NULL},//!!
    {"redirecturi",                              NULL},
    {"required",                                 NULL},
    {"requiredpermissionmask",                   NULL},
    {"respbuffer",                               NULL},
    {"restrained",                               NULL},
    {"restrictedpermissionmask",                 NULL},
    {"retrytimeout",                             NULL},
    {"rewrite",                                  NULL},
    {"rewritebase",                              NULL},
    {"rewritecond",                              NULL},
    {"rewriteengine",                            NULL},
    {"rewriterule",                              NULL},
    {"rewritefile",                              NULL},
    {"rollingsize",                              NULL},
    {"rubybin",                                  NULL},
    {"rules",                                    NULL},
    {"runonstartup",                             NULL},
    {"scripthandler",                            NULL},
    {"scripthandlerlist",                        NULL},
    {"secure",                                   NULL},
    {"securedconn",                              NULL},
    {"security",                                 NULL},
    {"servername",                               NULL},
    {"sslenablemulticerts",                      NULL},
    {"sslsessioncache",                          NULL},
    {"sslsessioncachesize",                      NULL},
    {"sslsessioncachetimeout",                   NULL},
    {"sslsessiontickets",                        NULL},
    {"sslsessionticketkeyfile",                  NULL},
    {"sslsessionticketlifetime",                 NULL},
    {"sslstrongdhkey",                           NULL},
    {"setuidmode",                               NULL},
    {"showversionnumber",                        NULL},
    {"shmdefaultdir",                            NULL},
    {"sitealiases",                              NULL},
    {"sitedomain",                               NULL},
    {"smartkeepalive",                           NULL},
    {"sndbufsize",                               NULL},
    {"softlimit",                                NULL},
    {"spdyadheader",                             NULL},
    {"sslcryptodevice",                          NULL},
    {"sslprotocol",                              NULL},
    {"statdir",                                  NULL},
    {"staticreqpersec",                          NULL},
    {"statuscode",                               NULL},
    {"suffix",                                   NULL},
    {"suffixes",                                 NULL},
    {"swappingdir",                              NULL},
    {"templatefile",                             NULL},
    {"totalinmemcachesize",                      NULL},
    {"totalmmapcachesize",                       NULL},
    {"tuning",                                   NULL},
    {"type",                                     NULL},
    {"updateinterval",                           NULL},
    {"updatemode",                               NULL},
    {"updateoffset",                             NULL},
    {"uri",                                      NULL},
    {"url",                                      NULL},
    {"urlfilter",                                NULL},
    {"urlfilterlist",                            NULL},//!!
    {"useipinproxyheader",                       NULL},
    {"user",                                     NULL},
    {"userdb",                                   NULL},
    {"usesendfile",                              NULL},
    {"useserver",                                NULL},
    {"verifydepth",                              NULL},
    {"vhaliases",                                NULL},
    {"vhdomain",                                 NULL},
    {"vhname",                                   NULL},
    {"vhost",                                    NULL},
    {"vhostmap",                                 NULL},
    {"vhostmaplist",                             NULL},//!!
    {"vhroot",                                   NULL},
    {"vhssl",                                    NULL},
    {"vhtemplate",                               NULL},
    {"vhtemplatelist",                           NULL},//!!
    {"virtualhost",                              NULL},
    {"virtualhostconfig",                        NULL},
    {"virtualhostlist",                              NULL},//!!
    {"virtualhosttemplate",                      NULL},
    {"websocket",                                NULL},
    {"websocketlist",                                NULL},//!!
    {"workers",                                      NULL},
    {"workingdir",                               NULL},


    {"disableinitlogrotation",                               NULL},
    {"fileetag",                               NULL},
    {"gracefulrestarttimeout",                               NULL},
    {"renegprotection",                               NULL},
    {"sessiontimeout",                               NULL},
    {"suspendedvhosts",                               NULL},
    {"restricteddirpermissionmask",                               NULL},
    {"restrictedscriptpermissionmask",                               NULL},

    {"phpsuexec",                            NULL},

    {"phpsuexecmaxconn",             NULL},
    {"useaio",             NULL},

    {"aioblocksize",             NULL},
    {"forcestrictownership",             NULL},
    {"accessfilename",             NULL},
    {"allowoverride",             NULL},
    {"cachetimeout",             NULL},
    {"general",             NULL},
    {"enablecontextac",             NULL},


    //Hooks name here
    {"l4_beginsession",          NULL},
    {"l4_endsession",          NULL},
    {"l4_recving",          NULL},
    {"l4_sending",          NULL},
    {"http_begin",          NULL},
    {"recv_req_header",          NULL},
    {"uri_map",          NULL},
    {"http_auth",          NULL},
    {"recv_req_body",          NULL},
    {"rcvd_req_body",          NULL},
    {"recv_resp_header",          NULL},
    {"recv_resp_body",          NULL},
    {"rcvd_resp_body",          NULL},
    {"handler_restart",          NULL},
    {"send_resp_header",          NULL},
    {"send_resp_body",          NULL},
    {"http_end",          NULL},
    {"main_inited",          NULL},
    {"main_prefork",          NULL},
    {"main_postfork",          NULL},
    {"worker_postfork",          NULL},
    {"worker_atexit",          NULL},
    {"main_atexit",          NULL},

    {"umask",          NULL},
    {"blockbadreq",      NULL},  //Add to avoid error notice in errorlog

    {"uploadpassbypath",          NULL},
    {"uploadtmpdir",          NULL},
    {"uploadtmpfilepermission",          NULL},


};

static HashStringMap<plainconfKeywords *> allKeyword(29, GHash::hfCiString,
        GHash::cmpCiString);
bool plainconf::bKeywordsInited = false;
bool plainconf::bErrorLogSetup = false;
AutoStr2 plainconf::rootPath = "";
StringList plainconf::errorLogList;
GPointerList plainconf::gModuleList;

/***
 * We try to make log available even if errorlog is not setup.
 * So, at the beginning, we put the logs to StringList plainconf::errorLogList by call logToMem()
 * once flushErrorLog() is called, it means errorlog is setup, and this function will save all
 * the buffered logs to errorlog file.
 * Then if logToMem still be called, it should not access the stringlist anymore,
 * but just access the errorlog directly.
 */
void plainconf::logToMem(char errorLevel, const char *format, ...)
{
    char buf[512];
    sprintf(buf, "%c[PlainConf] ", errorLevel);
    int len = strlen(buf);

    if (gModuleList.size() > 0)
    {
        XmlNode *pCurNode = (XmlNode *)gModuleList.back();
        sprintf(buf + len, "[%s:%s] ", pCurNode->getName(),
                ((pCurNode->getValue() == NULL) ? "" : pCurNode->getValue()));
    }

    len = strlen(buf);
    va_list ap;
    va_start(ap, format);
    int ret = vsnprintf(buf + len, 512 - len, format, ap);
    va_end(ap);

    if (!bErrorLogSetup)
        errorLogList.add(buf, ret + len);
    else
    {
        if (errorLevel == LOG_LEVEL_ERR)
            LS_ERROR("%s", buf + 1);
        else
            LS_INFO("%s", buf + 1);
    }
}


static int for_each_fn(void *s)
{
    const char *p = ((AutoStr2 *)s)->c_str();

    switch (*p)
    {
    case LOG_LEVEL_ERR:
        LS_ERROR("%s", p + 1);
        break;

    case LOG_LEVEL_INFO:
        LS_INFO("%s", p + 1);
        break;

    default:
        break;
    }

    return 0;
}


void plainconf::flushErrorLog()
{
    //int n = errorLogList.size();
    errorLogList.for_each(errorLogList.begin(), errorLogList.end(),
                          for_each_fn);
    errorLogList.clear();
    bErrorLogSetup = true;
}


void plainconf::tolowerstr(char *sLine)
{
    while (*sLine)
    {
        if (*sLine >= 'A' && *sLine <= 'Z')
            *sLine |= 0x20;

        ++sLine;
    }
}


void plainconf::initKeywords()
{
    if (bKeywordsInited)
        return ;

    int count = sizeof(sKeywords) / sizeof(plainconfKeywords);

    for (int i = 0; i < count; ++i)
    {
        allKeyword.insert(sKeywords[i].name, &sKeywords[i]);

        if (sKeywords[i].alias && strlen(sKeywords[i].alias) > 0)
            allKeyword.insert(sKeywords[i].alias, &sKeywords[i]);
    }

    bKeywordsInited = true;
}


void plainconf::setRootPath(const char *root)
{
    rootPath = root;
}

const char *plainconf::getRealName(char *name)
{
    assert(bKeywordsInited == true);
    tolowerstr(name);
    HashStringMap<plainconfKeywords *>::iterator it = allKeyword.find(name);

    if (it == allKeyword.end())
        return NULL;
    else
        return it.second()->name;
}


void plainconf::trimWhiteSpace(const char **p)
{
    while (**p == 0x20 || **p == '\t')
        ++(*p);
}


//Get the first ono-space position of a string
const char *plainconf::getStrNoSpace(const char *sLine, size_t &length)
{
    int len = strlen(sLine);
    int offset = -1, i;

    for (i = 0; i < len; ++i)
    {
        if (sLine[i] != ' ' && sLine[i] != '\t')
            break;
        else
            offset = i;
    }

    for (; i < len; ++i)
    {
        if (sLine[i] == ' ' || sLine[i] == '\t' ||
            sLine[i] == '\r' || sLine[i] == '\n')
            break;
    }

    length = i - (offset + 1);
    return sLine + offset + 1;
}


//pos: 0, start position, 1: end position
void plainconf::removeSpace(char *sLine, int pos)
{
    int len = strlen(sLine);
    int index, offset = -1;

    for (int i = 0; i < len; ++i)
    {
        index = ((pos == 0) ? i : (len - 1 - i));

        if (sLine[index] != ' ' &&
            sLine[index] != '\t' &&
            sLine[index] != '\r' &&
            sLine[index] != '\n')
            break;
        else
            offset = i;
    }

    if (pos == 0)
    {
        offset += 1; //index change to count
        memmove(sLine, sLine + offset, len - offset);
        sLine[len - offset] = 0x00;
    }
    else
        sLine[len - offset - 1] = 0x00;
}


bool plainconf::isChunkedLine(const char *sLine)
{
    int len = strlen(sLine);

    if (sLine[len - 1] != '\\')
        return false;

    //Already know the last one is a '\\'
    int continuesBackSlashCount = 1;
    const char *pStart = sLine;
    const char *pLast = sLine + len - 2;

    while (pLast >= pStart &&  *pLast-- == '\\')
    {
        ++continuesBackSlashCount;
        break; //Now if more than 2 \, will not be treated as continued
    }

    //return (continuesBackSlashCount % 2);
    return (continuesBackSlashCount == 1);
}


bool plainconf::strcatchr(char *s, char c, int maxStrLen)
{
    int len = strlen(s);

    if (len == maxStrLen -1)
        return false;

    s[len] = c;
    s[len + 1] = 0x00;
    return true;
}


void plainconf::saveUnknownItems(const char *fileName, int lineNumber,
                                 XmlNode *pCurNode, const char *name, const char *value)
{
    //if not inside a "module" and without a "::", treated as error
    if (strcasecmp(pCurNode->getName(), "module") != 0 &&
        strstr(name, "::") == NULL)
    {
        logToMem(LOG_LEVEL_ERR, "Not support [%s %s] in file %s:%d", name, value,
                 fileName, lineNumber);
        return ;
    }

    char newvalue[4096] = {0};
    XmlNode *pParamNode = new XmlNode;
    const char *attr = NULL;
    pParamNode->init(UNKNOWN_KEYWORDS, &attr);
    strcpy(newvalue, name);
    strcat(newvalue, " ");
    strcat(newvalue, value);
    pParamNode->setValue(newvalue, strlen(newvalue));
    pCurNode->addChild(pParamNode->getName(), pParamNode);
}


void plainconf::appendModuleParam(XmlNode *pModuleNode, const char *param)
{
    XmlNode *pParamNode = pModuleNode->getChild("param");

    if (pParamNode == NULL)
    {
        pParamNode = new XmlNode;
        const char *attr = NULL;
        pParamNode->init("param", &attr);
        pParamNode->setValue(param, strlen(param));
        pModuleNode->addChild(pParamNode->getName(), pParamNode);
    }
    else
    {
        AutoStr2 totalValue = pParamNode->getValue();
        totalValue.append("\n", 1);
        totalValue.append(param, strlen(param));
        pParamNode->setValue(totalValue.c_str(), totalValue.len());
    }

    logToMem(LOG_LEVEL_INFO, "[%s:%s] module [%s] add param [%s]",
             pModuleNode->getParent()->getName(),
             ((pModuleNode->getParent()->getValue()) ?
              pModuleNode->getParent()->getValue() : ""),
             pModuleNode->getValue(), param);
}


void plainconf::addModuleWithParam(XmlNode *pCurNode,
                                   const char *moduleName, const char *param)
{
    XmlNode *pModuleNode = NULL;
    XmlNodeList::const_iterator iter;
    const XmlNodeList *pModuleList = pCurNode->getChildren("module");

    if (pModuleList)
    {
        for (iter = pModuleList->begin(); iter != pModuleList->end(); ++iter)
        {
            if (strcasecmp((*iter)->getChildValue("name", 1), moduleName) == 0)
            {
                pModuleNode = (*iter);
                break;
            }
        }
    }

    if (!pModuleNode)
    {
        pModuleNode = new XmlNode;
        //XmlNode *pParamNode = new XmlNode;
        const char *attr = NULL;
        pModuleNode->init("module", &attr);
        pModuleNode->setValue(moduleName, strlen(moduleName));
        pCurNode->addChild(pModuleNode->getName(), pModuleNode);
        logToMem(LOG_LEVEL_INFO, "[%s:%s]addModuleWithParam ADD module %s",
                 pCurNode->getName(), pCurNode->getValue(), moduleName);
    }

    appendModuleParam(pModuleNode, param);
}


void plainconf::handleSpecialCase(XmlNode *pNode)
{
    const XmlNodeList *pUnknownList = pNode->getChildren(UNKNOWN_KEYWORDS);

    if (!pUnknownList)
        return ;

    int bModuleNode = (strcasecmp(pNode->getName(), "module") == 0);
    XmlNodeList::const_iterator iter;

    for (iter = pUnknownList->begin(); iter != pUnknownList->end(); ++iter)
    {
        const char *value = (*iter)->getValue();

        if (bModuleNode)
            appendModuleParam(pNode, value);
        else
        {
            const char *p = strstr(value, "::");

            //Only hanlde has :: case
            if (p)
            {
                /**
                 * CASE such as cache::enablecache 1, will be treated as
                 * module chace {
                 * param enablecache 1
                 * }
                 */
                char newname[1024] = {0};
                char newvalue[4096] = {0};
                strncpy(newname, value, p - value);
                strcpy(newvalue, p + 2);

                XmlNode *pRootNode = pNode;

                while (pRootNode->getParent())
                    pRootNode = pRootNode->getParent();

                const XmlNodeList *pModuleList = pRootNode->getChildren("module");

                if (pModuleList)
                {
                    XmlNodeList::const_iterator iter2;

                    for (iter2 = pModuleList->begin(); iter2 != pModuleList->end(); ++iter2)
                    {
                        if (strcasecmp((*iter2)->getValue(), newname) == 0)
                        {
                            addModuleWithParam(pNode, newname, newvalue);
                            break;
                        }
                    }

                    if (iter2 == pModuleList->end())
                        logToMem(LOG_LEVEL_ERR,
                                 "Module[%s] not defined in server leve while checking [%s].", newname,
                                 value);

                }
                else
                    logToMem(LOG_LEVEL_ERR,
                             "No module defined in server leve while checking [%s].", value);
            }
        }
    }
}


void plainconf::handleSpecialCaseLoop(XmlNode *pNode)
{
    XmlNodeList list;
    int count = pNode->getAllChildren(list);

    if (count > 0)
    {
        XmlNodeList::const_iterator iter;

        for (iter = list.begin(); iter != list.end(); ++iter)
            handleSpecialCaseLoop(*iter);

        handleSpecialCase(pNode);
    }
}


void plainconf::clearNameAndValue(char *name, char *value)
{
    name[0] = 0;
    value[0] = 0;
}


void plainconf::parseLine(const char *fileName, int lineNumber,
                          const char *sLine)
{
    const int MAX_NAME_LENGTH = 1024 << 6;
    char name[MAX_NAME_LENGTH] = {0};
    char value[MAX_NAME_LENGTH] = {0};
    const char *attr = NULL;

    XmlNode *pNode = NULL;
    XmlNode *pCurNode = (XmlNode *)gModuleList.back();
    const char *p = sLine;
    const char *pEnd = sLine + strlen(sLine);

    bool bNameSet = false;

    for (; p < pEnd; ++p)
    {
        //"{" is a beginning of a block only if it is the last char of a line
        if (*p == '{' && pEnd - p == 1)
        {
            if (strlen(name) > 0)
            {
                const char *pRealname = getRealName(name);

                if (pRealname)
                {
                    pNode = new XmlNode;
                    pNode->init(pRealname, &attr);

                    //Remove space in the end of the value such as "module cache  {", value will be "cache"
                    removeSpace(value, 1);

                    if (strlen(value) > 0)
                        pNode->setValue(value, strlen(value));

                    pCurNode->addChild(pNode->getName(), pNode);
                    gModuleList.push_back(pNode);
                    pCurNode = pNode;
                    clearNameAndValue(name, value);
                    break;
                }
                else
                {
                    logToMem(LOG_LEVEL_ERR,
                             "parseline find block name [%s] is NOT keyword in %s:%d", name, fileName,
                             lineNumber);
                    break;
                }
            }
            else
            {
                logToMem(LOG_LEVEL_ERR,
                         "parseline found '{' without a block name in %s:%d", fileName, lineNumber);
                break;
            }
        }

        else if (*p == '}' && p == sLine)
        {
            if (gModuleList.size() > 1)
            {
                gModuleList.pop_back();
                clearNameAndValue(name, value);

                if (*(p + 1))
                {
                    ++p;
                    trimWhiteSpace(&p);
                    parseLine(fileName, lineNumber, p);
                    break;
                }
            }
            else
            {
                logToMem(LOG_LEVEL_ERR, "parseline found more '}' in %s:%d", fileName,
                         lineNumber);
                clearNameAndValue(name, value);
                break;
            }
        }
        else if ((*p == ' ' || *p == '\t') && value[0] == 0)
        {
            bNameSet = true;
            continue;
        }
        else
        {
            if (!bNameSet)
                strcatchr(name, *p, MAX_NAME_LENGTH);
            else
                strcatchr(value, *p, MAX_NAME_LENGTH);
        }
    }

    if (name[0] != 0)
    {
        const char *pRealname = getRealName(name);

        if (pRealname)
        {
            assert(pNode == NULL);
            pNode = new XmlNode;
            pNode->init(pRealname, &attr);

            if (strlen(value) > 0)
                pNode->setValue(value, strlen(value));

            pCurNode->addChild(pNode->getName(), pNode);
        }
        else
        {
            //There is no special case in server level
            //if (memcmp(pCurNode->getName(), SERVER_ROOT_XML_NAME, sizeof(SERVER_ROOT_XML_NAME) - 1) != 0)
            saveUnknownItems(fileName, lineNumber, pCurNode, name, value);
            //else
            //    logToMem(LOG_LEVEL_ERR, "%s Server level find unknown keyword [%s], ignored.", SERVER_ROOT_XML_NAME, name );
        }
    }
}


bool plainconf::isValidline(const char *sLine)
{
    int len = strlen(sLine);

    if (len == 0 || sLine[0] == '#')
        return false;

    const char invalidChars[] = "# \t\r\n\\";
    bool bValid = false;

    for (int i = 0; i < len; ++i)
    {
        if (!strchr(invalidChars, sLine[i]))
        {
            bValid = true;
            break;
        }
    }

    return bValid;
}


//Return the length copied the sign, 0 means not a mulline mode
int plainconf::checkMultiLineMode(const char *sLine,
                                  char *sMultiLineModeSign, int maxSize)
{
    const char *p = strstr(sLine, "<<<");
    int n = 0;

    if (p && p > sLine && (n = strlen(sLine) - (p - sLine + 3)) > 0)
    {
        if (n > maxSize)
            n = maxSize;

        strncpy(sMultiLineModeSign, p + 3, n);
        return n;
    }

    return 0;
}


//if true return true, and also set the path
bool plainconf::isInclude(const char *sLine, AutoStr2 &path)
{
    char *p = NULL;
    if (strncasecmp(sLine, "include", 7) == 0)
        p = (char *)sLine + 7;
    else
        return false;

    removeSpace(p, 0);
    path = p;
    return true;
}

ConfFileType plainconf::checkFiletype(const char *path)
{
    struct stat sb;

    //Already has wildcahr, treat as directory
    if (strchr(path, '*') ||
        strchr(path, '?') ||
        (strchr(path, '[') && strchr(path, ']')))
        return eConfWildcard;

    if (stat(path, &sb) == -1)
        return eConfUnknown;

    if ((sb.st_mode & S_IFMT) == S_IFDIR)
        return eConfDir;

    else
        return eConfFile;
}


void plainconf::loadDirectory(const char *pPath, const char *pPattern)
{
    DIR *pDir = opendir(pPath);

    if (!pDir)
    {
        logToMem(LOG_LEVEL_ERR, "Failed to open directory [%s].", pPath);
        return ;
    }

    struct dirent *dir_ent;

    char str[4096] = {0};
    strcpy(str, pPath);
    strcatchr(str, '/', 4096);
    int offset = strlen(str);
    StringList AllEntries;

    while ((dir_ent = readdir(pDir)))
    {
        const char *pName = dir_ent->d_name;

        if ((strcmp(pName, ".") == 0) ||
            (strcmp(pName, "..") == 0) ||
            (*(pName + strlen(pName) - 1) == '~'))
            continue;

        if (pPattern)
        {
            //Beside the unmatch, also must exclude *,v which was created by rcs
            if (fnmatch(pPattern, pName, FNM_PATHNAME) != 0
                || fnmatch("*,v", pName, FNM_PATHNAME) == 0)
                continue;
        }

        strcpy(str + offset, pName);
        struct stat st;
        if (stat(str, &st) == 0)
        {
            if (S_ISDIR(st.st_mode)
                || pPattern
                || fnmatch("*.conf", pName, FNM_PATHNAME) == 0)
                AllEntries.add(str);
        }
    }
    closedir(pDir);
    AllEntries.sort();

    StringList::iterator iter;
    for (iter = AllEntries.begin(); iter != AllEntries.end(); ++iter)
    {
        const char *pName = (*iter)->c_str();
        logToMem(LOG_LEVEL_INFO, "Processing config file: %s", pName);
        loadConfFile(pName);
    }
}


void plainconf::getIncludeFile(const char *curDir, const char *orgFile,
                               char *targetFile)
{
    int len = strlen(orgFile);

    if (len == 0)
        return;

    //Absolute path
    if (orgFile[0] == '/')
        strcpy(targetFile, orgFile);

    else if (orgFile[0] == '$')
    {
        if (strncasecmp(orgFile, "$server_root/", 13) == 0)
        {
            strcpy(targetFile, rootPath.c_str());
            strcat(targetFile, orgFile + 13);
        }
        else
        {
            logToMem(LOG_LEVEL_ERR, "Can't resolve include file %s", orgFile);
            return ;
        }
    }

    else
    {
        strcpy(targetFile, curDir);
        strcat(targetFile, "/");
        strcat(targetFile, orgFile);
    }
}


//When checking we use lock for may need to update the conf file later
//If user RCS checkout a revision, a unlock should be used for next time checkin.
//Example: co -u1.1 httpd_config.conf
void plainconf::checkInFile(const char *path)
{
    if (access(path, 0) == -1)
        return ;

    //Backup file abd checkin and out
    char new_path[4096];
    strcpy(new_path, path);
    strcat(new_path, "0");

    AutoStr2 buf;
    buf.setStr("cp \"");
    buf.append(path, strlen(path));
    buf.append("\" \"", 3);
    buf.append(new_path, strlen(new_path));
    buf.append("\"", 1);
    int ret = system(buf.c_str());

    if (ret != 0)
    {
        logToMem(LOG_LEVEL_INFO, "Failed to backup the conf file %s, ret %d.",
                 path, ret);
        return ;
    }

    buf.setStr("ci -l -q -t-\"");
    buf.append(new_path, strlen(new_path));
    buf.append("\" -mUpdate \"", 12);
    buf.append(new_path, strlen(new_path));
    buf.append("\" >/dev/null 2>&1", 17);
    ret = system(buf.c_str());

    if (ret == 0)
        logToMem(LOG_LEVEL_INFO, "RCS checkin config file %s OK.", new_path);
    else
        logToMem(LOG_LEVEL_INFO,
                 "Failed to RCS checkin conf file %s, ret %d, error(%s). "
                 "Org command is %s.", new_path, ret, strerror(errno), buf.c_str());

    unlink(new_path);
}


static int appendBuf(AutoBuf *pBuf, const char *pSrc, size_t len)
{
    const size_t ABSOLUTE_MAX = 1024 << 6;
    size_t newLen = pBuf->size() + len;
    if (newLen > ABSOLUTE_MAX)
    {
        return LS_FAIL;
    }
    if (newLen > (size_t)pBuf->capacity())
    {
        pBuf->grow(ABSOLUTE_MAX - pBuf->capacity());
    }
    pBuf->append(pSrc, len);
    *pBuf->end() = '\0';
    return LS_OK;
}


//This function may be recruse called
void plainconf::loadConfFile(const char *path)
{
    logToMem(LOG_LEVEL_INFO, "start parsing file %s", path);

    ConfFileType type = checkFiletype(path);

    if (type == eConfUnknown)
        return;

    else if (type == eConfDir)
        loadDirectory(path, NULL);

    else if (type == eConfWildcard)
    {
        AutoStr2 prefixPath = path;
        const char *p = strrchr(path, '/');

        if (p)
            prefixPath.setStr(path, p - path);

        struct stat sb;

        //removed the wildchar filename, should be a directory if exist
        if (stat(prefixPath.c_str(), &sb) == -1)
        {
            logToMem(LOG_LEVEL_ERR, "LoadConfFile error 1, path:%s directory:%s",
                     path, prefixPath.c_str());
            return ;
        }

        if ((sb.st_mode & S_IFMT) != S_IFDIR)
        {
            logToMem(LOG_LEVEL_ERR, "LoadConfFile error 2, path:%s directory:%s",
                     path, prefixPath.c_str());
            return ;
        }

        loadDirectory(prefixPath.c_str(), p + 1);
    }

    else //existed file
    {
        //gModuleList.push_back();
        //XmlNode *xmlNode = new XmlNode;
        FILE *fp = fopen(path, "r");

        if (fp == NULL)
        {
            logToMem(LOG_LEVEL_ERR, "Cannot open configuration file: %s", path);
            return;
        }


        const int MAX_LINE_LENGTH = 8192;
        char sLine[MAX_LINE_LENGTH];
        char *p;
        AutoBuf bLines(MAX_LINE_LENGTH);
        int lineNumber = 0;
        int ret = LS_OK;
        const int MAX_MULLINE_SIGN_LENGTH = 128;
        char sMultiLineModeSign[MAX_MULLINE_SIGN_LENGTH] = {0};
        size_t  nMultiLineModeSignLen = 0;  //>0 is mulline mode

        while (!feof(fp))
        {
            sLine[0] = 0x00;
            fgets(sLine, MAX_LINE_LENGTH, fp);
            ++lineNumber;
            p = sLine;

            if (nMultiLineModeSignLen)
            {
                //Check if reach the END of the milline mode
                size_t len = 0;
                const char *pLineStart = getStrNoSpace(p, len);

                if (len == nMultiLineModeSignLen &&
                    strncasecmp(pLineStart, sMultiLineModeSign, nMultiLineModeSignLen) == 0)
                {
                    nMultiLineModeSignLen = 0;
                    //Remove the last \r\n so that if it is one line, it will still be one line
                    removeSpace(bLines.begin(), 1);
                    parseLine(path, lineNumber, bLines.begin());
                    bLines.resize(MAX_LINE_LENGTH);
                    bLines.clear();
                    // shrink buf.
                }
                else if ((ret = appendBuf(&bLines, p, strlen(p))) != LS_OK)
                {
                    break;
                }

                continue;
            }

            removeSpace(p, 0);
            removeSpace(p, 1);

            if (!isValidline(p))
                continue;

            AutoStr2 pathInclude;

            if (isInclude(p, pathInclude))
            {
                char achBuf[512] = {0};
                char *pathc = strdup(path);
                const char *curDir = dirname(pathc);
                getIncludeFile(curDir, pathInclude.c_str(), achBuf);
                free(pathc);
                loadConfFile(achBuf);
            }
            else
            {
                nMultiLineModeSignLen = checkMultiLineMode(p, sMultiLineModeSign,
                                        MAX_MULLINE_SIGN_LENGTH);

                if (nMultiLineModeSignLen > 0)
                {
                    if ((ret = appendBuf(&bLines, p,
                        strlen(p) - (3 + nMultiLineModeSignLen))) != LS_OK)
                    {
                        break;
                    }
                }
                //need to continue
                else if (isChunkedLine(p))
                {
                    if ((ret = appendBuf(&bLines, p, strlen(p) - 1)) != LS_OK)
                    {
                        break;
                    }
                    //strcatchr(sLines, ' ', MAX_LINE_LENGTH); //add a space at the end of the line which has a '\\'
                }

                else
                {
                    if ((ret = appendBuf(&bLines, p, strlen(p))) != LS_OK)
                    {
                        break;
                    }

                    parseLine(path, lineNumber, bLines.begin());
                    bLines.resize(MAX_LINE_LENGTH);
                    bLines.clear();
                }
            }
        }

        fclose(fp);
        if (ret != LS_OK)
        {
            logToMem(LOG_LEVEL_ERR, "Multiline configuration too long: %s", path);
            return;
        }

        //Parsed, check in it
        checkInFile(path);
    }

}


//return the root node of the tree
XmlNode *plainconf::parseFile(const char *configFilePath,
                              const char *rootTag)
{
#ifdef TEST_OUTPUT_PLAIN_CONF
    char *tmp = (char *)new char[5 * 1024 * 1024];

    if (tmp)
        delete []tmp;

#endif
    XmlNode *rootNode = new XmlNode;
    const char *attr = NULL;
    rootNode->init(rootTag, &attr);
    gModuleList.push_back(rootNode);

    loadConfFile(configFilePath);

    if (gModuleList.size() != 1)
        logToMem(LOG_LEVEL_ERR,
                 "parseFile find '{' and '}' do not match in the end of file %s, rootTag %s.",
                 configFilePath, rootTag);

    gModuleList.clear();

    handleSpecialCaseLoop(rootNode);


#ifdef TEST_OUTPUT_PLAIN_CONF
    char sPlainFile[512] = {0};
    strcpy(sPlainFile, configFilePath);
    strcat(sPlainFile, ".txt");
    plainconf::testOutputConfigFile(rootNode, sPlainFile);
#endif
    return rootNode;
}


void plainconf::release(XmlNode *pNode)
{
    XmlNodeList list;
    int count = pNode->getAllChildren(list);

    if (count > 0)
    {
        XmlNodeList::const_iterator iter;

        for (iter = list.begin(); iter != list.end(); ++iter)
            release(*iter);
    }

    if (!pNode->getParent())
        delete pNode;
}


//name: form like "moduleName|submodlue|itemname"
const char *plainconf::getConfDeepValue(const XmlNode *pNode,
                                        const char *name)
{
    const char *p = strchr(name, '|');

    if (!p)
        return pNode->getChildValue(name);
    else
    {
        AutoStr2 subName;
        subName.setStr(name, p - name);
        const XmlNode *subNode = pNode->getChild(subName.c_str());

        if (subNode)
            return getConfDeepValue(subNode, p + 1);
        else
            return NULL;
    }
}


//The below functions are only for test.
void plainconf::outputSpaces(int level, FILE *fp)
{
    for (int i = 1; i < level; ++i)
        fprintf(fp, "    ");
}


void plainconf::outputValue(FILE *fp, const char *value, int length)
{
    fwrite(value, length, 1, fp);
}


void plainconf::outputSigleNode(FILE *fp, const XmlNode *pNode, int level)
{
    outputSpaces(level, fp);
    const char *pStart = pNode->getValue();
    fprintf(fp, "%s ", pNode->getName());

    if (pStart && *pStart)
    {
        const char *p = strchr(pStart, '\n');

        if (p)
        {
            fprintf(fp, "<<<MY_END\n%s\n", pStart);
            outputSpaces(level, fp);
            fprintf(fp, "MY_END");
        }
        else
            outputValue(fp, pStart, strlen(pStart));
    }

    fprintf(fp, "\n");
}


static int s_compare(const void *p1, const void *p2)
{
    //return (*((XmlNode**)p1))->getName() - (*((XmlNode**)p2))->getName();
    int ret = (*((XmlNode **)p1))->hasChild() - (*((XmlNode **)
              p2))->hasChild();

    if (ret == 0)
        ret = (*((XmlNode **)p1))->getName() - (*((XmlNode **)p2))->getName();

    //strcasecmp( (*((XmlNode**)p1))->getName(), (*((XmlNode**)p2))->getName() );
    return ret;
}


void plainconf::outputConfigFile(const XmlNode *pNode, FILE *fp, int level)
{
    XmlNodeList list;
    int count = pNode->getAllChildren(list);
    list.sort(s_compare);

    if (count > 0)
    {
        if (level > 0)
        {
            fprintf(fp, "\n");
            outputSpaces(level, fp);
            const char *value = pNode->getValue();

            if (!value)
                value = "";

            fprintf(fp, "%s %s {\n", pNode->getName(), value);
        }

        XmlNodeList::const_iterator iter;

        for (iter = list.begin(); iter != list.end(); ++iter)
            outputConfigFile((*iter), fp, level + 1);

        if (level > 0)
        {
            outputSpaces(level, fp);
            fprintf(fp, "}\n");
        }
    }
    else
        outputSigleNode(fp, pNode, level);
}


void plainconf::testOutputConfigFile(const XmlNode *pNode,
                                     const char *file)
{
    FILE *fp = fopen(file, "w");

    if (!fp)
        return;

    int level = 0;
    outputConfigFile(pNode, fp, level);
    fclose(fp);
}
