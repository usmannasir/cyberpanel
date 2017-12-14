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
#ifndef MODULEMANAGER_H
#define MODULEMANAGER_H

#include <ls.h>
#include <http/httphandler.h>
#include <lsiapi/lsimoduledata.h>
#include <util/hashstringmap.h>
#include <util/tsingleton.h>

#include <stdint.h>


#define LSI_CONFDATA_NONE   0
#define LSI_CONFDATA_OWN    1
#define LSI_CONFDATA_PARSED 2
#define MAX_MODULE_CONFIG_LINES    300


class XmlNodeList;
class XmlNode;
class ModuleHandler;
class ModuleConfig;
class HttpContext;
class IolinkSessionHooks;
class HttpSessionHooks;
class ServerSessionHooks;

typedef lsi_module_t *ModulePointer;

class LsiModule : public HttpHandler
{
    friend class ModuleHandler;
public:
    explicit LsiModule(lsi_module_t *pModule);

    const char *getName() const     {   return "module";    }
    lsi_module_t *getModule() const {   return m_pModule;   }
private:
    lsi_module_t *m_pModule;
};

class ModuleManager : public HashStringMap<LsiModule *>,
    public TSingleton<ModuleManager>
{
    friend class TSingleton<ModuleManager>;
private:
    ModuleManager();

    iterator addModule(const char *name, const char *pType,
                       lsi_module_t *pModule);
    int getModulePath(const char *name, char *path, int max_len);
    lsi_module_t *loadModule(const char *name);
    void disableModule(lsi_module_t *pModule);
    int storeModulePointer(int index, lsi_module_t *module);
    int loadPrelinkedModules();

public:
    ~ModuleManager()
    {}

    int initModule();

    int runModuleInit();

    int loadModules(const XmlNodeList *pModuleNodeList);
    int unloadModules();

    int getModuleCount()  {   return size();  }
    short getModuleDataCount(unsigned int level);
    void incModuleDataCount(unsigned int level);

    void OnTimer100msec();
    void OnTimer10sec();

    void applyConfigToIolinkRt(IolinkSessionHooks *pRtHooks,
                               ModuleConfig *moduleConfig);
    void applyConfigToServerRt(ServerSessionHooks *pSessionHooks,
                               ModuleConfig *moduleConfig);
    void applyConfigToHttpRt(HttpSessionHooks *pRtHooks,
                             ModuleConfig *moduleConfig);
    void updateHttpApiHook(HttpSessionHooks *pRtHooks,
                           ModuleConfig *moduleConfig, int module_id);

    lsi_module_t *GetModulePointer(int module_id)
    {   return m_pModuleArray[module_id];  }

    ModuleConfig *getGlobalModuleConfig()
    {   return m_pGlobalModuleConfig;    }
    static void updateDebugLevel();

private:
    ModulePointer *m_pModuleArray;
    short  m_aModuleDataCount[LSI_DATA_COUNT];
    ModuleConfig    *m_pGlobalModuleConfig;

};


/***
 * Inheriting of the lsi_module_config_t
 * Global to listener and global to VHost do not inherit,
 * only between the contexts, may inherit
 * if only copy pointer of the struct, not set the BIT in the context.
 * Otherwise, set the BIT and data_flag set to 0 and config and sparam to NULL
 *
 */
typedef struct lsi_module_config_s
{
    lsi_module_t   *module;
    int16_t         data_flag;
    int16_t         filters_enable;
    void           *config; //if config_own_flag set, this need to be released
    AutoStr2       *sparam;
} lsi_module_config_t;


class ModuleConfig : public LsiModuleData
{
public:
    ModuleConfig() {};
    ~ModuleConfig();

    void copy(short _module_id, lsi_module_config_t *module_config)
    {
        lsi_module_config_t *config = get(_module_id);
        memcpy(config, module_config, sizeof(lsi_module_config_t));
        //config->config_own_flag = 0;     //should I have this void *config, in case lsi_module_config_t * module_config will be released outside
    }

    lsi_module_config_t *get(short _module_id) const
    {   return (lsi_module_config_t *)LsiModuleData::get(_module_id);    }


public:
    //Return the module count
    int getCount()  { return m_iCount;   }

    void init(int count);
    void inherit(const ModuleConfig *parentConfig);

    int isMatchGlobal();

    void setFilterEnable(short _module_id, int v);
    int getFilterEnable(short _module_id);


public:
    static void setFilterEnable(lsi_module_config_t *module_config, int v)
    {   module_config->filters_enable = ((v) ? 1 : 0);  }
    static int  getFilterEnable(lsi_module_config_t *module_config)
    {   return module_config->filters_enable;   }

    static int  compare(lsi_module_config_t *config1,
                        lsi_module_config_t *config2);

    static int  parsePriority(const XmlNode *pModuleNode, int *priority);
    static int  parseConfig(const XmlNode *pModuleNode, lsi_module_t *pModule,
                            ModuleConfig *pModuleConfig, int level, const char *name);

    static int  saveConfig(const XmlNode *pModuleUrlfilterNode,
                           lsi_module_t *pModule, lsi_module_config_t *module_config);

    static int  parseConfigList(const XmlNodeList *moduleConfigNodeList,
                                ModuleConfig *pModuleConfig, int level, const char *name);

    
    
    
    static int getKeyIndex(lsi_config_key_t *keys, const char *str);
    static void releaseModuleParamInfo(module_param_info_t *param_arr,
                                       int param_count);
    
    
    //return the val_out length
    static int escapeParamVal(const char *val_in, int len, char *val);
    
    static int preParseModuleParam(const char *param, int paramLen,
                                   int level, lsi_config_key_t *keys,
                                   module_param_info_t *param_arr,
                                   int *param_count);
};


#endif // MODULEMANAGER_H
