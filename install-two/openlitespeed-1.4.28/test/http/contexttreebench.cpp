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

#include <http/contexttree.h>
#include <http/httpcontext.h>
#include <lsr/ls_pool.h>
#include <util/misc/profiletime.h>

#include <stdio.h>
#include <string.h>

char *argv0 = NULL;

const char *aUriNames[] =
{
    "/",
    "/user/vhost/context/subcon/dark/", // Go deep
    "/user1/vhost/context/", // Contiguous and ptr should be the same.
    "/user1/vhost1/context/",
    "/user1/vhost2/context/",
    "/user1/vhost3/context/",
    "/user1/vhost4/context/",
    "/user1/vhost5/context/",
    "/user1/vhost6/context/",
    "/user1/vhost7/context/",
    "/user1/vhost8/context/",
    "/user1/vhost9/context/",
    "/user1/vhost10/context/",
    "/user2/vhost/context/",
    "/user3/vhost/context/",
    "/user4/vhost/context/",
    "/user5/vhost/context/",
    "/user6/vhost/context/",
    "/user7/vhost/context/",
    "/user8/vhost/context/" //Best case for new tree & contiguous.
};

const char *aDirNames[] =
{
    "/home/",
    "/home/user/vhost/context/subcon/dark/", // Go deep
    "/home/user1/vhost/context/", // Contiguous and ptr should be the same.
    "/home/user1/vhost1/context/",
    "/home/user1/vhost2/context/",
    "/home/user1/vhost3/context/",
    "/home/user1/vhost4/context/",
    "/home/user1/vhost5/context/",
    "/home/user1/vhost6/context/",
    "/home/user1/vhost7/context/",
    "/home/user1/vhost8/context/",
    "/home/user1/vhost9/context/",
    "/home/user1/vhost10/context/",
    "/home/user2/vhost/context/",
    "/home/user3/vhost/context/",
    "/home/user4/vhost/context/",
    "/home/user5/vhost/context/",
    "/home/user6/vhost/context/",
    "/home/user7/vhost/context/",
    "/home/user8/vhost/context/" //Best case for new tree & contiguous.
};
const int iDirCnt = 20;

void parse(ContextTree *pTree, char **aUris, int loops, int iTarget)
{
    int i;
    const HttpContext *pContext;
    ProfileTime timer("Benching!", loops, PROFILE_NANO);
    for (i = 0; i < loops; ++i)
    {
        pContext = pTree->getContext(aUris[iTarget],
                                     strlen(aUris[iTarget]));
        pContext->changeUidOnly();

        pContext = pTree->matchLocation(pContext->getLocation(),
                                        pContext->getLocationLen());
        pContext->changeUidOnly();

        pContext = pTree->bestMatch(aUris[iTarget], strlen(aUris[iTarget]));
        pContext->changeUidOnly();

        pContext = pTree->matchLocation(pContext->getLocation(),
                                        pContext->getLocationLen());
        pContext->changeUidOnly();
    }
}

void singletest(ContextTree *pTree, int loops)
{

    int i;
    HttpContext *aContexts[iDirCnt];
    char *aUris[iDirCnt];
    for (i = 0; i < iDirCnt; ++i)
    {
        aUris[i] = ls_pdupstr(aUriNames[i]);
        aContexts[i] = new HttpContext();
        aContexts[i]->set(aUris[i], aDirNames[i], NULL);
        if (pTree->add(aContexts[i]) != LS_OK)
            printf("Add failed.\n");
    }

    printf("Deepest\n");
    for (i = 0; i < 10; ++i)
        parse(pTree, aUris, loops, 1);

    printf("New Tree Contiguous and Ptr should be same.\n");
    for (i = 0; i < 10; ++i)
        parse(pTree, aUris, loops, 2);

    printf("Orig best case?\n");
    for (i = 0; i < 10; ++i)
        parse(pTree, aUris, loops, 12);

    printf("New Tree Contiguous best case.\n");
    for (i = 0; i < 10; ++i)
        parse(pTree, aUris, loops, 1);

}

void tentest(ContextTree *pTree, int loops)
{
    int i, j;
    HttpContext *aContexts[iDirCnt * 10];
    char *aUris[iDirCnt * 10];
    for (i = 0; i < iDirCnt; ++i)
    {
        for (j = 0; j < 10; ++j)
        {
            aUris[i * 10 + j] = (char *)ls_palloc(strlen(aUriNames[i]) + 4);
            snprintf(aUris[i * 10 + j], strlen(aUriNames[i]) + 4, "%s%d",
                     aUriNames[i], j);
            aContexts[i * 10 + j] = new HttpContext();
            aContexts[i * 10 + j]->set(aUris[i * 10 + j], aDirNames[i], NULL);
            if (pTree->add(aContexts[i * 10 + j]) != LS_OK)
                printf("Add failed.\n");
        }
    }

//     for (i = 0; i < iDirCnt * 10; ++i)
//     {
//         printf("Uris: %s\n", aUris[i]);
//         printf("Contexts: %.*s\n", aContexts[i]->getURILen(),
//                aContexts[i]->getURI());
//     }

    parse(pTree, aUris, loops, iDirCnt * 10);
}

int main(int ac, char *av[])
{
    int loops = 100000;
    ContextTree *pTree = new ContextTree();
    HttpContext *pRootContext = new HttpContext();

    printf("Begin Bench\n");
    pRootContext->set(aUriNames[0], aDirNames[0], NULL);

    pTree->setRootContext(pRootContext);
    pTree->setRootLocation(aDirNames[0], strlen(aDirNames[0]));

//     tentest(pTree, loops);
    singletest(pTree, loops);

    delete pTree;
    return 0;
}