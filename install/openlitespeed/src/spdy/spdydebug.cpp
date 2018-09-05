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
#include "spdydebug.h"

#include <lsdef.h>
#include <util/autobuf.h>

#include <netinet/in.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int printheader(unsigned char *buff, int length)
{
    static char namebuff[1000];
    static char strbuff[1000];
    uint16_t temp16, NameCount, theLength, curP = 0;

    if (length < 2)
        return LS_FAIL;

    memcpy(&temp16, buff + curP, 2);
    curP += 2;

    NameCount = htons(temp16);
    if (NameCount == 0)
        return NameCount;

    //NameCount = 20;
    if (curP + 2 > length)
        return LS_FAIL;

    printf("There are %d names in the pack\n", NameCount);

    for (int i = 0; i < NameCount; i++)
    {
        memcpy(&temp16, buff + curP, 2);
        theLength = htons(temp16);
        curP += 2;

        if (curP + theLength > length)
            return LS_FAIL;

        memcpy(namebuff, buff + curP, theLength);
        namebuff[theLength] = 0;
        curP += theLength;

        if (curP + 2 > length)
            return LS_FAIL;

        memcpy(&temp16, buff + curP, 2);
        theLength = htons(temp16);
        curP += 2;

        if (curP + theLength > length)
            return LS_FAIL;

        memcpy(strbuff, buff + curP, theLength);
        strbuff[theLength] = 0;
        printf("%s %s\n", namebuff, strbuff);
        curP += theLength;

        if (i + 1 == NameCount)
        {
            printf("End of buff, curP:length = %d:%d\n", curP, length);
            return 1;
        }

        if (curP + 2 > length)
            return LS_FAIL;
    }

    return 1;
}


void printbuffstr(char *buff, int length)
{
    if (length > 999)
        length = 999;

    ::write(STDOUT_FILENO, buff, length);
}


void printbuff(unsigned char *buff, int length)
{
    char pbuff[1000];
    AutoBuf buf(4096);

    for (int i = 0; i < length;)
    {
        pbuff[0] = 0;
        int ii = length - i;

        if (ii < 16)
        {
            pbuff[0] = 0;
            sprintf(pbuff, "%04X, ", i);
            buf.append(pbuff);

            for (int ix = 0; ix < ii; ix++)
            {
                pbuff[0] = 0;
                sprintf(pbuff, "%02X,", buff[i + ix]);
                buf.append(pbuff);
            }

            buf.append("\n");

            break;
        }
        else
        {
            pbuff[0] = 0;
            sprintf(pbuff,
                    "%04X, %02X,%02X,%02X,%02X,%02X,%02X,%02X,%02X,%02X,%02X,%02X,%02X,%02X,%02X,%02X,%02X,\n",
                    i,
                    buff[i], buff[i + 1], buff[i + 2], buff[i + 3], buff[i + 4], buff[i + 5],
                    buff[i + 6], buff[i + 7],
                    buff[i + 8], buff[i + 9], buff[i + 10], buff[i + 11], buff[i + 12],
                    buff[i + 13], buff[i + 14], buff[i + 15]);
            buf.append(pbuff);
            i += 16;
        }
    }

    ::write(STDOUT_FILENO, buf.begin(), buf.size());
}
