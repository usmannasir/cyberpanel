/*
 * 
 */

#include "addrmap.h"
#include <shm/lsshmtypes.h>
#include <shm/lsshmhash.h>
#include <sys/mman.h>


int Addr2OffMap::alloc(size_t size)
{
    assert(m_table == NULL);
    m_table = (AddrOffPair *)malloc(size * sizeof(*m_table));
    if (m_table)
    {
        memset(m_table, 0, size * sizeof(*m_table));
        m_tableEnd  = m_table + size;
        m_tableSize = size;
        return LS_OK;
    }
    return LS_FAIL;
}    


void Addr2OffMap::release()
{
    if (m_table)
    {
        free(m_table);
        LS_ZERO_FILL(m_table, m_tableSize);
    }
}


void Addr2OffMap::swap(Addr2OffMap &rhs)
{
    char buf[sizeof(Addr2OffMap)];
    memmove(buf, &rhs, sizeof(buf));
    memmove(&rhs, this, sizeof(buf));
    memmove(this, buf, sizeof(buf));
}


int Addr2OffMap::rehash(int new_size)
{
    new_size = LsShmHash::roundUp(new_size);

    Addr2OffMap newTable(new_size);
    if (newTable.m_table == NULL)
        return LS_FAIL;
    AddrOffPair *p = m_table;
    AddrOffPair *pEnd = m_table + m_tableSize;
    while(p < pEnd)
    {
        if (p->m_ptr)
        {
            if (newTable.addEx(p) == LS_FAIL)
            {
                newTable.release();
                return rehash(new_size * 2);
            }
        }
        p++;
    }
    swap(newTable);
    return LS_OK;
}
    
    
int Addr2OffMap::add_collide(const AddrOffPair *p, AddrOffPair *pInfo)
{
    AddrOffPair *pEnd = pInfo + 3;
    if (pEnd >= m_tableEnd)
        pEnd = m_table + (pEnd - m_tableEnd);
    while(pInfo != pEnd)
    {
        assert(((size_t)pInfo->m_ptr) >> LARGE_PAGE_BITS
                != ((size_t)p->m_ptr) >> LARGE_PAGE_BITS);
        if (pInfo == m_tableEnd - 1)
        {
            pInfo = m_table;
        }
        else
        {
            ++pInfo;
        }
        if (pInfo->m_ptr == NULL)
        {
            memmove(pInfo, p, sizeof(*p));
            return LS_OK;
        }
    }
    return LS_FAIL;
}


const AddrOffPair *Addr2OffMap::lookup_collid(const char *p, AddrOffPair *pInfo) const
{
    AddrOffPair *pEnd = pInfo + 3;
    if (pEnd >= m_tableEnd)
        pEnd = m_table + (pEnd - m_tableEnd);
    while(pInfo != pEnd)
    {
        if (pInfo == m_tableEnd - 1)
        {
            pInfo = m_table;
        }
        else
        {
            ++pInfo;
        }
        if (((size_t)pInfo->m_ptr >> LARGE_PAGE_BITS) == 
            ((size_t)p) >> LARGE_PAGE_BITS)
        {
            return pInfo;
        }
    }
    return NULL;
}
    


AddrMap::~AddrMap()
{

}


int AddrMap::addLargePage(AddrOffPair info, size_t size)
{
    assert((info.m_offset & LARGE_PAGE_MASK) == 0);
    assert((size   & LARGE_PAGE_MASK) == 0);
    int page = info.m_offset >> LARGE_PAGE_BITS;
    assert(page == m_off2ptrTable.size());
    char * end = info.m_ptr + size;
    while(info.m_ptr < end)
    {
        if (m_off2ptrTable.push_back(info.m_ptr) == -1)
            return LS_FAIL;
        m_ptr2offTable.add(&info);
        info.m_ptr += LARGE_PAGE_SIZE;
        info.m_offset += LARGE_PAGE_SIZE;
    }
    return LS_OK;
}


int AddrMap::mapAddrSpace(size_t total)
{
    int needed = total - getMaxOffset();
    if (needed <= 0)
        return LS_OK;
    AddrOffPair pair;
    size_t bytes = (needed + LARGE_PAGE_MASK ) & ~LARGE_PAGE_MASK;
    pair.m_ptr = (char *) mmap(NULL, bytes + LARGE_PAGE_SIZE, PROT_NONE,
                               MAP_ANON|MAP_SHARED, -1, 0);
    if (!pair.m_ptr)
        return LS_FAIL;
    if (((unsigned long)pair.m_ptr & LARGE_PAGE_MASK) == 0)
        bytes += LARGE_PAGE_SIZE;
    else
    {
        char *pRelease = pair.m_ptr;
        size_t size; 
        pair.m_ptr = (char *)(((unsigned long)pair.m_ptr & ~LARGE_PAGE_MASK) 
                            + LARGE_PAGE_SIZE);
        size = pair.m_ptr - pRelease;
        munmap(pRelease, size);
        pRelease = pair.m_ptr + bytes;
        munmap(pRelease, LARGE_PAGE_SIZE - size);
    }
    pair.m_offset = getMaxOffset();
    if (addLargePage(pair, bytes) == LS_FAIL)
    {
        munmap(pair.m_ptr, bytes);
        return LS_FAIL;
    }
    return LS_OK;
    
}


int AddrMap::remap(int fd, size_t start_offset, size_t new_size)
{
    if (mapAddrSpace(new_size) == LS_FAIL)
        return LS_FAIL;
    start_offset = start_offset & ~(LSSHM_PAGESIZE -1);
    while(start_offset < new_size)
    {
        size_t block_end = (start_offset + LARGE_PAGE_SIZE) & ~LARGE_PAGE_MASK;
        if (block_end > new_size)
            block_end = new_size;
        char * ptr = offset2ptr(start_offset);
        ptr = (char *)mmap(ptr, block_end - start_offset, PROT_READ | PROT_WRITE,
                            MAP_FIXED | MAP_SHARED, fd, start_offset);
        if (ptr == MAP_FAILED)
            return LS_FAIL;
        start_offset = block_end;
    }
    return LS_OK;
    
}

static int unmap_large_page(void *pPage)
{
    munmap(pPage, LARGE_PAGE_SIZE);
    return 0;
}


void AddrMap::unmap()
{
    m_off2ptrTable.for_each(m_off2ptrTable.begin(), m_off2ptrTable.end(), 
                            unmap_large_page);
    m_off2ptrTable.clear();
    m_ptr2offTable.clear();
}


size_t AddrMap::getAvailAddrSpace( size_t offset, size_t required_size)
{
    size_t avail = 0;
    int page = offset >> LARGE_PAGE_BITS;
    avail = LARGE_PAGE_SIZE - (offset & LARGE_PAGE_MASK);
    while(avail < required_size && page < m_off2ptrTable.size() - 1)
    {
        if (required_size > LARGE_PAGE_SIZE 
            && m_off2ptrTable[page + 1] - m_off2ptrTable[page] == LARGE_PAGE_SIZE)
        {
            avail += LARGE_PAGE_SIZE;
            ++page;
        }
        else
            break;
    }
    return avail;    
}

