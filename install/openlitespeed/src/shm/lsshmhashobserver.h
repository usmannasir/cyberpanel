#ifndef LSSHMHASHOBSERVER_H
#define LSSHMHASHOBSERVER_H

#include <lsdef.h>

class LsShmHash;
class LsShmHashObserver
{
public:
    explicit LsShmHashObserver(LsShmHash *pHash);
    virtual ~LsShmHashObserver();
    
    virtual int onNewEntry(const void *pKey, int keyLen, const void *pVal, 
                           int valLen, uint32_t lruTm) = 0;
    virtual int onDelEntry(const void *pKey, int keyLen) = 0;
    
    LsShmHash *getHash() const      {   return m_pHash;     }
    
private:
    LsShmHash *m_pHash;
    
    LS_NO_COPY_ASSIGN(LsShmHashObserver);
};

#endif // LSSHMHASHOBSERVER_H
