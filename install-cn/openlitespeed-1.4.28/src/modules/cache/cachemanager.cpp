/*
 *
 */

#include "cachemanager.h"
#include "cacheentry.h"

#include <util/autobuf.h>

#include <assert.h>
#include <ctype.h>
#include <stdio.h>



void CacheManager::populatePrivateTag()
{
    const char *pPrivateTags[] =
    {
        "E.formkey",
        "E.cart",
        "E.welcome",
        "E.minicart_head",
        "E.topLinks",
        "E.compare",
        "E.viewed",
        "E.compared",
        "E.poll",
        "E.messages",
        "E.reorder",
        "E.wishlist",
        "E.footer",
        "E.header",
        NULL
    };
    const char **p;
    for (p = pPrivateTags; *p != NULL; p++)
        getTagId(*p, strlen(*p));
}


void CacheManager::generateRpt(const char *name, AutoBuf *pBuf)
{
    CacheInfo *pInfo = getCacheInfo();
    cachestats_t *pPublic = pInfo->getPublicStats();
    cachestats_t *pPrivate = pInfo->getPrivateStats();
    char achBuf[4096];
    int n = snprintf(achBuf, 4096,
                     "[%s] PUB_CREATES:%d, PUB_HITS: %d, PUB_PURGE: %d, "
                     "PUB_EXPIRE: %d, PUB_COLLISION: %d, "
                     "PVT_CREATES:%d, PVT_HITS: %d, PVT_PURGE: %d, "
                     "PVT_EXPIRE: %d, PVT_COLLISION: %d, "
                     "PVT_SESSIONS: %d, PVT_SESSION_PURGE: %d, "
                     "FULLPAGE_HITS: %d, PARTIAL_HITS: %d\n",
                     name, pPublic->created, pPublic->hits, pPublic->purged,
                     pPublic->expired, pPublic->collisions,
                     pPrivate->created, pPrivate->hits, pPrivate->purged,
                     pPrivate->expired, pPrivate->collisions,
                     getPrivateSessionCount(),
                     pInfo->getSessionPurged(),
                     pInfo->getFullPageHits(),
                     pInfo->getPartialPageHits()
                    );
    pBuf->append(achBuf, n);

}

