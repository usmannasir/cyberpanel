#ifndef ADDRMAP_H
#define ADDRMAP_H

#include <lsdef.h>
#include <util/gpointerlist.h>

#include <assert.h>
#include <stdlib.h>

#define LARGE_PAGE_SIZE  0x100000l    //1MB
#define LARGE_PAGE_MASK  0xfffffl
#define LARGE_PAGE_BITS  20

struct AddrOffPair
{
    char   *m_ptr;
    size_t  m_offset; 
};


class Addr2OffMap
{
public:
    explicit Addr2OffMap(int capacity)
        : m_table(NULL)
        , m_tableEnd(NULL)
        , m_tableSize(0)
    {
        alloc(capacity);
    }

    ~Addr2OffMap()
    {
        if (m_table)
            free(m_table);
    }
        
    const AddrOffPair *lookup(const char *p) const
    {
        size_t page = ((size_t)p) >> LARGE_PAGE_BITS;
        AddrOffPair *pInfo = &m_table[page % m_tableSize];
        if (((size_t)pInfo->m_ptr >> LARGE_PAGE_BITS) == page)
        {
            return pInfo;
        }
        return lookup_collid(p, pInfo);
    }
    
    int add(const AddrOffPair *p)
    {
        if (addEx(p) == LS_FAIL)
        {
            if (rehash(m_tableSize * 2) == LS_FAIL)
                return LS_FAIL;
            return add(p);
        }
        return LS_OK;
    }
    
    void clear()
    {
        if (m_table)
            memset(m_table, 0, m_tableSize * sizeof(*m_table));
    }
    
private:

    int addEx(const AddrOffPair *p)
    {
        AddrOffPair *pInfo = m_table + 
                            (((size_t)p->m_ptr) >> LARGE_PAGE_BITS) % m_tableSize;
        if (pInfo->m_ptr == NULL)
        {
            memmove(pInfo, p, sizeof(*p));
            return LS_OK;
        }
        return add_collide(p, pInfo);
    }
    
    int alloc(size_t size);
    
    void release();

    void swap(Addr2OffMap &rhs);
    
    int rehash(int new_size);
    
    int add_collide(const AddrOffPair *p, AddrOffPair *pInfo);
    
    const AddrOffPair *lookup_collid(const char *p, AddrOffPair *pInfo) const;
    
    
private:
    AddrOffPair    *m_table;
    AddrOffPair    *m_tableEnd;
    size_t          m_tableSize;

    LS_NO_COPY_ASSIGN(Addr2OffMap);
    
};

class AddrMap
{
public:
    AddrMap()
        : m_off2ptrTable(16)
        , m_ptr2offTable(16)
        {}
    ~AddrMap();
    
    int addLargePage(AddrOffPair info, size_t size);
    
    size_t getMaxOffset() const     
    {   return m_off2ptrTable.size() * LARGE_PAGE_SIZE;   }
    
    char *offset2ptr(size_t offset) const
    {
        int page = offset >> LARGE_PAGE_BITS;
        if (page >= m_off2ptrTable.size())
            return NULL;
        return m_off2ptrTable[page] + (offset & LARGE_PAGE_MASK);
    }
    
    size_t ptr2offset(const void *ptr) const
    {
        const AddrOffPair * pInfo = m_ptr2offTable.lookup((char *)ptr);
        if (pInfo == NULL)
            return 0;
        return pInfo->m_offset + ((char *)ptr - pInfo->m_ptr);
    }
    
    int mapAddrSpace(size_t total);
    int remap(int fd, size_t start_offset, size_t new_size);
    void unmap();
    
    size_t getAvailAddrSpace( size_t offset, size_t required_size);

private:
    TPointerList<char>    m_off2ptrTable;
    Addr2OffMap           m_ptr2offTable;
    
    LS_NO_COPY_ASSIGN(AddrMap);
};

#endif // ADDRMAP_H
