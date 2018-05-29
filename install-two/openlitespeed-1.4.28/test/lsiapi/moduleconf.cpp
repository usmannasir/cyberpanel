/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2017  LiteSpeed Technologies, Inc.                 *
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
#ifdef RUN_TEST

#include <lsiapi/lsiapi.h>
#include <ls.h>
#include "unittest-cpp/UnitTest++.h"
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>
#include <lsiapi/modulemanager.h>

struct escapeMatchInfo_t
{
    const char *src;
    const char *dst;
};

escapeMatchInfo_t tests[] =
{
    {" !!!  123 ", " !!!  123 "},
    {"   123 ", "   123 "},
    
     {"   123 \\", "   123 \\"},
     {"   123 \\\\", "   123 \\\\"},
     
     {"   123 \\\"", "   123 \""},
     
     
    
    {"\'   123 \'", "   123 "},
    {"`   123 `", "   123 "},
    {"\"   123 \"", "   123 "},
    
    {"\'   123 \'", "   123 "},
    {"`   123 `", "   123 "},
    {"\"   123 \"", "   123 "},
    
    {"\' \"  123 \'", " \"  123 "},
    {"` \"  123 `", " \"  123 "},
    {"\" `  123 \"", " `  123 "},
    
    {"\' \\\"  123 \'", " \\\"  123 "},
    {"` \\\"  123 `", " \\\"  123 "},
    {"\" \\`  123 \"", " \\`  123 "},
    
    {"\\' \"  123 \'", "\\ \"  123 "},
    {"\\` \"  123 `", "\\ \"  123 "},
    {"\\\" `  123 \"", "\\ `  123 "},
    
    {"\' \\\'  123 \'", " \'  123 "},
    {"` \\`  123 `", " `  123 "},
    {"\" \\\"  123 \"", " \"  123 "},
    
    
    //Special cases
    {"`  \\`  `   \\\" \"123 \\\"  ff \"  \\\' \'123 \\\'  ff \'    ",
        "  `     \\ 123 \\  ff   \\ 123 \\  ff     " },

    {"`  \\`  `   \\\"\\\' \"123 \\\"  ff \"  \\\' \'123 \\\'  ff \'    \\",
        "  `     \\\\\' 123 \\  ff   \\ 123 \\  ff     \\" },
        
    {"\\\\\\\` 123 \\\\\\\` 112 \\r\\n \\t \\\" 444 \`",
        "\\\\\\ 123 \\\\\` 112 \\r\\n \\t \\\" 444 " },

    //  [` 123 \\` 345 `] ====> [ 123 \` 345 ]
    {"` 123 \\\\` 345 `", " 123 \\` 345 "},
        
    
};

TEST(TEST_MODULECONF)
{
    char str[1024] = {0};
    size_t ret, i;
    FILE *f = fopen("/tmp/samples.txt", "w");
    
    for (i=0; i<sizeof(tests)/sizeof(escapeMatchInfo_t); ++i)
    {
        ret = ModuleConfig::escapeParamVal(tests[i].src, strlen(tests[i].src), str);
        printf("i %d %d.\n", i, strlen(tests[i].dst));
        CHECK(ret == strlen(tests[i].dst));
        CHECK(memcmp(str, tests[i].dst, ret) ==0);
        
        if(f)
            fprintf(f, "[%s]\n[%s]\n\n", tests[i].src, tests[i].dst);
    }
    
    if(f)
    {
        fclose(f);
        printf("File /tmp/samples.txt created, you may view it for sample in plain text.\n");
    }
    printf("Pass all tests of TEST_MODULECONF.\n");
    
}



#endif
