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
#ifndef IOCHAIN_H
#define IOCHAIN_H

#include "edio/ediostream.h"
/*
class IOChain;
class InputSrc : public EdIS
{
    IOChain * m_pChain;
public:
    InputSrc()
        : m_pChain( NULL )
        {}
    void setIPChain( IOChain * pChain )
        {   m_pChain = pChain;  }

};

class OutputDst : public EdOS
{
    IOChain * m_pChain;
public:
    OutputDst()
        : m_pChain( NULL )
        {}
    void setIPChain( IOChain * pChain )
        {   m_pChain = pChain;  }

};

#include "util/loopbuf.h"
class IOChain
{
    InputSrc    * m_pSrc;
    OutputDst   * m_pDest;
    LoopBuf     m_buf;
public:
    IOChain(InputSrc* src, OutputDst* dest)
        : m_pSrc( src )
        , m_pDest( dest )
    {
        assert( m_pSrc );
        assert( m_pDest );
        m_pSrc->setIOChain( this );
        m_pDest->setIOChain( this );
    }
    ~IOChain() {};

};
*/
#endif
