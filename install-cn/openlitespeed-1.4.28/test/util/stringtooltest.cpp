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
#ifdef RUN_TEST

#include "stringtooltest.h"
#include <util/stringtool.h>
#include "unittest-cpp/UnitTest++.h"


SUITE(StringtoolTest)
{
    TEST(mempbrkTest)
    {
        const char *pAccept, *pInput = "abcdefg";
        int iAcceptLength, iInputLength = 7;

        printf("STRINGTOOL: Mempbrk Test\n");
        pAccept = "f";
        iAcceptLength = 1;
        CHECK(StringTool::mempbrk(pInput, iInputLength, pAccept,
                                  iAcceptLength) == pInput + 5);

        pAccept = "jklofd";
        iAcceptLength = 4;
        CHECK(StringTool::mempbrk(pInput, iInputLength, pAccept,
                                  iAcceptLength) == NULL);

        iAcceptLength = 5;
        CHECK(StringTool::mempbrk(pInput, iInputLength, pAccept,
                                  iAcceptLength) == pInput + 5);

        iAcceptLength = 6;
        CHECK(StringTool::mempbrk(pInput, iInputLength, pAccept,
                                  iAcceptLength) == pInput + 3);

        pInput = "zxvnmgfpoi";
        iInputLength = 10;
        pAccept = "abcdefg";
        iAcceptLength = 7;
        CHECK(StringTool::mempbrk(pInput, iInputLength, pAccept,
                                  iAcceptLength) == pInput + 5);
    }

    TEST(memmemTest)
    {
        const char *pAccept, *pOutput,
              *pInput = "abcdefghijklmnopqrstuvwxyzghijkm";
        printf("STRINGTOOL: Memmem Test\n");
        pAccept = "abc";
        CHECK((pOutput = (const char *)StringTool::memmem(pInput, strlen(pInput),
                         pAccept, strlen(pAccept))) == pInput);

        pAccept = "ghijk";
        CHECK((pOutput = (const char *)StringTool::memmem(pInput, strlen(pInput),
                         pAccept, strlen(pAccept))) == memchr(pInput, 'g', strlen(pInput)));

        pAccept = "ghijkm";
        CHECK((pOutput = (const char *)StringTool::memmem(pInput, strlen(pInput),
                         pAccept, strlen(pAccept))) == memrchr(pInput, 'g', strlen(pInput)));

        pAccept = "sabc";
        CHECK(StringTool::memmem(pInput, strlen(pInput), pAccept,
                                 strlen(pAccept)) == NULL);

        pAccept = "ghijkmz";
        CHECK(StringTool::memmem(pInput, strlen(pInput), pAccept,
                                 strlen(pAccept)) == NULL);

        pAccept = "znkl";
        CHECK(StringTool::memmem(pInput, strlen(pInput), pAccept,
                                 strlen(pAccept)) == NULL);

    }
    //For Look Up SubString, if fail, check again with debugger to find i value
    TEST(lookupSubStringTest)
    {
        const char *pRet;
        int iRetLen, iNumTests = 20;
        printf("STRINGTOOL: lookupSubString Test \n");

        for (int i = 0; i < iNumTests; ++i)
        {
            iRetLen = 0;
            pRet = StringTool::lookupSubString(aLUSSInputs[i],
                                               aLUSSInputs[i] + aLUSSInputLen[i],
                                               aLUSSKeys[i],
                                               aLUSSKeyLen[i],
                                               &iRetLen,
                                               aLUSSSep[i],
                                               aLUSSComp[i]
                                              );
            //if aLUSSRet == -1, expect NULL
            //if aLUSSRetLen == -2 not looking for a len
            if (aLUSSRet[i] == -1)
            {
                CHECK(pRet == NULL);
                if (pRet != NULL)
                {
                    printf("ERROR: Failed test i = %d\n", i);
                    printf("Expected pRet == NULL, got %p\n", pRet);
                }
            }
            else if (aLUSSRetLen[i] == -2)
            {
                CHECK(pRet == aLUSSInputs[i] + aLUSSRet[i]);
                if (pRet != aLUSSInputs[i] + aLUSSRet[i])
                {
                    printf("ERROR: Failed test i = %d\n", i);
                    printf("Expected pRet = %p, got %p\n",
                           (aLUSSInputs[i] + aLUSSRet[i]), pRet);
                }
            }
            else
            {
                CHECK(pRet == aLUSSInputs[i] + aLUSSRet[i]
                      && iRetLen == aLUSSRetLen[i]);
                if (pRet != aLUSSInputs[i] + aLUSSRet[i]
                    || iRetLen != aLUSSRetLen[i])
                {
                    printf("ERROR: Failed test i = %d\n", i);
                    printf("Expected pRet = %p, retLen = %d, got %p, %d\n",
                           (aLUSSInputs[i] + aLUSSRet[i]),
                           aLUSSRetLen[i],
                           pRet, iRetLen);
                }
            }
        }
    }

    TEST(Memspn)
    {
        size_t iOutput;
        int iNumTests = 6;
        printf("STRINGTOOL: Memspn Test \n");
        for (int i = 0; i < iNumTests; ++i)
        {
            iOutput = StringTool::memspn(pMemspnInput, aMemspnInputSize[i],
                                         pMemspnAccept, aMemspnAcceptSize[i]);
            CHECK(iOutput == aMemspnOutput[i]);
            if (iOutput != aMemspnOutput[i])
            {
                printf("ERROR: Failed test i = %d\n", i);
                printf("Expected output = %d, got %d\n", (int)aMemspnOutput[i],
                       (int)iOutput);
            }
        }
    }

    TEST(MemCspn)
    {
        size_t iOutput;
        int iNumTests = 6;
        printf("STRINGTOOL: MemCspn Test \n");
        for (int i = 0; i < iNumTests; ++i)
        {
            iOutput = StringTool::memcspn(pMemspnInput, aMemspnInputSize[i],
                                          pMemspnAccept, aMemspnAcceptSize[i]);
            CHECK(iOutput == aMemCspnOutput[i]);
            if (iOutput != aMemCspnOutput[i])
            {
                printf("ERROR: Failed test i = %d\n", i);
                printf("Expected output = %d, got %d\n", (int)aMemCspnOutput[i],
                       (int)iOutput);
            }
        }
    }
}

#endif
